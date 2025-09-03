#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Proximity Service Demo${NC}"
echo "=================================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose is not installed or not in PATH${NC}"
    exit 1
fi

# Show current running containers
echo -e "${YELLOW}📊 Current running containers:${NC}"
docker-compose ps

# Stop all services
echo -e "\n${YELLOW}🔄 Stopping all services...${NC}"
docker-compose down

# Optional: Remove volumes (uncomment if you want to clear all data)
# echo -e "${YELLOW}🗑️  Removing volumes...${NC}"
# docker-compose down -v

# Optional: Remove images (uncomment if you want to remove built images)
# echo -e "${YELLOW}🗑️  Removing images...${NC}"
# docker-compose down --rmi all

echo -e "\n${GREEN}✅ All services stopped successfully${NC}"
echo ""
echo -e "${YELLOW}💡 To start the demo again, run:${NC} ./start-demo.sh"
echo -e "${YELLOW}🧹 To clean up everything (volumes, images), run:${NC} docker-compose down -v --rmi all"
echo ""