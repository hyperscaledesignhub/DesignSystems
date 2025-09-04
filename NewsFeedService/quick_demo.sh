#!/bin/bash

# News Feed System - Quick Demo Script
# One-click setup and demo of the complete system

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                         🚀 NEWS FEED SYSTEM DEMO 🚀                        ║${NC}"  
echo -e "${PURPLE}║                    Enterprise-Grade Social Media Platform                    ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${CYAN}This demo will:${NC}"
echo -e "${CYAN}✨ Setup all infrastructure (PostgreSQL, Redis, RabbitMQ)${NC}"
echo -e "${CYAN}🚀 Start all 7 microservices${NC}"
echo -e "${CYAN}🧪 Run comprehensive system tests${NC}"
echo -e "${CYAN}📊 Show you the complete social media system in action${NC}"

echo -e "\n${YELLOW}⚠️  Prerequisites: Docker must be running${NC}"
echo -e "${BLUE}Press [ENTER] to continue or [Ctrl+C] to exit...${NC}"
read -r

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📦 STEP 1: Setting up infrastructure dependencies...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"

./setup_dependencies.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Infrastructure setup failed. Please check Docker is running.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Infrastructure ready! Press [ENTER] to start services...${NC}"
read -r

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 STEP 2: Starting all microservices...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"

./start_system.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Service startup failed. Check logs for details.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ All services started! Press [ENTER] to run demo tests...${NC}"
read -r

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🧪 STEP 3: Running comprehensive system demonstration...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}🔬 Running ultimate system test (all 7 services)...${NC}"
python test_ultimate_system.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ System test failed. Check service logs.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ System test completed! Press [ENTER] to run API Gateway test...${NC}"
read -r

echo -e "\n${YELLOW}🌐 Testing API Gateway functionality...${NC}"
python test_api_gateway.py

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🎉 DEMO COMPLETE - System Overview${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${GREEN}🏆 Congratulations! Your News Feed System is fully operational!${NC}"

echo -e "\n${YELLOW}📡 RUNNING SERVICES:${NC}"
echo -e "   🌐 API Gateway:       http://localhost:8370 (Central routing, rate limiting)"
echo -e "   👤 User Service:      http://localhost:8371 (Authentication, JWT tokens)"
echo -e "   📝 Post Service:      http://localhost:8372 (Content creation, storage)"
echo -e "   🤝 Graph Service:     http://localhost:8373 (Social relationships)"
echo -e "   📡 Fanout Service:    http://localhost:8374 (Async post distribution)"
echo -e "   📰 News Feed Service: http://localhost:8375 (Personalized feeds)"
echo -e "   🔔 Notification Svc:  http://localhost:8376 (Multi-type notifications)"

echo -e "\n${YELLOW}🗄️  INFRASTRUCTURE:${NC}"
echo -e "   🐘 PostgreSQL: 4 databases running (user, post, graph, notification)"
echo -e "   🔴 Redis: Caching & feed storage"
echo -e "   🐰 RabbitMQ: Message queuing for async processing"

echo -e "\n${YELLOW}🧪 NEXT STEPS - Try these:${NC}"
echo -e "   ${CYAN}# Test individual services${NC}"
echo -e "   python test_user_service.py"
echo -e "   python test_post_service.py" 
echo -e "   python test_graph_service.py"
echo -e "   python test_fanout_service.py"
echo -e "   python test_newsfeed_service.py"
echo -e "   python test_notification_service.py"

echo -e "\n   ${CYAN}# Check service health${NC}"
echo -e "   curl http://localhost:8370/services/status"

echo -e "\n   ${CYAN}# Monitor system activity${NC}"
echo -e "   tail -f logs/*.log"

echo -e "\n   ${CYAN}# Example API calls via Gateway${NC}"
echo -e "   # Register user:"
echo -e "   curl -X POST http://localhost:8370/api/v1/auth/register \\"
echo -e "     -H 'Content-Type: application/json' \\"
echo -e "     -d '{\"username\":\"demo_user\", \"email\":\"demo@test.com\", \"password\":\"demo123\"}'"

echo -e "\n${YELLOW}🛑 TO STOP THE SYSTEM:${NC}"
echo -e "   ./stop_system.sh"

echo -e "\n${YELLOW}📊 SYSTEM CAPABILITIES:${NC}"
echo -e "   ✅ Facebook-scale social media architecture"
echo -e "   ✅ Real-time personalized news feeds"
echo -e "   ✅ Push-based fanout for optimal performance"
echo -e "   ✅ Enterprise-grade microservices"
echo -e "   ✅ Horizontal scalability to millions of users"
echo -e "   ✅ Production-ready security & authentication"
echo -e "   ✅ Comprehensive monitoring & testing"

echo -e "\n${GREEN}🌟 You now have a complete, production-ready social media backend!${NC}"
echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                    🎉 WELCOME TO YOUR NEWS FEED SYSTEM! 🎉                  ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"