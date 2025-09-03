#!/bin/bash

# ProximityService - Independent Docker Services Startup Script
# This script runs all services as independent Docker containers without docker-compose

set -e

echo "🚀 Starting ProximityService with independent Docker containers..."

# Create custom Docker network
NETWORK_NAME="proximity-network"
echo "📡 Creating Docker network: $NETWORK_NAME"
docker network create $NETWORK_NAME 2>/dev/null || echo "Network $NETWORK_NAME already exists"

# Create Docker volumes
echo "💾 Creating Docker volumes..."
docker volume create postgres_primary_data 2>/dev/null || true
docker volume create postgres_replica1_data 2>/dev/null || true
docker volume create postgres_replica2_data 2>/dev/null || true
docker volume create redis_master_data 2>/dev/null || true
docker volume create redis_replica1_data 2>/dev/null || true
docker volume create redis_replica2_data 2>/dev/null || true

# Function to wait for service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if docker run --rm --network $NETWORK_NAME alpine/curl:latest -s --connect-timeout 1 $host:$port > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "   Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Function to wait for PostgreSQL
wait_for_postgres() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if docker run --rm --network $NETWORK_NAME postgres:15 pg_isready -h $host -p $port > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "   Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# 1. Start PostgreSQL Primary
echo "🐘 Starting PostgreSQL Primary..."
docker run -d \
    --name postgres-primary \
    --network $NETWORK_NAME \
    -p 5832:5832 \
    -e POSTGRES_PASSWORD=password \
    -e PGPORT=5832 \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_REPLICATION_USER=replicator \
    -e POSTGRES_REPLICATION_PASSWORD=replica_password \
    -v postgres_primary_data:/var/lib/postgresql/data \
    -v $(pwd)/services/database/init.sql:/docker-entrypoint-initdb.d/init.sql \
    -v $(pwd)/services/database/primary-setup.sh:/docker-entrypoint-initdb.d/primary-setup.sh \
    postgres:15 \
    postgres -p 5832 -c wal_level=replica -c max_wal_senders=10 -c max_replication_slots=10 -c hot_standby=on

wait_for_postgres postgres-primary 5832 "PostgreSQL Primary"

# 2. Start PostgreSQL Replicas
echo "🐘 Starting PostgreSQL Replica 1..."
docker run -d \
    --name postgres-replica1 \
    --network $NETWORK_NAME \
    -p 5833:5833 \
    -e POSTGRES_PASSWORD=password \
    -e PGPORT=5833 \
    -e PGUSER=postgres \
    -e POSTGRES_PRIMARY_HOST=postgres-primary \
    -e POSTGRES_PRIMARY_PORT=5832 \
    -e POSTGRES_REPLICATION_USER=replicator \
    -e POSTGRES_REPLICATION_PASSWORD=replica_password \
    -v postgres_replica1_data:/var/lib/postgresql/data \
    -v $(pwd)/services/database/replica-setup.sh:/docker-entrypoint-initdb.d/replica-setup.sh \
    postgres:15 \
    postgres -p 5833

echo "🐘 Starting PostgreSQL Replica 2..."
docker run -d \
    --name postgres-replica2 \
    --network $NETWORK_NAME \
    -p 5834:5834 \
    -e POSTGRES_PASSWORD=password \
    -e PGPORT=5834 \
    -e PGUSER=postgres \
    -e POSTGRES_PRIMARY_HOST=postgres-primary \
    -e POSTGRES_PRIMARY_PORT=5832 \
    -e POSTGRES_REPLICATION_USER=replicator \
    -e POSTGRES_REPLICATION_PASSWORD=replica_password \
    -v postgres_replica2_data:/var/lib/postgresql/data \
    -v $(pwd)/services/database/replica-setup.sh:/docker-entrypoint-initdb.d/replica-setup.sh \
    postgres:15 \
    postgres -p 5834

# 3. Start Redis Master
echo "🗃️ Starting Redis Master..."
docker run -d \
    --name redis-master \
    --network $NETWORK_NAME \
    -p 6739:6739 \
    -e REDIS_REPLICATION_MODE=master \
    -v redis_master_data:/data \
    redis:7-alpine \
    redis-server --port 6739 --maxmemory 2gb --maxmemory-policy allkeys-lru --save 60 1000

sleep 3  # Wait for Redis master to start

# 4. Start Redis Replicas
echo "🗃️ Starting Redis Replica 1..."
docker run -d \
    --name redis-replica1 \
    --network $NETWORK_NAME \
    -p 6740:6740 \
    -e REDIS_REPLICATION_MODE=slave \
    -v redis_replica1_data:/data \
    redis:7-alpine \
    redis-server --port 6740 --replicaof redis-master 6739 --maxmemory 2gb --maxmemory-policy allkeys-lru

echo "🗃️ Starting Redis Replica 2..."
docker run -d \
    --name redis-replica2 \
    --network $NETWORK_NAME \
    -p 6741:6741 \
    -e REDIS_REPLICATION_MODE=slave \
    -v redis_replica2_data:/data \
    redis:7-alpine \
    redis-server --port 6741 --replicaof redis-master 6739 --maxmemory 2gb --maxmemory-policy allkeys-lru

# 5. Start Redis Sentinels
echo "👁️ Starting Redis Sentinels..."
docker run -d \
    --name redis-sentinel1 \
    --network $NETWORK_NAME \
    -p 26379:26379 \
    -v $(pwd)/services/cache/sentinel.conf:/etc/redis/sentinel.conf \
    redis:7-alpine \
    redis-sentinel /etc/redis/sentinel.conf

docker run -d \
    --name redis-sentinel2 \
    --network $NETWORK_NAME \
    -p 26380:26380 \
    -v $(pwd)/services/cache/sentinel2.conf:/etc/redis/sentinel2.conf \
    redis:7-alpine \
    redis-sentinel /etc/redis/sentinel2.conf

docker run -d \
    --name redis-sentinel3 \
    --network $NETWORK_NAME \
    -p 26381:26381 \
    -v $(pwd)/services/cache/sentinel3.conf:/etc/redis/sentinel3.conf \
    redis:7-alpine \
    redis-sentinel /etc/redis/sentinel3.conf

# 6. Build and start Location Service
echo "📍 Building and starting Location Service..."
cd services/location-service
docker build -t location-service-standalone .
cd ../..

docker run -d \
    --name location-service \
    --network $NETWORK_NAME \
    -p 8921:8921 \
    -e REDIS_HOST=redis-master \
    -e REDIS_PORT=6739 \
    location-service-standalone

# 7. Build and start Business Service (if not already built)
echo "🏢 Building and starting Business Service..."
cd services/business-service
docker build -t business-service-standalone . 2>/dev/null || echo "Business service image already exists"
cd ../..

# Stop existing business service if running
docker stop business-service-standalone 2>/dev/null || true
docker rm business-service-standalone 2>/dev/null || true

docker run -d \
    --name business-service-standalone \
    --network $NETWORK_NAME \
    -p 9823:9823 \
    -e DATABASE_URL="postgresql://postgres:password@postgres-primary:5832/proximity_db" \
    -e REDIS_HOST=redis-master \
    -e REDIS_PORT=6739 \
    business-service-standalone

# 8. Build and start API Gateway
echo "🚪 Building and starting API Gateway..."
cd services/api-gateway
docker build -t api-gateway-standalone .
cd ../..

docker run -d \
    --name api-gateway \
    --network $NETWORK_NAME \
    -p 7891:7891 \
    -e REDIS_HOST=redis-master \
    -e REDIS_PORT=6739 \
    -e LOCATION_SERVICE_URL=http://location-service:8921 \
    -e BUSINESS_SERVICE_URL=http://business-service-standalone:9823 \
    api-gateway-standalone

# 9. Build and start Cache Warmer
echo "🔥 Building and starting Cache Warmer..."
cd services/cache
docker build -t cache-warmer-standalone .
cd ../..

docker run -d \
    --name cache-warmer \
    --network $NETWORK_NAME \
    -e DATABASE_URL="postgresql://postgres:password@postgres-primary:5832/proximity_db" \
    -e REDIS_HOST=redis-master \
    -e REDIS_PORT=6739 \
    cache-warmer-standalone

# 10. Start UI independently (using existing script)
echo "🌐 Starting UI independently..."
if [ -f "start-ui.sh" ]; then
    ./start-ui.sh
else
    echo "⚠️ UI start script not found. Starting UI manually..."
    cd demo
    nohup python3 -m http.server 8081 > ../ui.log 2>&1 &
    UI_PID=$!
    echo $UI_PID > .ui.pid
    echo "✅ UI started on http://localhost:8081 (PID: $UI_PID)"
    cd ..
fi

# Wait for services to be ready
echo "🔍 Checking service health..."
sleep 5

wait_for_service redis-master 6739 "Redis Master"
wait_for_service location-service 8921 "Location Service" 
wait_for_service business-service-standalone 9823 "Business Service"
wait_for_service api-gateway 7891 "API Gateway"

# Display service status
echo ""
echo "🎉 All services started successfully!"
echo ""
echo "📊 Service Status:"
echo "=================="
echo "🐘 PostgreSQL Primary:     http://localhost:5832"
echo "🐘 PostgreSQL Replica 1:   http://localhost:5833" 
echo "🐘 PostgreSQL Replica 2:   http://localhost:5834"
echo "🗃️ Redis Master:           http://localhost:6739"
echo "🗃️ Redis Replica 1:        http://localhost:6740"
echo "🗃️ Redis Replica 2:        http://localhost:6741"
echo "👁️ Redis Sentinel 1:       http://localhost:26379"
echo "👁️ Redis Sentinel 2:       http://localhost:26380"
echo "👁️ Redis Sentinel 3:       http://localhost:26381"
echo "📍 Location Service:       http://localhost:8921"
echo "🏢 Business Service:       http://localhost:9823"
echo "🚪 API Gateway:            http://localhost:7891"
echo "🌐 Demo UI:               http://localhost:8081"
echo ""
echo "🔍 Health Check Endpoints:"
echo "=========================="
echo "curl http://localhost:8921/health  # Location Service"
echo "curl http://localhost:9823/health  # Business Service"
echo "curl http://localhost:7891/health  # API Gateway"
echo ""
echo "🛑 To stop all services, run: ./stop-docker-services.sh"
echo ""
echo "✅ ProximityService is ready! Visit http://localhost:8081 to use the demo."