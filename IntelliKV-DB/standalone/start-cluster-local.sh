#!/bin/bash

# Start 3-node cluster locally using node.py
# 
# This script starts a 3-node distributed key-value database cluster locally.
# 
# Required environment variables for node.py:
#   CONFIG_FILE    - Path to YAML configuration file (default: yaml/config-local.yaml)
#   SEED_NODE_ID   - Node ID from the config file (e.g., db-node-1, db-node-2, db-node-3)
#
# The node.py script reads the following from the YAML config:
#   - Node ID, host, and port configuration
#   - Seed nodes for cluster formation
#   - Replication factor
#   - Anti-entropy settings
#   - Persistence settings
#
# Each node is started with:
#   CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=<node-id> python distributed/node.py
#
# The nodes will:
#   1. Load their configuration from the YAML file
#   2. Start the HTTP server on the configured port
#   3. Initialize persistence, hash ring, and anti-entropy managers
#   4. Automatically join other seed nodes to form the cluster
#   5. Begin gossip protocol for peer discovery
#
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m' 
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting 3-Node Local Cluster${NC}"
echo "====================================="

# Use local config file
CONFIG_FILE="yaml/config-local.yaml"

# Check if local config exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo -e "${RED}Error: $CONFIG_FILE not found${NC}"
    echo "Please ensure the local configuration file exists."
    exit 1
fi

# Read ports from local YAML config
echo -e "${YELLOW}Reading configuration from $CONFIG_FILE...${NC}"

# Function to extract node info from YAML using Python
get_node_info() {
    local node_id=$1
    local field=$2
    python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
for node in config['cluster']['seed_nodes']:
    if node['id'] == '$node_id':
        print(node['$field'])
        break
"
}

# Get host and port for each node
NODE1_HOST=$(get_node_info "db-node-1" "host")
NODE1_PORT=$(get_node_info "db-node-1" "db_port")
NODE2_HOST=$(get_node_info "db-node-2" "host")
NODE2_PORT=$(get_node_info "db-node-2" "db_port")
NODE3_HOST=$(get_node_info "db-node-3" "host")
NODE3_PORT=$(get_node_info "db-node-3" "db_port")

echo "Node 1 (db-node-1): $NODE1_HOST:$NODE1_PORT"
echo "Node 2 (db-node-2): $NODE2_HOST:$NODE2_PORT"
echo "Node 3 (db-node-3): $NODE3_HOST:$NODE3_PORT"

# Cleanup
echo -e "${YELLOW}Cleaning up...${NC}"
echo "Killing all Python processes..."
pkill -f python 2>/dev/null || true
pkill -f "distributed/node.py" 2>/dev/null || true
sleep 3
rm -rf ./data
mkdir -p ./data

# Function to check health
check_health() {
    local host=$1
    local port=$2
    local name=$3
    for i in {1..15}; do
        local response=$(curl -s "http://${host}:${port}/health" 2>/dev/null)
        if echo "$response" | grep -q "healthy\|degraded"; then
            if echo "$response" | grep -q "healthy"; then
                echo -e "${GREEN}✅ ${name} is healthy${NC}"
            else
                echo -e "${YELLOW}⚠️  ${name} is degraded (waiting for peers)${NC}"
            fi
            return 0
        fi
        echo "Waiting for ${name}... ($i/15)"
        sleep 2
    done
    echo -e "${RED}❌ ${name} failed to start${NC}"
    return 1
}

# Start Node 1
echo -e "${GREEN}Starting Node 1 (db-node-1) on port $NODE1_PORT...${NC}"
echo "Command: CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=db-node-1 python distributed/node.py"
CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=db-node-1 python distributed/node.py > node1.log 2>&1 &
PID1=$!
echo "Node 1 PID: $PID1"

if ! check_health $NODE1_HOST $NODE1_PORT "Node 1"; then
    echo "Check node1.log for details"
    exit 1
fi

# Start Node 2
echo -e "${GREEN}Starting Node 2 (db-node-2) on port $NODE2_PORT...${NC}"
echo "Command: CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=db-node-2 python distributed/node.py"
CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=db-node-2 python distributed/node.py > node2.log 2>&1 &
PID2=$!
echo "Node 2 PID: $PID2"

if ! check_health $NODE2_HOST $NODE2_PORT "Node 2"; then
    echo "Check node2.log for details"
    exit 1
fi

# Start Node 3  
echo -e "${GREEN}Starting Node 3 (db-node-3) on port $NODE3_PORT...${NC}"
echo "Command: CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=db-node-3 python distributed/node.py"
CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=db-node-3 python distributed/node.py > node3.log 2>&1 &
PID3=$!
echo "Node 3 PID: $PID3"

if ! check_health $NODE3_HOST $NODE3_PORT "Node 3"; then
    echo "Check node3.log for details"
    exit 1
fi

# Wait for cluster formation
echo -e "${YELLOW}Waiting for cluster formation...${NC}"
sleep 15

# Check cluster status
echo -e "${BLUE}Cluster Status:${NC}"
echo ""
echo "Node 1:"
curl -s http://$NODE1_HOST:$NODE1_PORT/info | python -m json.tool
echo ""
echo "Node 2:"
curl -s http://$NODE2_HOST:$NODE2_PORT/info | python -m json.tool  
echo ""
echo "Node 3:"
curl -s http://$NODE3_HOST:$NODE3_PORT/info | python -m json.tool

echo ""
echo -e "${GREEN}🎉 Local Cluster Ready!${NC}"
echo "========================"
echo "Node 1: http://$NODE1_HOST:$NODE1_PORT"
echo "Node 2: http://$NODE2_HOST:$NODE2_PORT"
echo "Node 3: http://$NODE3_HOST:$NODE3_PORT"
echo ""
echo "Test commands:"
echo "curl -X PUT -H 'Content-Type: application/json' -d '{\"value\":\"hello\"}' http://$NODE1_HOST:$NODE1_PORT/kv/test"
echo "curl http://$NODE2_HOST:$NODE2_PORT/kv/test"
echo ""
echo "To manually start individual nodes, use:"
echo "  CONFIG_FILE=yaml/config-local.yaml SEED_NODE_ID=db-node-1 python distributed/node.py"
echo "  CONFIG_FILE=yaml/config-local.yaml SEED_NODE_ID=db-node-2 python distributed/node.py"
echo "  CONFIG_FILE=yaml/config-local.yaml SEED_NODE_ID=db-node-3 python distributed/node.py"
echo ""
echo "Press Ctrl+C to stop the cluster"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Stopping cluster...${NC}"
    kill $PID1 $PID2 $PID3 2>/dev/null || true
    pkill -f "distributed/node.py" 2>/dev/null || true
    echo -e "${GREEN}Cluster stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep running
while true; do
    sleep 1
done 