#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Complete Proximity Service Demo${NC}"
echo "============================================"

# Start backend services
echo -e "${YELLOW}🏗️  Starting backend services...${NC}"
./start-demo.sh

# Wait a moment for services to stabilize
echo -e "${YELLOW}⏳ Waiting for services to stabilize...${NC}"
sleep 5

# Start UI
echo -e "${YELLOW}🌐 Starting demo UI...${NC}"
./start-ui.sh

echo -e "\n${GREEN}🎉 Complete demo is now running!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}🌐 Demo UI:${NC}       http://localhost:8081"
echo -e "${BLUE}📡 API Gateway:${NC}   http://localhost:7891/api/v1/*"
echo -e "${BLUE}🔍 Location API:${NC}  http://localhost:8921"
echo -e "${BLUE}🏢 Business API:${NC}  http://localhost:9823"
echo ""
echo -e "${YELLOW}🛑 To stop everything, run:${NC} ./stop-full-demo.sh"
echo -e "${YELLOW}📖 To view backend logs:${NC} docker-compose logs -f"
echo -e "${YELLOW}📖 To view UI logs:${NC} tail -f ui.log"
echo ""