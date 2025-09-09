#!/bin/bash

# Distributed Message Queue Demo - Startup Script
# This script starts all services as individual Docker containers
# UI runs as a non-Docker Python service

set -e

echo "======================================"
echo "Starting Distributed Message Queue Demo"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Network name
NETWORK_NAME="msgqueue-network"

# Create network if it doesn't exist
echo -e "${YELLOW}Creating Docker network...${NC}"
docker network create $NETWORK_NAME 2>/dev/null || echo "Network already exists"

# Build and run Coordinator Service (needs to start first)
echo -e "${GREEN}Building and starting Coordinator Service...${NC}"
docker build --no-cache -t msgqueue-coordinator -f coordinator/Dockerfile .
docker run -d \
  --name msgqueue-coordinator \
  --network $NETWORK_NAME \
  -p 19004:19004 \
  -e COORDINATOR_HOST=0.0.0.0 \
  -e COORDINATOR_PORT=19004 \
  msgqueue-coordinator

# Wait for coordinator to be ready
echo "Waiting for Coordinator to be ready..."
sleep 5

# Build and run Broker Services (3 instances for replication)
echo -e "${GREEN}Building and starting Broker Services...${NC}"
docker build --no-cache -t msgqueue-broker -f broker/Dockerfile .

for i in 1 2 3; do
  echo "Starting Broker instance $i..."
  docker run -d \
    --name msgqueue-broker-$i \
    --network $NETWORK_NAME \
    -p $((19000 + i)):19001 \
    -v msgqueue-broker-data-$i:/data/broker \
    -e BROKER_ID=$i \
    -e BROKER_HOST=msgqueue-broker-$i \
    -e BROKER_PORT=19001 \
    -e COORDINATOR_URL=http://msgqueue-coordinator:19004 \
    msgqueue-broker
  sleep 2
done

# Build and run Producer Service
echo -e "${GREEN}Building and starting Producer Service...${NC}"
docker build --no-cache -t msgqueue-producer -f producer/Dockerfile .
docker run -d \
  --name msgqueue-producer \
  --network $NETWORK_NAME \
  -p 19007:19002 \
  -e PRODUCER_HOST=0.0.0.0 \
  -e PRODUCER_PORT=19002 \
  -e BROKER_URLS=http://msgqueue-broker-1:19001,http://msgqueue-broker-2:19001,http://msgqueue-broker-3:19001 \
  -e COORDINATOR_URL=http://msgqueue-coordinator:19004 \
  msgqueue-producer

# Build and run Consumer Services (2 instances for consumer group demo)
echo -e "${GREEN}Building and starting Consumer Services...${NC}"
docker build --no-cache -t msgqueue-consumer -f consumer/Dockerfile .

for i in 1 2; do
  echo "Starting Consumer instance $i..."
  docker run -d \
    --name msgqueue-consumer-$i \
    --network $NETWORK_NAME \
    -p $((19007 + i)):19003 \
    -e CONSUMER_ID=consumer-$i \
    -e CONSUMER_GROUP=demo-group \
    -e CONSUMER_HOST=0.0.0.0 \
    -e CONSUMER_PORT=19003 \
    -e BROKER_URLS=http://msgqueue-broker-1:19001,http://msgqueue-broker-2:19001,http://msgqueue-broker-3:19001 \
    -e COORDINATOR_URL=http://msgqueue-coordinator:19004 \
    msgqueue-consumer
  sleep 2
done

# Build and run API Gateway Service
echo -e "${GREEN}Building and starting API Gateway Service...${NC}"
docker build --no-cache -t msgqueue-gateway -f gateway/Dockerfile .
docker run -d \
  --name msgqueue-gateway \
  --network $NETWORK_NAME \
  -p 19005:19005 \
  -e GATEWAY_HOST=0.0.0.0 \
  -e GATEWAY_PORT=19005 \
  -e PRODUCER_URL=http://msgqueue-producer:19002 \
  -e CONSUMER_URL=http://msgqueue-consumer-1:19003 \
  -e BROKER_URL=http://msgqueue-broker-1:19001 \
  -e COORDINATOR_URL=http://msgqueue-coordinator:19004 \
  msgqueue-gateway

# Build and run Monitoring Service
echo -e "${GREEN}Building and starting Monitoring Service...${NC}"
docker build --no-cache -t msgqueue-monitoring -f monitoring/Dockerfile .
docker run -d \
  --name msgqueue-monitoring \
  --network $NETWORK_NAME \
  -p 19006:19006 \
  -e MONITORING_HOST=0.0.0.0 \
  -e MONITORING_PORT=19006 \
  -e SERVICE_URLS=http://msgqueue-broker-1:19001,http://msgqueue-broker-2:19001,http://msgqueue-broker-3:19001,http://msgqueue-producer:19002,http://msgqueue-consumer-1:19003,http://msgqueue-consumer-2:19003,http://msgqueue-coordinator:19004,http://msgqueue-gateway:19005 \
  msgqueue-monitoring

# Start UI as a non-Docker Python service
echo -e "${GREEN}Starting UI Service (non-Docker)...${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 to run the UI.${NC}"
    exit 1
fi

# Install UI dependencies if needed
echo "Installing UI dependencies..."
pip3 install fastapi uvicorn aiohttp --quiet 2>/dev/null || pip install fastapi uvicorn aiohttp --quiet 2>/dev/null || true

# Start UI in background
echo "Starting UI server on port 8080..."
export GATEWAY_URL=http://localhost:19005
export MONITORING_URL=http://localhost:19006
export UI_PORT=8080

# Create a PID file for the UI process
nohup python3 ui/app.py > ui/ui.log 2>&1 &
UI_PID=$!
echo $UI_PID > ui/ui.pid
echo "UI Service started with PID: $UI_PID"

# Wait a moment for UI to start
sleep 3

# Check if UI is running
if ps -p $UI_PID > /dev/null; then
    echo -e "${GREEN}UI Service is running on http://localhost:8080${NC}"
else
    echo -e "${RED}UI Service failed to start. Check ui/ui.log for details.${NC}"
fi

echo ""
echo -e "${GREEN}======================================"
echo "All services started successfully!"
echo "======================================"
echo ""
echo "Service URLs:"
echo "  - UI Dashboard: http://localhost:8080 (Python process)"
echo "  - API Gateway: http://localhost:19005"
echo "  - Monitoring: http://localhost:19006"
echo "  - Coordinator: http://localhost:19004"
echo "  - Broker 1: http://localhost:19001"
echo "  - Broker 2: http://localhost:19002"
echo "  - Broker 3: http://localhost:19003"
echo "  - Producer: http://localhost:19007"
echo "  - Consumer 1: http://localhost:19008"
echo "  - Consumer 2: http://localhost:19009"
echo ""
echo "To stop all services, run: ./scripts/stop.sh"
echo -e "${NC}"

# Show running containers
echo "Running Docker containers:"
docker ps --filter "name=msgqueue-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "UI Process Status:"
if ps -p $UI_PID > /dev/null; then
    echo "  UI Server (PID: $UI_PID) - Running on port 8080"
else
    echo "  UI Server - Not running"
fi