#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Complete Proximity Service Demo${NC}"
echo "============================================="

# Stop UI first
echo -e "${YELLOW}🌐 Stopping demo UI...${NC}"
./stop-ui.sh

# Stop backend services
echo -e "${YELLOW}🏗️  Stopping backend services...${NC}"
./stop-demo.sh

echo -e "\n${GREEN}✅ Complete demo stopped successfully${NC}"
echo ""
echo -e "${YELLOW}💡 To start the complete demo again, run:${NC} ./start-full-demo.sh"
echo -e "${YELLOW}🏗️  To start only backend services, run:${NC} ./start-demo.sh"
echo -e "${YELLOW}🌐 To start only the UI, run:${NC} ./start-ui.sh"
echo ""