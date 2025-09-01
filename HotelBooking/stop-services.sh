#!/bin/bash

echo "Stopping Hotel Booking System Services..."
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Stop Frontend UI
echo -e "${GREEN}Stopping Frontend UI...${NC}"
if [ -f frontend.pid ]; then
    PID=$(cat frontend.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null
        echo "Frontend UI stopped"
    else
        echo "Frontend UI process not found"
    fi
    rm frontend.pid
else
    # Try to find and kill npm start process
    pkill -f "npm start" 2>/dev/null
    pkill -f "react-scripts start" 2>/dev/null
    echo "Attempted to stop Frontend UI process"
fi

# Stop all Docker containers
echo -e "\n${GREEN}Stopping Docker containers...${NC}"
containers=("hotel-service" "room-service" "guest-service" "inventory-service" "reservation-service" "payment-service" "postgres-db" "redis-cache")

for container in "${containers[@]}"; do
    if docker ps | grep -q $container; then
        docker stop $container
        docker rm $container
        echo -e "${GREEN}✓${NC} Stopped and removed $container"
    else
        echo -e "  $container was not running"
    fi
done

# Clean up any remaining containers
echo -e "\n${GREEN}Cleaning up any remaining containers...${NC}"
docker ps -aq | xargs -r docker rm -f 2>/dev/null

echo -e "\n${GREEN}All services stopped!${NC}"
echo "========================================="