#!/bin/bash

echo "🛑 Stopping Google Drive MVP - All Services"
echo "==========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to stop and remove container
stop_container() {
    local container_name=$1
    local description=$2
    
    if docker ps -q -f name=$container_name | grep -q .; then
        echo -e "${YELLOW}🛑 Stopping $description...${NC}"
        docker stop $container_name > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ $description stopped${NC}"
        else
            echo -e "${RED}✗ Failed to stop $description${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️ $description is not running${NC}"
    fi
    
    # Remove container if it exists
    if docker ps -a -q -f name=$container_name | grep -q .; then
        docker rm $container_name > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ $description container removed${NC}"
        fi
    fi
}

echo -e "${BLUE}Step 1: Stopping UI Service${NC}"
echo "------------------------------"

# Stop UI Service (React App)
if [ -f "ui-service/ui-service.pid" ]; then
    UI_PID=$(cat ui-service/ui-service.pid)
    if ps -p $UI_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}🛑 Stopping UI Service...${NC}"
        kill $UI_PID 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ UI Service stopped${NC}"
        else
            echo -e "${RED}✗ Failed to stop UI Service${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️ UI Service is not running${NC}"
    fi
    rm -f ui-service/ui-service.pid
    rm -f ui-service/ui-service.log
    echo -e "${GREEN}✓ UI Service files cleaned up${NC}"
else
    echo -e "${BLUE}ℹ️ No UI Service PID file found${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Stopping Application Services${NC}"
echo "------------------------------------"

# Stop Application Services
stop_container "api-gateway" "API Gateway"
stop_container "notification-service" "Notification Service"
stop_container "block-service" "Block Service"
stop_container "metadata-service" "Metadata Service"
stop_container "file-service" "File Service"
stop_container "auth-service" "Auth Service"

echo ""
echo -e "${BLUE}Step 3: Stopping Infrastructure Services${NC}"
echo "----------------------------------------"

# Stop Infrastructure Services
stop_container "minio-gdrive" "MinIO"
stop_container "redis-gdrive" "Redis"
stop_container "postgres-gdrive" "PostgreSQL"

echo ""
echo -e "${BLUE}Step 4: Cleanup${NC}"
echo "---------------"

# Remove any orphaned containers
echo -e "${YELLOW}🧹 Cleaning up orphaned containers...${NC}"
orphaned=$(docker ps -a --filter "status=exited" -q)
if [ ! -z "$orphaned" ]; then
    docker rm $orphaned > /dev/null 2>&1
    echo -e "${GREEN}✓ Orphaned containers cleaned up${NC}"
else
    echo -e "${BLUE}ℹ️ No orphaned containers found${NC}"
fi

# Optional: Remove unused networks
echo -e "${YELLOW}🌐 Cleaning up unused networks...${NC}"
docker network prune -f > /dev/null 2>&1
echo -e "${GREEN}✓ Unused networks cleaned up${NC}"

# Optional: Remove dangling images
echo -e "${YELLOW}🖼️ Cleaning up dangling images...${NC}"
dangling=$(docker images -f "dangling=true" -q)
if [ ! -z "$dangling" ]; then
    docker rmi $dangling > /dev/null 2>&1
    echo -e "${GREEN}✓ Dangling images cleaned up${NC}"
else
    echo -e "${BLUE}ℹ️ No dangling images found${NC}"
fi

echo ""
echo "==========================================="
echo -e "${GREEN}🎯 ALL SERVICES STOPPED SUCCESSFULLY!${NC}"
echo ""
echo -e "${BLUE}What was stopped:${NC}"
echo "🎨 UI Service (port 3000)"
echo "🌐 API Gateway (port 9010)"
echo "🔔 Notification Service (port 9005)"
echo "🧱 Block Service (port 9004)"
echo "📋 Metadata Service (port 9003)"
echo "📁 File Service (port 9012)"
echo "🔐 Auth Service (port 9011)"
echo "🪣 MinIO (ports 9000-9001)"
echo "🔴 Redis (port 6379)"
echo "🗄️ PostgreSQL (port 5432)"
echo ""
echo -e "${YELLOW}All containers removed and ports freed.${NC}"
echo -e "${GREEN}System is clean and ready for restart.${NC}"