#!/bin/bash

# Distributed Message Queue Demo - Stop Script
# This script stops all Docker containers and the UI Python process

echo "======================================"
echo "Stopping Distributed Message Queue Demo"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Stop UI Python Service (non-Docker)
echo -e "${YELLOW}Stopping UI Service (Python process)...${NC}"
if [ -f ui/ui.pid ]; then
    UI_PID=$(cat ui/ui.pid)
    if ps -p $UI_PID > /dev/null 2>&1; then
        echo "Stopping UI process (PID: $UI_PID)..."
        kill $UI_PID 2>/dev/null
        sleep 2
        # Force kill if still running
        if ps -p $UI_PID > /dev/null 2>&1; then
            echo "Force stopping UI process..."
            kill -9 $UI_PID 2>/dev/null
        fi
        echo "UI process stopped"
    else
        echo "UI process not running (PID: $UI_PID)"
    fi
    rm -f ui/ui.pid
else
    echo "No UI PID file found. Checking for running UI processes..."
    # Try to find and kill any running UI process
    pkill -f "python.*ui/app.py" 2>/dev/null || echo "No UI process found"
fi

# Clean up UI log file
if [ -f ui/ui.log ]; then
    echo "Cleaning up UI log file..."
    rm -f ui/ui.log
fi

# Stop and remove Monitoring Service
echo -e "${YELLOW}Stopping Monitoring Service...${NC}"
docker stop msgqueue-monitoring 2>/dev/null && docker rm msgqueue-monitoring 2>/dev/null || echo "Monitoring service not running"

# Stop and remove API Gateway Service
echo -e "${YELLOW}Stopping API Gateway Service...${NC}"
docker stop msgqueue-gateway 2>/dev/null && docker rm msgqueue-gateway 2>/dev/null || echo "Gateway service not running"

# Stop and remove Consumer Services
echo -e "${YELLOW}Stopping Consumer Services...${NC}"
for i in 1 2; do
  docker stop msgqueue-consumer-$i 2>/dev/null && docker rm msgqueue-consumer-$i 2>/dev/null || echo "Consumer $i not running"
done

# Stop and remove Producer Service
echo -e "${YELLOW}Stopping Producer Service...${NC}"
docker stop msgqueue-producer 2>/dev/null && docker rm msgqueue-producer 2>/dev/null || echo "Producer service not running"

# Stop and remove Broker Services
echo -e "${YELLOW}Stopping Broker Services...${NC}"
for i in 1 2 3; do
  docker stop msgqueue-broker-$i 2>/dev/null && docker rm msgqueue-broker-$i 2>/dev/null || echo "Broker $i not running"
done

# Stop and remove Coordinator Service
echo -e "${YELLOW}Stopping Coordinator Service...${NC}"
docker stop msgqueue-coordinator 2>/dev/null && docker rm msgqueue-coordinator 2>/dev/null || echo "Coordinator service not running"

# Optional: Remove Docker network
echo -e "${YELLOW}Removing Docker network...${NC}"
docker network rm msgqueue-network 2>/dev/null || echo "Network already removed or doesn't exist"

# Optional: Clean up volumes (uncomment if you want to remove persistent data)
# echo -e "${YELLOW}Removing data volumes...${NC}"
# for i in 1 2 3; do
#   docker volume rm msgqueue-broker-data-$i 2>/dev/null || echo "Volume broker-data-$i doesn't exist"
# done

echo ""
echo -e "${GREEN}======================================"
echo "All services stopped successfully!"
echo "======================================"
echo ""
echo "To remove Docker images as well, run:"
echo "  docker rmi msgqueue-monitoring msgqueue-gateway msgqueue-consumer msgqueue-producer msgqueue-broker msgqueue-coordinator"
echo ""
echo "To remove data volumes, run:"
echo "  docker volume rm msgqueue-broker-data-1 msgqueue-broker-data-2 msgqueue-broker-data-3"
echo -e "${NC}"

# Show any remaining containers with msgqueue prefix
REMAINING=$(docker ps -a --filter "name=msgqueue-" --format "{{.Names}}" | wc -l)
if [ $REMAINING -gt 0 ]; then
  echo -e "${RED}Warning: Some containers may still be running:${NC}"
  docker ps -a --filter "name=msgqueue-" --format "table {{.Names}}\t{{.Status}}"
fi

# Check for any remaining UI processes
UI_PROCESSES=$(pgrep -f "python.*ui/app.py" | wc -l)
if [ $UI_PROCESSES -gt 0 ]; then
  echo -e "${RED}Warning: UI process may still be running${NC}"
  ps aux | grep "ui/app.py" | grep -v grep
fi