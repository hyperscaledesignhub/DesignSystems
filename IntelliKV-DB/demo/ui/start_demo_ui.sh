#!/bin/bash

# Start Demo UI for Distributed Database
# This script starts the web-based UI for all demos

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🌐 Starting Distributed Database Demo UI${NC}"
echo "========================================="

# Check if we're in the right directory
if [[ ! -f "app.py" ]]; then
    echo -e "${RED}Error: Please run this script from the demo/ui directory${NC}"
    echo "Usage: cd demo/ui && bash start_demo_ui.sh"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is required but not installed${NC}"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install -r requirements.txt

# Check if cluster is running
echo -e "${YELLOW}Checking cluster status...${NC}"
CLUSTER_HEALTHY=true

for port in 9999 10000 10001; do
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Node on port $port is healthy${NC}"
    else
        echo -e "${RED}❌ Node on port $port is not reachable${NC}"
        CLUSTER_HEALTHY=false
    fi
done

if [ "$CLUSTER_HEALTHY" = false ]; then
    echo -e "${YELLOW}⚠️  Some cluster nodes are not healthy${NC}"
    echo "To start the cluster, run from the project root:"
    echo "  bash scripts/start-cluster-local.sh"
    echo ""
    echo "The UI will still start, but demos may not work properly."
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set environment variables
export CLUSTER_NODES="localhost:9999,localhost:10000,localhost:10001"

echo -e "${GREEN}Starting Demo UI server...${NC}"
echo ""
echo "🌐 Demo URLs:"
echo "  Main Launcher: http://localhost:7342"
echo "  Twitter Demo:  http://localhost:7342/twitter"
echo "  Collab Editor: http://localhost:7342/collab-editor"
echo "  CDN Demo:      http://localhost:7342/cdn"
echo "  Inventory:     http://localhost:7342/inventory"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the Flask application
python3 app.py