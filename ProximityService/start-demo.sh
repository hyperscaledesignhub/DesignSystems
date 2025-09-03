#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Proximity Service Demo${NC}"
echo "================================"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose is not installed or not in PATH${NC}"
    exit 1
fi

# Stop any existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down

# Build all services
echo -e "${YELLOW}🔨 Building all services...${NC}"
docker-compose build

# Start all services
echo -e "${YELLOW}🔄 Starting all services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Check service health
echo -e "${BLUE}🏥 Checking service health...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check API Gateway
if curl -s http://localhost:7891/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API Gateway: http://localhost:7891${NC}"
else
    echo -e "${RED}❌ API Gateway: Failed to start${NC}"
fi

# Check Location Service
if curl -s http://localhost:8921/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Location Service: http://localhost:8921${NC}"
else
    echo -e "${RED}❌ Location Service: Failed to start${NC}"
fi

# Check Business Service
if curl -s http://localhost:9823/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Business Service: http://localhost:9823${NC}"
else
    echo -e "${RED}❌ Business Service: Failed to start${NC}"
fi

# Demo UI is separate - use ./start-ui.sh

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Generate demo data
echo -e "${YELLOW}📊 Generating demo data...${NC}"
if python3 demo/generate_data.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Demo data generated successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Demo data generation failed (services may still be starting)${NC}"
fi

# Show service status
echo -e "\n${BLUE}📊 Service Status:${NC}"
docker-compose ps

echo -e "\n${GREEN}🎉 Backend services are ready!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}📡 API Gateway:${NC}   http://localhost:7891/api/v1/*"
echo -e "${BLUE}🔍 Location API:${NC}  http://localhost:8921"
echo -e "${BLUE}🏢 Business API:${NC}  http://localhost:9823"
echo ""
echo -e "${YELLOW}🌐 To start the Demo UI, run:${NC} ./start-ui.sh"
echo -e "${YELLOW}🛑 To stop the backend, run:${NC} ./stop-demo.sh"
echo -e "${YELLOW}📖 To view logs, run:${NC} docker-compose logs -f"
echo ""