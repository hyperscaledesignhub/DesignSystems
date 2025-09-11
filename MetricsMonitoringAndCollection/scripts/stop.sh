#!/bin/bash

# Metrics Monitoring System - Individual Docker Container Stop Script
# This script stops and removes all service containers

set -e

echo "================================================"
echo "   Metrics Monitoring System - Demo Shutdown   "
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NETWORK_NAME="metrics-network"

# Function to stop and remove container
stop_container() {
    local container=$1
    if docker ps -a --format "table {{.Names}}" | grep -q "^$container$"; then
        echo -e "Stopping ${YELLOW}$container${NC}..."
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    else
        echo -e "Container ${YELLOW}$container${NC} not found, skipping..."
    fi
}

echo -e "\n${RED}Step 1: Stopping Local Services${NC}"

# Stop local UI service
echo -e "Stopping local ${YELLOW}Demo UI${NC}..."
DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UI_PID_FILE="$DEMO_DIR/ui/ui.pid"
if [ -f "$UI_PID_FILE" ]; then
    UI_PID=$(cat "$UI_PID_FILE")
    if ps -p $UI_PID > /dev/null 2>&1; then
        echo "Killing UI process (PID: $UI_PID)"
        kill $UI_PID 2>/dev/null || true
        rm -f "$UI_PID_FILE"
    else
        echo "UI process not found"
        rm -f "$UI_PID_FILE"
    fi
else
    echo "No UI PID file found, trying to kill by port..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

# Stop local Metrics Collector
echo -e "Stopping local ${YELLOW}Metrics Collector${NC}..."
METRICS_COLLECTOR_PID_FILE="$DEMO_DIR/metrics-collector.pid"
if [ -f "$METRICS_COLLECTOR_PID_FILE" ]; then
    METRICS_COLLECTOR_PID=$(cat "$METRICS_COLLECTOR_PID_FILE")
    if ps -p $METRICS_COLLECTOR_PID > /dev/null 2>&1; then
        echo "Killing Metrics Collector process (PID: $METRICS_COLLECTOR_PID)"
        kill $METRICS_COLLECTOR_PID 2>/dev/null || true
        rm -f "$METRICS_COLLECTOR_PID_FILE"
    else
        echo "Metrics Collector process not found"
        rm -f "$METRICS_COLLECTOR_PID_FILE"
    fi
else
    echo "No Metrics Collector PID file found, trying to kill by port..."
    lsof -ti:9847 | xargs kill -9 2>/dev/null || true
fi

# Stop local Data Consumer
echo -e "Stopping local ${YELLOW}Data Consumer${NC}..."
DATA_CONSUMER_PID_FILE="$DEMO_DIR/data-consumer.pid"
if [ -f "$DATA_CONSUMER_PID_FILE" ]; then
    DATA_CONSUMER_PID=$(cat "$DATA_CONSUMER_PID_FILE")
    if ps -p $DATA_CONSUMER_PID > /dev/null 2>&1; then
        echo "Killing Data Consumer process (PID: $DATA_CONSUMER_PID)"
        kill $DATA_CONSUMER_PID 2>/dev/null || true
        rm -f "$DATA_CONSUMER_PID_FILE"
    else
        echo "Data Consumer process not found"
        rm -f "$DATA_CONSUMER_PID_FILE"
    fi
else
    echo "No Data Consumer PID file found, trying to kill by port..."
    lsof -ti:4692 | xargs kill -9 2>/dev/null || true
fi

echo -e "\n${RED}Step 2: Stopping Docker Services${NC}"

stop_container "demo-dashboard"
stop_container "demo-alert-manager"
stop_container "demo-query-service"
stop_container "demo-data-consumer"
stop_container "demo-metrics-collector"

echo -e "\n${RED}Step 3: Stopping Infrastructure Services${NC}"
stop_container "demo-influxdb"
stop_container "demo-kafka"
stop_container "demo-zookeeper"
stop_container "demo-redis"
stop_container "demo-etcd"

echo -e "\n${RED}Step 4: Removing Docker Network${NC}"
if docker network ls | grep -q "$NETWORK_NAME"; then
    echo "Removing network $NETWORK_NAME..."
    docker network rm $NETWORK_NAME 2>/dev/null || echo "Network may still have connected containers"
else
    echo "Network $NETWORK_NAME not found"
fi

echo -e "\n${RED}Step 5: Cleaning up Docker Resources${NC}"
echo "Removing unused containers..."
docker container prune -f 2>/dev/null || true

echo "Removing unused images (optional)..."
read -p "Do you want to remove unused Docker images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker image prune -f
fi

echo -e "\n================================================"
echo -e "${GREEN}   All services stopped successfully!${NC}"
echo -e "================================================"
echo -e "\nStopped services:"
echo -e "  ${YELLOW}Local Services:${NC}"
echo -e "    - Demo UI (port 3000)"
echo -e "    - Metrics Collector (port 9847)"
echo -e "    - Data Consumer (port 4692)"
echo -e "  ${YELLOW}Docker Services:${NC}"
echo -e "    - Dashboard, Alert Manager, Query Service"
echo -e "    - InfluxDB, Kafka, Zookeeper, Redis, etcd"
echo -e "\nTo restart services, run: ${GREEN}./scripts/startup.sh${NC}"