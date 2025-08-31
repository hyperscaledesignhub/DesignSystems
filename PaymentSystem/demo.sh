#!/bin/bash

# Payment System Demo - Master Control Script
# This script manages all services and UI together

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}    Payment System Demo - Master Control${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

print_menu() {
    echo -e "${GREEN}Please choose an option:${NC}"
    echo ""
    echo "  1) Start All (Services + UI)"
    echo "  2) Start Services Only"
    echo "  3) Start UI Only"
    echo "  4) Stop All (Services + UI)"
    echo "  5) Stop Services Only"
    echo "  6) Stop UI Only"
    echo "  7) Restart All"
    echo "  8) Check Status"
    echo "  9) View Logs"
    echo "  0) Exit"
    echo ""
}

start_all() {
    echo -e "${GREEN}🚀 Starting all services and UI...${NC}"
    ./start-services.sh
    echo ""
    echo -e "${GREEN}🎨 Starting UI in 3 seconds...${NC}"
    sleep 3
    ./start-ui.sh &
    echo ""
    echo -e "${GREEN}✅ All systems are running!${NC}"
    echo -e "${YELLOW}📱 Open http://localhost:3001 in your browser${NC}"
}

stop_all() {
    echo -e "${RED}🛑 Stopping all services and UI...${NC}"
    ./stop-ui.sh
    ./stop-services.sh
    echo -e "${GREEN}✅ All systems stopped!${NC}"
}

restart_all() {
    echo -e "${YELLOW}🔄 Restarting all services...${NC}"
    stop_all
    sleep 2
    start_all
}

check_status() {
    echo -e "${BLUE}📊 System Status:${NC}"
    echo "================================"
    
    # Check Docker services
    echo -e "${YELLOW}Docker Services:${NC}"
    docker-compose ps --format "table {{.Service}}\t{{.State}}\t{{.Ports}}"
    
    echo ""
    echo -e "${YELLOW}Service Health:${NC}"
    
    # Check each service health
    check_service() {
        local name=$1
        local url=$2
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "  ✅ $name"
        else
            echo -e "  ❌ $name"
        fi
    }
    
    check_service "Wallet Service (8740)" "http://localhost:8740/health"
    check_service "Fraud Detection (8742)" "http://localhost:8742/health"
    check_service "Reconciliation (8741)" "http://localhost:8741/health"
    check_service "Notification (8743)" "http://localhost:8743/health"
    check_service "Jaeger UI (16686)" "http://localhost:16686"
    
    # Check UI
    if lsof -ti:3001 > /dev/null 2>&1; then
        echo -e "  ✅ UI Server (3001)"
    else
        echo -e "  ❌ UI Server (3001)"
    fi
}

view_logs() {
    echo -e "${BLUE}📜 Select service to view logs:${NC}"
    echo "  1) Wallet Service"
    echo "  2) Fraud Detection Service"
    echo "  3) Reconciliation Service"
    echo "  4) Notification Service"
    echo "  5) All Services"
    echo "  0) Back to main menu"
    
    read -p "Enter choice: " log_choice
    
    case $log_choice in
        1) docker-compose logs -f wallet-service ;;
        2) docker-compose logs -f fraud-detection-service ;;
        3) docker-compose logs -f reconciliation-service ;;
        4) docker-compose logs -f notification-service ;;
        5) docker-compose logs -f ;;
        0) return ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
}

# Main loop
while true; do
    print_header
    print_menu
    read -p "Enter your choice [0-9]: " choice
    
    case $choice in
        1)
            start_all
            read -p "Press Enter to continue..."
            ;;
        2)
            ./start-services.sh
            read -p "Press Enter to continue..."
            ;;
        3)
            ./start-ui.sh
            ;;
        4)
            stop_all
            read -p "Press Enter to continue..."
            ;;
        5)
            ./stop-services.sh
            read -p "Press Enter to continue..."
            ;;
        6)
            ./stop-ui.sh
            read -p "Press Enter to continue..."
            ;;
        7)
            restart_all
            read -p "Press Enter to continue..."
            ;;
        8)
            check_status
            read -p "Press Enter to continue..."
            ;;
        9)
            view_logs
            ;;
        0)
            echo -e "${GREEN}👋 Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            sleep 2
            ;;
    esac
done