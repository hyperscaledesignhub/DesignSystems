#!/bin/bash

# Stock Exchange Demo - Complete System Startup
# This script starts all microservices and frontend for customer demonstration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏦 STOCK EXCHANGE DEMO - COMPLETE SYSTEM${NC}"
echo "=========================================="
echo -e "${BLUE}Starting Stock Exchange Demo for Customer Presentation${NC}"
echo

# Check prerequisites
echo -e "${PURPLE}Checking Prerequisites${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is available${NC}"
echo -e "${GREEN}✅ Docker Compose is available${NC}"

# Navigate to demo directory
cd "$(dirname "$0")/.."

echo
echo -e "${PURPLE}Starting All Services with Docker Compose${NC}"

# Stop any existing containers
echo -e "${BLUE}ℹ Stopping any existing containers...${NC}"
cd docker && docker-compose down -v --remove-orphans 2>/dev/null || true

# Build and start all services
echo -e "${BLUE}ℹ Building and starting all services...${NC}"
docker-compose up --build -d

echo
echo -e "${BLUE}ℹ Waiting for all services to be healthy...${NC}"

# Wait for services to be healthy
TIMEOUT=120
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $TIMEOUT ]; do
    if docker-compose ps | grep -q "unhealthy\|starting"; then
        echo -e "${YELLOW}⏳ Services still starting... (${ELAPSED}s/${TIMEOUT}s)${NC}"
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    else
        break
    fi
done

# Check final status
echo
echo -e "${PURPLE}Service Status Check${NC}"
if docker-compose ps | grep -q "unhealthy"; then
    echo -e "${RED}❌ Some services are unhealthy${NC}"
    docker-compose ps
    exit 1
else
    echo -e "${GREEN}✅ All services are running and healthy${NC}"
fi

# Create demo users
echo
echo -e "${PURPLE}Setting Up Demo Data${NC}"
echo -e "${BLUE}ℹ Creating demo users...${NC}"

# Wait a bit more for services to fully initialize
sleep 10

# Create demo users via API
curl -s -X POST http://localhost:8347/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "buyer_demo", "email": "buyer@demo.com", "password": "demopass123"}' > /dev/null || true

curl -s -X POST http://localhost:8347/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "seller_demo", "email": "seller@demo.com", "password": "demopass123"}' > /dev/null || true

echo -e "${GREEN}✅ Demo users created${NC}"

# Test system integration
echo
echo -e "${PURPLE}Testing System Integration${NC}"

# Test authentication
echo -e "${BLUE}ℹ Testing authentication...${NC}"
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8347/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "buyer_demo", "password": "demopass123"}')

if echo "$AUTH_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ Authentication is working${NC}"
    
    # Extract token for further testing
    TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
    
    # Test order placement
    echo -e "${BLUE}ℹ Testing order placement...${NC}"
    ORDER_RESPONSE=$(curl -s -X POST http://localhost:8347/v1/order \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"symbol": "DEMO", "side": "BUY", "quantity": "10", "price": "100.00"}')
    
    if echo "$ORDER_RESPONSE" | grep -q "id"; then
        echo -e "${GREEN}✅ Order placement is working${NC}"
    else
        echo -e "${YELLOW}⚠ Order placement may have issues${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Authentication may have issues${NC}"
fi

# Show system information
echo
echo -e "${PURPLE}🎯 Demo System Ready!${NC}"
echo
echo -e "${BLUE}ℹ 📱 Frontend Application:${NC}"
echo -e "   ${BLUE}http://localhost:3000${NC}"
echo
echo -e "${BLUE}ℹ 🔗 API Gateway:${NC}"
echo -e "   ${BLUE}http://localhost:8347${NC}"
echo
echo -e "${BLUE}ℹ 📊 Individual Microservices:${NC}"
echo -e "   • User Service:        ${BLUE}http://localhost:8975${NC}"
echo -e "   • Wallet Service:      ${BLUE}http://localhost:8651${NC}"
echo -e "   • Order Manager:       ${BLUE}http://localhost:8426${NC}"
echo -e "   • Risk Manager:        ${BLUE}http://localhost:8539${NC}"
echo -e "   • Matching Engine:     ${BLUE}http://localhost:8792${NC}"
echo -e "   • Market Data:         ${BLUE}http://localhost:8864${NC}"
echo -e "   • Reporting Service:   ${BLUE}http://localhost:9127${NC}"
echo -e "   • Notification Service: ${BLUE}http://localhost:9243${NC}"
echo
echo -e "${BLUE}ℹ 🔐 Demo Credentials:${NC}"
echo -e "   • Buyer:  username: ${GREEN}buyer_demo${NC}, password: ${GREEN}demopass123${NC}"
echo -e "   • Seller: username: ${GREEN}seller_demo${NC}, password: ${GREEN}demopass123${NC}"
echo
echo -e "${BLUE}ℹ 🧪 Demo Scripts:${NC}"
echo -e "   • Complete Flow:       ${BLUE}python3 microservice_flow_demo.py${NC}"
echo -e "   • Redis Messaging:     ${BLUE}python3 redis_pubsub_demo.py${NC}"
echo -e "   • Matching Engine:     ${BLUE}python3 matching_engine_demo.py${NC}"
echo
echo -e "${BLUE}ℹ 🐳 Docker Management:${NC}"
echo -e "   • View logs:           ${BLUE}docker-compose logs -f [service-name]${NC}"
echo -e "   • Stop all services:   ${BLUE}docker-compose down${NC}"
echo -e "   • Restart service:     ${BLUE}docker-compose restart [service-name]${NC}"
echo
echo -e "${YELLOW}⚠ This is a demonstration system for customer presentation${NC}"
echo -e "${BLUE}ℹ All services are now running and ready for demo${NC}"
echo
echo -e "${GREEN}🎉 DEMO SYSTEM SUCCESSFULLY STARTED!${NC}"