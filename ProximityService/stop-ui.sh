#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Proximity Service Demo UI${NC}"
echo "===================================="

# Check for stored PID
if [ -f ".ui.pid" ]; then
    UI_PID=$(cat .ui.pid)
    if kill -0 $UI_PID 2>/dev/null; then
        echo -e "${YELLOW}🔄 Stopping UI server (PID: $UI_PID)...${NC}"
        kill $UI_PID
        sleep 2
        
        # Force kill if still running
        if kill -0 $UI_PID 2>/dev/null; then
            echo -e "${YELLOW}🔨 Force stopping UI server...${NC}"
            kill -9 $UI_PID
        fi
        
        echo -e "${GREEN}✅ UI server stopped successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  UI server (PID: $UI_PID) was not running${NC}"
    fi
    
    # Clean up PID file
    rm .ui.pid
else
    # Try to find and kill any UI server process
    UI_PID=$(pgrep -f "python3.*http.server.*8081" 2>/dev/null)
    if [ ! -z "$UI_PID" ]; then
        echo -e "${YELLOW}🔄 Found UI server process (PID: $UI_PID), stopping...${NC}"
        kill $UI_PID
        sleep 2
        
        # Force kill if still running
        if kill -0 $UI_PID 2>/dev/null; then
            kill -9 $UI_PID
        fi
        
        echo -e "${GREEN}✅ UI server stopped successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  No UI server process found running on port 8081${NC}"
    fi
fi

# Check if port is now free
if lsof -i :8081 > /dev/null 2>&1; then
    echo -e "${RED}❌ Port 8081 is still busy. Manual cleanup needed:${NC}"
    echo -e "${YELLOW}lsof -i :8081${NC}"
    echo -e "${YELLOW}kill -9 [PID]${NC}"
else
    echo -e "${GREEN}✅ Port 8081 is now free${NC}"
fi

echo ""
echo -e "${YELLOW}💡 To start the UI again, run:${NC} ./start-ui.sh"
echo -e "${YELLOW}🏢 To start backend services, run:${NC} ./start-demo.sh"
echo ""