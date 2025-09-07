#!/bin/bash

echo "🚀 Starting Google Drive MVP - All Services"
echo "==========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if container is running
check_container() {
    if docker ps -q -f name=$1 | grep -q .; then
        echo -e "${GREEN}✓ $1 is running${NC}"
        return 0
    else
        echo -e "${RED}✗ $1 failed to start${NC}"
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo -e "${YELLOW}⏳ Waiting for $service_name to be ready on port $port...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:$port > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service_name is ready!${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo -e "${RED}✗ $service_name failed to become ready${NC}"
    return 1
}

echo -e "${BLUE}Step 1: Starting Infrastructure Services${NC}"
echo "----------------------------------------"

# Start PostgreSQL
echo "🗄️ Starting PostgreSQL..."
docker run -d --name postgres-gdrive \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=gdrive \
    -p 5432:5432 \
    postgres:15-alpine

# Start Redis
echo "🔴 Starting Redis..."
docker run -d --name redis-gdrive \
    -p 6379:6379 \
    redis:7-alpine

# Start MinIO
echo "🪣 Starting MinIO..."
docker run -d --name minio-gdrive \
    -p 9000:9000 \
    -p 9001:9001 \
    -e MINIO_ROOT_USER=minioadmin \
    -e MINIO_ROOT_PASSWORD=minioadmin123 \
    minio/minio server /data --console-address ":9001"

echo -e "${YELLOW}⏳ Waiting for infrastructure to be ready...${NC}"
sleep 20

# Wait for MinIO specifically 
echo -e "${YELLOW}⏳ Waiting for MinIO to be ready...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:9000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MinIO is ready!${NC}"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

echo -e "${BLUE}Step 2: Building Service Images${NC}"
echo "--------------------------------"

# Build all service images
services=("auth-service" "file-service" "metadata-service" "block-service" "notification-service" "api-gateway")

for service in "${services[@]}"; do
    echo "🔨 Building $service..."
    cd $service && docker build -t $service . && cd ..
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $service built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build $service${NC}"
        exit 1
    fi
done

echo -e "${BLUE}Step 3: Starting Application Services${NC}"
echo "------------------------------------"

# Start Auth Service
echo "🔐 Starting Auth Service..."
docker run -d --name auth-service \
    --network bridge \
    -p 9011:9001 \
    -e DB_HOST=172.17.0.1 \
    -e DB_USER=postgres \
    -e DB_PASSWORD=postgres \
    -e DB_NAME=gdrive \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    auth-service

# Start File Service
echo "📁 Starting File Service..."
docker run -d --name file-service \
    --network bridge \
    -p 9012:9002 \
    -e DB_HOST=172.17.0.1 \
    -e DB_USER=postgres \
    -e DB_PASSWORD=postgres \
    -e DB_NAME=gdrive \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    -e STORAGE_ENDPOINT=172.17.0.1:9000 \
    -e STORAGE_ACCESS_KEY=minioadmin \
    -e STORAGE_SECRET_KEY=minioadmin123 \
    -e STORAGE_BUCKET=gdrive-files \
    -e AUTH_SERVICE_URL=http://172.17.0.1:9011 \
    file-service

# Start Metadata Service  
echo "📋 Starting Metadata Service..."
docker run -d --name metadata-service \
    --network bridge \
    -p 9003:8000 \
    -e DB_HOST=172.17.0.1 \
    -e DB_USER=postgres \
    -e DB_PASSWORD=postgres \
    -e DB_NAME=gdrive \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    -e AUTH_SERVICE_URL=http://172.17.0.1:9011 \
    metadata-service

# Start Block Service
echo "🧱 Starting Block Service..."
docker run -d --name block-service \
    --network bridge \
    -p 9004:8000 \
    -e DB_HOST=172.17.0.1 \
    -e DB_USER=postgres \
    -e DB_PASSWORD=postgres \
    -e DB_NAME=gdrive \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    -e AUTH_SERVICE_URL=http://172.17.0.1:9011 \
    -e STORAGE_ENDPOINT=172.17.0.1:9000 \
    -e STORAGE_ACCESS_KEY=minioadmin \
    -e STORAGE_SECRET_KEY=minioadmin123 \
    -e STORAGE_BUCKET=gdrive-blocks \
    block-service

# Start Notification Service
echo "🔔 Starting Notification Service..."
docker run -d --name notification-service \
    --network bridge \
    -p 9005:8000 \
    -e DB_HOST=172.17.0.1 \
    -e DB_USER=postgres \
    -e DB_PASSWORD=postgres \
    -e DB_NAME=gdrive \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    -e AUTH_SERVICE_URL=http://172.17.0.1:9011 \
    notification-service

# Start API Gateway
echo "🌐 Starting API Gateway..."
docker run -d --name api-gateway \
    --network bridge \
    -p 9010:8000 \
    -e AUTH_SERVICE_URL=http://172.17.0.1:9011 \
    -e FILE_SERVICE_URL=http://172.17.0.1:9012 \
    -e METADATA_SERVICE_URL=http://172.17.0.1:9003 \
    -e BLOCK_SERVICE_URL=http://172.17.0.1:9004 \
    -e NOTIFICATION_SERVICE_URL=http://172.17.0.1:9005 \
    -e REDIS_HOST=172.17.0.1 \
    -e REDIS_PORT=6379 \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    api-gateway

echo -e "${BLUE}Step 4: Starting UI Service${NC}"
echo "---------------------------"

# Start UI Service (React App)
echo "🎨 Starting UI Service..."
cd ui-service

# Check if node_modules exists, if not install dependencies
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing UI dependencies...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to install UI dependencies${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ UI dependencies installed${NC}"
fi

# Start the React development server in background
echo -e "${YELLOW}⚡ Starting React development server...${NC}"
nohup npm start > ui-service.log 2>&1 &
UI_PID=$!
echo $UI_PID > ui-service.pid

# Wait for UI to be ready
echo -e "${YELLOW}⏳ Waiting for UI service to be ready...${NC}"
ui_ready=false
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ UI Service is ready!${NC}"
        ui_ready=true
        break
    fi
    sleep 2
done

cd ..

if [ "$ui_ready" = false ]; then
    echo -e "${RED}✗ UI Service failed to start${NC}"
    if [ -f "ui-service/ui-service.pid" ]; then
        kill $(cat ui-service/ui-service.pid) 2>/dev/null
        rm -f ui-service/ui-service.pid
    fi
fi

echo -e "${BLUE}Step 5: Verifying All Services${NC}"
echo "-----------------------------"

# Wait for all services to be ready
sleep 5

# Check all containers
echo "📊 Container Status:"
containers=("postgres-gdrive" "redis-gdrive" "minio-gdrive" "auth-service" "file-service" "metadata-service" "block-service" "notification-service" "api-gateway")

all_running=true
for container in "${containers[@]}"; do
    if ! check_container $container; then
        all_running=false
    fi
done

# Check service health
echo ""
echo "🏥 Service Health Checks:"
services_health=(
    "Auth Service:9011"
    "File Service:9012" 
    "Metadata Service:9003"
    "Block Service:9004"
    "Notification Service:9005"
    "API Gateway:9010"
)

for service_info in "${services_health[@]}"; do
    IFS=':' read -r service_name port <<< "$service_info"
    if curl -s http://localhost:$port/health > /dev/null 2>&1 || curl -s http://localhost:$port > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $service_name (port $port) is healthy${NC}"
    else
        echo -e "${RED}✗ $service_name (port $port) is not responding${NC}"
        all_running=false
    fi
done

echo ""
echo "==========================================="
if [ "$all_running" = true ]; then
    echo -e "${GREEN}🎉 ALL SERVICES STARTED SUCCESSFULLY!${NC}"
    echo ""
    echo -e "${BLUE}Service Endpoints:${NC}"
    echo "🎨 UI Service:          http://localhost:3000"
    echo "🌐 API Gateway:         http://localhost:9010"
    echo "🔐 Auth Service:        http://localhost:9011"
    echo "📁 File Service:        http://localhost:9012" 
    echo "📋 Metadata Service:    http://localhost:9003"
    echo "🧱 Block Service:       http://localhost:9004"
    echo "🔔 Notification Service: http://localhost:9005"
    echo ""
    echo -e "${BLUE}Infrastructure:${NC}"
    echo "🗄️ PostgreSQL:          localhost:5432"
    echo "🔴 Redis:               localhost:6379"
    echo "🪣 MinIO Console:       http://localhost:9001"
    echo ""
    echo -e "${YELLOW}🎯 Ready for Demo! Open http://localhost:3000 in your browser${NC}"
    echo -e "${GREEN}📱 Use the UI to test all MVP features interactively!${NC}"
else
    echo -e "${RED}❌ SOME SERVICES FAILED TO START${NC}"
    echo "Check the logs with: docker logs <service-name>"
    exit 1
fi