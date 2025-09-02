#!/bin/bash

# Search Autocomplete System - Simple Stop Script  
# Stops all Docker services + Native UI

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Search Autocomplete System${NC}"
echo

# Stop UI server
echo -e "${YELLOW}Stopping UI Server...${NC}"
if [ -f "/tmp/autocomplete_ui_pid" ]; then
    UI_PID=$(cat /tmp/autocomplete_ui_pid)
    if kill -0 "$UI_PID" 2>/dev/null; then
        kill "$UI_PID" 2>/dev/null
        echo -e "${GREEN}✅ UI Server stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  UI Server was not running${NC}"
    fi
    rm -f /tmp/autocomplete_ui_pid
else
    echo -e "${YELLOW}⚠️  No UI Server PID file found${NC}"
fi

# Stop and remove all Docker containers
echo -e "${YELLOW}Stopping Docker containers...${NC}"
containers=$(docker ps -q --filter "name=autocomplete-" 2>/dev/null || true)
if [ ! -z "$containers" ]; then
    docker stop $containers 2>/dev/null || true
    echo -e "${GREEN}✅ All containers stopped${NC}"
else
    echo -e "${YELLOW}⚠️  No containers were running${NC}"
fi

echo -e "${YELLOW}Removing Docker containers...${NC}"
containers=$(docker ps -aq --filter "name=autocomplete-" 2>/dev/null || true)
if [ ! -z "$containers" ]; then
    docker rm $containers 2>/dev/null || true
    echo -e "${GREEN}✅ All containers removed${NC}"
else
    echo -e "${YELLOW}⚠️  No containers to remove${NC}"
fi

# Remove network
echo -e "${YELLOW}Removing Docker network...${NC}"
docker network rm autocomplete-net 2>/dev/null || true
echo -e "${GREEN}✅ Docker network removed${NC}"

# Also kill any remaining processes on our ports (cleanup)
echo -e "${YELLOW}Checking for remaining processes...${NC}"
ports=(12893 13761 15294 14742 11845 12847)
for port in "${ports[@]}"; do
    pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}Killing process on port $port (PID: $pid)${NC}"
        kill -9 "$pid" 2>/dev/null || true
    fi
done

echo
echo -e "${GREEN}🎉 All services stopped successfully!${NC}"
echo -e "${YELLOW}📝 System is completely shut down${NC}"
echo