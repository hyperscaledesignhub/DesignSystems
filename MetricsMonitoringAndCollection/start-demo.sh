#!/bin/bash

# Metrics Monitoring System - Demo Launcher
# One-command demo startup with validation

set -e

echo "======================================================"
echo "    Metrics Monitoring System - Demo Launcher        "
echo "======================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check available memory
available_mem=$(docker info --format '{{.MemTotal}}' 2>/dev/null | awk '{print int($1/1024/1024/1024)}')
if [ "$available_mem" -lt 6 ]; then
    echo -e "${YELLOW}Warning: Less than 6GB RAM available. Demo may run slowly.${NC}"
fi

# Check ports
echo "Checking required ports..."
required_ports=(2379 2181 5317 6379 6428 7539 8026 8080 9293 9847 4692)
for port in "${required_ports[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}Port $port is already in use. Please stop the service using it.${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ All prerequisites satisfied${NC}"

# Start services
echo -e "\n${GREEN}Starting demo services...${NC}"
./scripts/startup.sh

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for all services to be ready...${NC}"
sleep 30

# Health check
echo -e "\n${YELLOW}Performing health checks...${NC}"
services=(
    "http://localhost:9847/health|Metrics Collector"
    "http://localhost:7539/health|Query Service"
    "http://localhost:6428/health|Alert Manager"
    "http://localhost:3000|Demo UI"
)

all_healthy=true
for service in "${services[@]}"; do
    url=$(echo $service | cut -d'|' -f1)
    name=$(echo $service | cut -d'|' -f2)
    
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name is healthy${NC}"
    else
        echo -e "${RED}✗ $name is not responding${NC}"
        all_healthy=false
    fi
done

echo ""
if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}🎉 Demo is ready!${NC}"
    echo ""
    echo -e "Access points:"
    echo -e "  ${YELLOW}Interactive Demo UI:${NC} http://localhost:3000"
    echo -e "  ${YELLOW}Main Dashboard:${NC}     http://localhost:5317"
    echo -e "  ${YELLOW}InfluxDB UI:${NC}        http://localhost:8026"
    echo ""
    echo -e "To stop the demo: ${GREEN}./scripts/stop.sh${NC}"
    echo ""
    echo -e "${YELLOW}Starting data generator in 10 seconds...${NC}"
    sleep 10
    
    # Start data generator in background
    if [ -f "data/generator.py" ]; then
        echo "Starting data generator..."
        nohup python3 data/generator.py --types cpu memory network application > /dev/null 2>&1 &
        echo "Data generator PID: $!"
    fi
    
    # Open demo UI in browser (if available)
    if command -v open &> /dev/null; then
        open http://localhost:3000
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:3000
    else
        echo "Please open http://localhost:3000 in your browser"
    fi
    
else
    echo -e "${RED}⚠️  Some services are not healthy. Check logs with:${NC}"
    echo "docker logs <container-name>"
fi