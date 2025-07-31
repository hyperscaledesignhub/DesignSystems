#!/bin/bash
"""
Main Demo Launcher - All Distributed Database Demos
"""

echo "🚀 Distributed Database Demo Suite"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if cluster is running
echo "🔍 Checking cluster health..."
if ! curl -s http://localhost:9999/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Cluster not running. Please start the cluster first:${NC}"
    echo "   cd /Users/vijayabhaskarv/hyper-scale/kvdb/DesignSystems/NoSQL-DB"
    echo "   ./scripts/start_local_cluster.sh"
    exit 1
fi

echo -e "${GREEN}✅ Cluster is running${NC}"
echo ""

# Set cluster nodes environment
export CLUSTER_NODES="localhost:9999,localhost:10000,localhost:10001"

# Function to show demo menu
show_menu() {
    echo -e "${CYAN}Available Demos:${NC}"
    echo ""
    echo -e "${BLUE}1)${NC} 🐦 Twitter Demo           ${YELLOW}(Port 8001)${NC} - Real-time engagement tracking"
    echo -e "${BLUE}2)${NC} 📝 Collaborative Editor   ${YELLOW}(Port 8002)${NC} - Real-time document editing"
    echo -e "${BLUE}3)${NC} 📦 Inventory Management   ${YELLOW}(Port 8003)${NC} - Multi-warehouse inventory"
    echo -e "${BLUE}4)${NC} 🌐 CDN Distribution       ${YELLOW}(Port 8004)${NC} - Content delivery network"
    echo -e "${BLUE}5)${NC} 🔥 Concurrent Writes      ${YELLOW}(Port 8005)${NC} - Quorum consensus & consistency"
    echo -e "${BLUE}6)${NC} 🚀 Start All Demos        ${YELLOW}(All Ports)${NC} - Launch everything"
    echo -e "${BLUE}7)${NC} 🧹 Stop All Demos         ${YELLOW}(Cleanup)${NC} - Kill all demo processes"
    echo -e "${BLUE}8)${NC} 📊 Show Demo Status        ${YELLOW}(Info)${NC} - Check which demos are running"
    echo -e "${BLUE}9)${NC} ❌ Exit"
    echo ""
}

# Function to check if a demo is running
check_demo_status() {
    local port=$1
    local name=$2
    
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name running on port $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $name not running on port $port${NC}"
        return 1
    fi
}

# Function to start a demo
start_demo() {
    local script=$1
    local name=$2
    local port=$3
    
    echo -e "${YELLOW}🚀 Starting $name...${NC}"
    
    # Kill existing instance
    pkill -f "$script" 2>/dev/null || true
    
    # Start in background
    cd "$(dirname "$0")"
    ./$script > /dev/null 2>&1 &
    
    # Wait a moment and check if it started
    sleep 3
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name started successfully on port $port${NC}"
        echo -e "${CYAN}   URL: http://localhost:$port${NC}"
    else
        echo -e "${RED}❌ Failed to start $name${NC}"
    fi
    echo ""
}

# Function to stop all demos
stop_all_demos() {
    echo -e "${YELLOW}🧹 Stopping all demos...${NC}"
    
    pkill -f "twitter_demo.py" 2>/dev/null || true
    pkill -f "collab_editor_demo.py" 2>/dev/null || true
    pkill -f "inventory_demo.py" 2>/dev/null || true
    pkill -f "cdn_demo.py" 2>/dev/null || true
    pkill -f "concurrent_writes_demo.py" 2>/dev/null || true
    
    echo -e "${GREEN}✅ All demos stopped${NC}"
    echo ""
}

# Function to show demo status
show_demo_status() {
    echo -e "${CYAN}📊 Demo Status:${NC}"
    echo ""
    
    check_demo_status 8001 "Twitter Demo"
    check_demo_status 8002 "Collaborative Editor"
    check_demo_status 8003 "Inventory Management"
    check_demo_status 8004 "CDN Distribution"
    check_demo_status 8005 "Concurrent Writes"
    
    echo ""
    echo -e "${CYAN}🖥️  Cluster Nodes:${NC}"
    for node in "localhost:9999" "localhost:10000" "localhost:10001"; do
        if curl -s http://$node/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $node${NC}"
        else
            echo -e "${RED}❌ $node${NC}"
        fi
    done
    echo ""
}

# Function to start all demos
start_all_demos() {
    echo -e "${PURPLE}🚀 Starting All Demos...${NC}"
    echo ""
    
    start_demo "run_twitter_demo.sh" "Twitter Demo" 8001
    start_demo "run_collab_editor_demo.sh" "Collaborative Editor" 8002
    start_demo "run_inventory_demo.sh" "Inventory Management" 8003
    start_demo "run_cdn_demo.sh" "CDN Distribution" 8004
    start_demo "run_concurrent_writes_demo.sh" "Concurrent Writes" 8005
    
    echo -e "${GREEN}🎉 All demos started!${NC}"
    echo ""
    echo -e "${CYAN}📍 Demo URLs:${NC}"
    echo -e "   🐦 Twitter Demo:           ${YELLOW}http://localhost:8001${NC}"
    echo -e "   📝 Collaborative Editor:   ${YELLOW}http://localhost:8002${NC}"
    echo -e "   📦 Inventory Management:   ${YELLOW}http://localhost:8003${NC}"
    echo -e "   🌐 CDN Distribution:       ${YELLOW}http://localhost:8004${NC}"
    echo -e "   🔥 Concurrent Writes:      ${YELLOW}http://localhost:8005${NC}"
    echo ""
    echo -e "${PURPLE}💡 Features Showcase:${NC}"
    echo -e "   • Twitter: Regular endpoints for high-performance counters"
    echo -e "   • Collaborative: Causal endpoints for proper edit ordering"
    echo -e "   • Inventory: Load-balanced operations across warehouses"
    echo -e "   • CDN: Distributed caching with regional optimization"
    echo -e "   • Concurrent Writes: Quorum consensus for data consistency"
    echo ""
}

# Main menu loop
while true; do
    show_menu
    read -p "Select an option (1-9): " choice
    echo ""
    
    case $choice in
        1)
            start_demo "run_twitter_demo.sh" "Twitter Demo" 8001
            ;;
        2)
            start_demo "run_collab_editor_demo.sh" "Collaborative Editor" 8002
            ;;
        3)
            start_demo "run_inventory_demo.sh" "Inventory Management" 8003
            ;;
        4)
            start_demo "run_cdn_demo.sh" "CDN Distribution" 8004
            ;;
        5)
            start_demo "run_concurrent_writes_demo.sh" "Concurrent Writes" 8005
            ;;
        6)
            start_all_demos
            ;;
        7)
            stop_all_demos
            ;;
        8)
            show_demo_status
            ;;
        9)
            echo -e "${YELLOW}👋 Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid option. Please choose 1-9.${NC}"
            echo ""
            ;;
    esac
done