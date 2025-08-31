#!/bin/bash

# Start S3 Storage System with Web UI
# Complete setup script for customers

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🌐 S3 Storage System with Web UI${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl not found${NC}"
    echo "Please install curl"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies OK${NC}"
echo ""

# Start services
echo -e "${BLUE}Starting S3 Storage System...${NC}"
docker-compose -f docker-compose-with-ui.yml up -d

echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 60

# Check if services are healthy
echo -e "${BLUE}Checking service health...${NC}"

services=("postgresql" "identity-service" "bucket-service" "storage-service" "metadata-service" "object-service" "api-gateway" "web-ui")
healthy_services=0

for service in "${services[@]}"; do
    if docker-compose -f docker-compose-with-ui.yml ps | grep "$service" | grep -q "healthy\|Up"; then
        echo -e "${GREEN}✅ $service${NC}"
        healthy_services=$((healthy_services + 1))
    else
        echo -e "${RED}❌ $service${NC}"
    fi
done

if [ $healthy_services -eq ${#services[@]} ]; then
    echo -e "${GREEN}✅ All services healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  ${healthy_services}/${#services[@]} services healthy${NC}"
    echo "Some services may still be starting up..."
fi

echo ""

# Get API key
echo -e "${BLUE}Getting API key...${NC}"
API_KEY=""

# Try to get API key from logs (may take a moment)
for i in {1..10}; do
    API_KEY=$(docker-compose -f docker-compose-with-ui.yml logs identity-service 2>/dev/null | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //' || echo "")
    if [ -n "$API_KEY" ]; then
        break
    fi
    echo -e "${YELLOW}⏳ Waiting for API key generation... (attempt $i/10)${NC}"
    sleep 5
done

if [ -n "$API_KEY" ]; then
    echo -e "${GREEN}✅ API Key obtained: ${API_KEY}${NC}"
else
    echo -e "${RED}❌ Could not get API key automatically${NC}"
    echo "Please check the identity service logs manually:"
    echo "  docker-compose -f docker-compose-with-ui.yml logs identity-service | grep 'Admin API Key'"
fi

echo ""

# Test connectivity
echo -e "${BLUE}Testing connectivity...${NC}"

# Test API Gateway
if curl -s http://localhost:7841/health > /dev/null; then
    echo -e "${GREEN}✅ API Gateway (port 7841)${NC}"
else
    echo -e "${RED}❌ API Gateway not responding${NC}"
fi

# Test Web UI
if curl -s http://localhost:9347/api/health > /dev/null; then
    echo -e "${GREEN}✅ Web UI (port 9347)${NC}"
else
    echo -e "${RED}❌ Web UI not responding${NC}"
fi

echo ""

# Show access information
echo -e "${BLUE}🎉 S3 Storage System is ready!${NC}"
echo -e "${BLUE}==============================${NC}"
echo ""
echo -e "${GREEN}🌐 Web UI:${NC} http://localhost:9347"
echo -e "${GREEN}🔧 API Gateway:${NC} http://localhost:7841"
if [ -n "$API_KEY" ]; then
    echo -e "${GREEN}🔑 API Key:${NC} ${API_KEY}"
fi
echo ""

echo -e "${BLUE}How to use:${NC}"
echo "1. Open http://localhost:9347 in your browser"
echo "2. Enter the API key on the login page"
echo "3. Start creating buckets and uploading files!"
echo ""

echo -e "${BLUE}Quick Test:${NC}"
echo "# Create a bucket"
echo "curl -X POST http://localhost:7841/buckets \\"
echo "  -H 'Authorization: Bearer ${API_KEY}' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"bucket_name\": \"test-bucket\"}'"
echo ""

echo -e "${BLUE}Useful Commands:${NC}"
echo "# View logs"
echo "docker-compose -f docker-compose-with-ui.yml logs -f"
echo ""
echo "# Stop services"
echo "docker-compose -f docker-compose-with-ui.yml down"
echo ""
echo "# Check service status"
echo "docker-compose -f docker-compose-with-ui.yml ps"
echo ""

echo -e "${BLUE}Documentation:${NC}"
echo "📖 UI Guide: ./UI_GUIDE.md"
echo "📖 API Guide: ./README.md"
echo "🧪 Testing: ./TESTING_GUIDE.md"
echo ""

echo -e "${GREEN}Happy storing! 🚀${NC}"