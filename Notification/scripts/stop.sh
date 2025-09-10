#!/bin/bash

# Notification System Demo - Stop Script
# This script stops all services and cleans up

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping Notification System Demo${NC}"
echo "======================================="

# Stop UI service if running
if [ -f "ui.pid" ]; then
  UI_PID=$(cat ui.pid)
  if ps -p $UI_PID > /dev/null 2>&1; then
    echo -e "${YELLOW}Stopping UI service (PID: $UI_PID)...${NC}"
    kill $UI_PID 2>/dev/null || true
    rm ui.pid
  else
    echo "UI service not running"
    rm ui.pid
  fi
else
  echo "No UI PID file found"
fi

# Stop and remove Docker containers
echo -e "${YELLOW}Stopping Docker containers...${NC}"

CONTAINERS=(
  "api-gateway"
  "notification-server"
  "email-worker"
  "sms-worker"
  "push-worker"
  "user-database"
  "redis-service"
)

for container in "${CONTAINERS[@]}"; do
  if docker ps -a | grep -q $container; then
    echo "  Stopping $container..."
    docker stop $container 2>/dev/null || true
    docker rm $container 2>/dev/null || true
  fi
done

# Remove network
echo -e "${YELLOW}Removing Docker network...${NC}"
docker network rm notification-network 2>/dev/null || echo "Network already removed"

echo ""
echo -e "${GREEN}✅ All services stopped successfully!${NC}"
echo ""

# Ask if user wants to clean up data
read -p "Do you want to clean up persistent data (Redis, SQLite)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Cleaning up data...${NC}"
  rm -rf ../data/redis/* 2>/dev/null || true
  rm -rf ../data/sqlite/* 2>/dev/null || true
  echo -e "${GREEN}Data cleaned up!${NC}"
fi

echo ""
echo -e "${GREEN}Cleanup complete!${NC}"