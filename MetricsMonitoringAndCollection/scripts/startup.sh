#!/bin/bash

# Metrics Monitoring System - Individual Docker Container Startup Script
# This script starts all services as individual Docker containers

set -e

echo "================================================"
echo "   Metrics Monitoring System - Demo Startup    "
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NETWORK_NAME="metrics-network"
DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICES_DIR="$DEMO_DIR/services"
UI_DIR="$DEMO_DIR/ui"

# Function to check if container is running
container_exists() {
    docker ps -a --format "table {{.Names}}" | grep -q "^$1$"
}

# Function to stop and remove container if exists
cleanup_container() {
    if container_exists "$1"; then
        echo -e "${YELLOW}Stopping and removing existing container: $1${NC}"
        docker stop "$1" 2>/dev/null || true
        docker rm "$1" 2>/dev/null || true
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $service to be ready..."
    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo -e " ${GREEN}Ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}Timeout!${NC}"
    return 1
}

echo -e "\n${GREEN}Step 1: Creating Docker network${NC}"
docker network create $NETWORK_NAME 2>/dev/null || echo "Network already exists"

echo -e "\n${GREEN}Step 2: Starting Infrastructure Services${NC}"

# Start etcd
echo "Starting etcd..."
cleanup_container "demo-etcd"
docker run -d \
    --name demo-etcd \
    --network $NETWORK_NAME \
    -p 2379:2379 \
    -p 2380:2380 \
    quay.io/coreos/etcd:v3.5.0 \
    /usr/local/bin/etcd \
    --name etcd0 \
    --advertise-client-urls http://0.0.0.0:2379 \
    --listen-client-urls http://0.0.0.0:2379 \
    --initial-advertise-peer-urls http://0.0.0.0:2380 \
    --listen-peer-urls http://0.0.0.0:2380 \
    --initial-cluster etcd0=http://0.0.0.0:2380
wait_for_service "etcd" 2379

# Start Redis
echo "Starting Redis..."
cleanup_container "demo-redis"
docker run -d \
    --name demo-redis \
    --network $NETWORK_NAME \
    -p 6379:6379 \
    redis:7-alpine
wait_for_service "Redis" 6379

# Start Kafka (using single-node setup)
echo "Starting Zookeeper for Kafka..."
cleanup_container "demo-zookeeper"
docker run -d \
    --name demo-zookeeper \
    --network $NETWORK_NAME \
    -p 2181:2181 \
    -e ZOOKEEPER_CLIENT_PORT=2181 \
    -e ZOOKEEPER_TICK_TIME=2000 \
    confluentinc/cp-zookeeper:7.0.1
wait_for_service "Zookeeper" 2181

echo "Starting Kafka..."
cleanup_container "demo-kafka"
docker run -d \
    --name demo-kafka \
    --network $NETWORK_NAME \
    -p 9293:9293 \
    -e KAFKA_BROKER_ID=1 \
    -e KAFKA_ZOOKEEPER_CONNECT=demo-zookeeper:2181 \
    -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9293,PLAINTEXT_INTERNAL://demo-kafka:29092 \
    -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_INTERNAL:PLAINTEXT \
    -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
    -e KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1 \
    -e KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1 \
    confluentinc/cp-kafka:7.0.1
wait_for_service "Kafka" 9293

# Start InfluxDB
echo "Starting InfluxDB..."
cleanup_container "demo-influxdb"
docker run -d \
    --name demo-influxdb \
    --network $NETWORK_NAME \
    -p 8026:8086 \
    -e DOCKER_INFLUXDB_INIT_MODE=setup \
    -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
    -e DOCKER_INFLUXDB_INIT_PASSWORD=admin123 \
    -e DOCKER_INFLUXDB_INIT_ORG=metrics \
    -e DOCKER_INFLUXDB_INIT_BUCKET=metrics \
    -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=demo-token-123 \
    influxdb:2.7
wait_for_service "InfluxDB" 8026

echo -e "\n${GREEN}Step 3: Building Application Services${NC}"

# Build metrics-collector
echo "Building metrics-collector..."
cd "$SERVICES_DIR/metrics-collector"
docker build --no-cache -t demo-metrics-collector .

# Build data-consumer
echo "Building data-consumer..."
cd "$SERVICES_DIR/data-consumer"
docker build --no-cache -t demo-data-consumer .

# Build query-service
echo "Building query-service..."
cd "$SERVICES_DIR/query-service"
docker build --no-cache -t demo-query-service .

# Build alert-manager
echo "Building alert-manager..."
cd "$SERVICES_DIR/alert-manager"
docker build --no-cache -t demo-alert-manager .

# Build dashboard
echo "Building dashboard..."
cd "$SERVICES_DIR/dashboard"
docker build --no-cache -t demo-dashboard .

echo -e "\n${GREEN}Step 4: Starting Application Services${NC}"

# Start metrics-collector
echo "Starting metrics-collector..."
cleanup_container "demo-metrics-collector"
docker run -d \
    --name demo-metrics-collector \
    --network $NETWORK_NAME \
    -p 9847:9847 \
    -e KAFKA_BROKER=demo-kafka:29092 \
    -e ETCD_HOST=demo-etcd \
    -e ETCD_PORT=2379 \
    demo-metrics-collector
wait_for_service "metrics-collector" 9847

# Start data-consumer
echo "Starting data-consumer..."
cleanup_container "demo-data-consumer"
docker run -d \
    --name demo-data-consumer \
    --network $NETWORK_NAME \
    -p 4692:4692 \
    -e KAFKA_BROKER=demo-kafka:29092 \
    -e INFLUXDB_URL=http://demo-influxdb:8086 \
    -e INFLUXDB_TOKEN=demo-token-123 \
    -e INFLUXDB_ORG=metrics \
    -e INFLUXDB_BUCKET=metrics \
    demo-data-consumer
wait_for_service "data-consumer" 4692

# Start query-service
echo "Starting query-service..."
cleanup_container "demo-query-service"
docker run -d \
    --name demo-query-service \
    --network $NETWORK_NAME \
    -p 7539:7539 \
    -e INFLUXDB_URL=http://demo-influxdb:8086 \
    -e INFLUXDB_TOKEN=demo-token-123 \
    -e INFLUXDB_ORG=metrics \
    -e INFLUXDB_BUCKET=metrics \
    -e REDIS_HOST=demo-redis \
    -e REDIS_PORT=6379 \
    demo-query-service
wait_for_service "query-service" 7539

# Start alert-manager
echo "Starting alert-manager..."
cleanup_container "demo-alert-manager"
docker run -d \
    --name demo-alert-manager \
    --network $NETWORK_NAME \
    -p 6428:6428 \
    -e QUERY_SERVICE_HOST=demo-query-service \
    demo-alert-manager
wait_for_service "alert-manager" 6428

# Start dashboard
echo "Starting dashboard..."
cleanup_container "demo-dashboard"
docker run -d \
    --name demo-dashboard \
    --network $NETWORK_NAME \
    -p 5317:5317 \
    -e QUERY_SERVICE_URL=http://demo-query-service:7539 \
    -e ALERT_MANAGER_URL=http://demo-alert-manager:6428 \
    demo-dashboard
wait_for_service "dashboard" 5317

echo -e "\n${GREEN}Step 5: Starting Demo UI (Local Node.js)${NC}"

# Install dependencies and start demo UI locally
if [ -d "$UI_DIR" ]; then
    echo "Installing UI dependencies..."
    cd "$UI_DIR"
    npm install > /dev/null 2>&1
    
    echo "Starting demo UI locally..."
    # Kill any existing UI process on port 3000
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    # Start UI in background with local service URLs from UI directory
    cd "$UI_DIR"
    PORT=3000 METRICS_COLLECTOR_URL=http://localhost:9848 QUERY_SERVICE_URL=http://localhost:7539 ALERT_MANAGER_URL=http://localhost:6428 DASHBOARD_URL=http://localhost:5317 nohup npm start > ui.log 2>&1 &
    
    echo $! > "$UI_DIR/ui.pid"
    wait_for_service "demo-ui" 3000
fi

echo -e "\n${GREEN}Step 6: Starting Local Python Services${NC}"

# Start Metrics Collector locally
echo "Starting Metrics Collector locally..."
# Kill any existing process on port 9847
lsof -ti:9847 | xargs kill -9 2>/dev/null || true
cd "$DEMO_DIR/services/metrics-collector"
nohup env PYTHONPATH="$DEMO_DIR" python3 app.py > metrics-collector.log 2>&1 &
echo $! > "$DEMO_DIR/metrics-collector.pid"
wait_for_service "Metrics Collector" 9847

# Start Data Consumer locally  
echo "Starting Data Consumer locally..."
# Kill any existing process on port 4692
lsof -ti:4692 | xargs kill -9 2>/dev/null || true
cd "$DEMO_DIR/services/data-consumer"
nohup env PYTHONPATH="$DEMO_DIR" INFLUXDB_TOKEN=demo-token-123 INFLUXDB_ORG=metrics python3 app.py > data-consumer.log 2>&1 &
echo $! > "$DEMO_DIR/data-consumer.pid"
wait_for_service "Data Consumer" 4692

echo -e "\n${GREEN}Step 7: Creating Kafka Topics${NC}"
docker exec demo-kafka kafka-topics --create --topic metrics --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 2>/dev/null || echo "Topic 'metrics' already exists"

echo -e "\n================================================"
echo -e "${GREEN}   All services started successfully!${NC}"
echo -e "================================================"
echo -e "\nService URLs:"
echo -e "  ${YELLOW}Demo UI:${NC}          http://localhost:3000"
echo -e "  ${YELLOW}Dashboard:${NC}        http://localhost:5317"
echo -e "  ${YELLOW}Query Service:${NC}    http://localhost:7539"
echo -e "  ${YELLOW}Alert Manager:${NC}    http://localhost:6428"
echo -e "  ${YELLOW}Metrics Collector:${NC} http://localhost:9847"
echo -e "  ${YELLOW}InfluxDB:${NC}         http://localhost:8026"
echo -e "\nTo stop all services, run: ${GREEN}./scripts/stop.sh${NC}"
echo -e "To view Docker logs, run: ${GREEN}docker logs <container-name>${NC}"
echo -e "To view UI logs, run: ${GREEN}tail -f ui/ui.log${NC}"
echo -e "\nContainer names:"
echo -e "  demo-etcd, demo-redis, demo-zookeeper, demo-kafka, demo-influxdb"
echo -e "  demo-metrics-collector, demo-data-consumer, demo-query-service"
echo -e "  demo-alert-manager, demo-dashboard"
echo -e "\nLocal services:"
echo -e "  Demo UI: running on port 3000 (PID in ui/ui.pid)"
echo -e "  Metrics Collector: running on port 9847 (PID in metrics-collector.pid)"
echo -e "  Data Consumer: running on port 4692 (PID in data-consumer.pid)"
echo -e "\nLocal service logs:"
echo -e "  tail -f ui/ui.log"
echo -e "  tail -f services/metrics-collector/metrics-collector.log" 
echo -e "  tail -f services/data-consumer/data-consumer.log"