#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌐 Starting Proximity Service Demo UI${NC}"
echo "====================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ python3 is not installed or not in PATH${NC}"
    exit 1
fi

# Check if demo directory exists
if [ ! -d "demo" ]; then
    echo -e "${RED}❌ Demo directory not found${NC}"
    exit 1
fi

# Check if services are running
echo -e "${YELLOW}🔍 Checking if backend services are running...${NC}"
if curl -s http://localhost:7891/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend services are running${NC}"
else
    echo -e "${YELLOW}⚠️  Backend services not detected. Start them with: ./start-demo.sh${NC}"
fi

# Kill any existing UI server
UI_PID=$(pgrep -f "python3.*http.server.*8081" 2>/dev/null)
if [ ! -z "$UI_PID" ]; then
    echo -e "${YELLOW}🛑 Stopping existing UI server (PID: $UI_PID)...${NC}"
    kill $UI_PID
    sleep 2
fi

# Check if port 8081 is available
if lsof -i :8081 > /dev/null 2>&1; then
    echo -e "${RED}❌ Port 8081 is busy. Free it up first:${NC}"
    echo -e "${YELLOW}lsof -i :8081${NC}"
    echo -e "${YELLOW}kill -9 [PID]${NC}"
    exit 1
fi

# Start the UI server in background
echo -e "${YELLOW}🚀 Starting UI server on port 8081...${NC}"
cd demo
nohup python3 -m http.server 8081 > ../ui.log 2>&1 &
UI_PID=$!
cd ..

# Save PID for stopping later
echo $UI_PID > .ui.pid

# Wait a moment and check if it started
sleep 2
if kill -0 $UI_PID 2>/dev/null; then
    echo -e "${GREEN}✅ UI server started successfully (PID: $UI_PID)${NC}"
    echo ""
    echo -e "${BLUE}🌐 Demo UI:${NC} http://localhost:8081"
    echo -e "${BLUE}📊 Features:${NC}"
    echo "  • Interactive map with business locations"
    echo "  • Search businesses by location and radius"
    echo "  • Create, edit, and delete businesses"
    echo "  • Database and Redis failover testing"
    echo "  • Real-time health monitoring dashboard"
    echo ""
    echo -e "${YELLOW}💡 To stop the UI, run:${NC} ./stop-ui.sh"
    echo -e "${YELLOW}📖 To view UI logs, run:${NC} tail -f ui.log"
else
    echo -e "${RED}❌ Failed to start UI server${NC}"
    if [ -f .ui.pid ]; then
        rm .ui.pid
    fi
    exit 1
fi