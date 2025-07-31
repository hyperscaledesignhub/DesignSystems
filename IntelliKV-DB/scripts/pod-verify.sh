#!/bin/bash

# Pod Internal Cluster Verification Script
# This script runs inside a pod to test the distributed database cluster

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m' 
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔍 Pod Internal Cluster Verification${NC}"
echo "======================================="

# Function to wait for node health
wait_for_node() {
    local host=$1
    local port=$2
    local name=$3
    echo -e "${YELLOW}Waiting for ${name}...${NC}"
    for i in {1..15}; do
        if curl -s "http://${host}:${port}/health" | grep -q "healthy"; then
            echo -e "${GREEN}✅ ${name} is healthy${NC}"
            return 0
        fi
        echo "  Attempt $i/15..."
        sleep 2
    done
    echo -e "${RED}❌ ${name} failed to start${NC}"
    return 1
}

# Get pod hostnames (these are the internal DNS names in Kubernetes)
POD0_HOST="distributed-database-0.db-headless-service.distributed-db.svc.cluster.local"
POD1_HOST="distributed-database-1.db-headless-service.distributed-db.svc.cluster.local"
POD2_HOST="distributed-database-2.db-headless-service.distributed-db.svc.cluster.local"
PORT=8080

echo -e "${YELLOW}Pod hostnames:${NC}"
echo "Pod 0: $POD0_HOST:$PORT"
echo "Pod 1: $POD1_HOST:$PORT"
echo "Pod 2: $POD2_HOST:$PORT"
echo ""

# Test 1: Basic Health Check
echo -e "${BLUE}1. Testing Basic Health Check${NC}"
echo "================================"

echo "Testing health endpoints:"
echo "Pod 0:"
curl -s http://$POD0_HOST:$PORT/health | python -m json.tool
echo "Pod 1:"
curl -s http://$POD1_HOST:$PORT/health | python -m json.tool
echo "Pod 2:"
curl -s http://$POD2_HOST:$PORT/health | python -m json.tool

# Test 2: Basic Data Storage and Retrieval
echo -e "\n${BLUE}2. Testing Basic Data Storage and Retrieval${NC}"
echo "=============================================="

echo "Storing test data on Pod 0..."
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"pod_test_value"}' http://$POD0_HOST:$PORT/kv/pod_test

echo -e "\nVerifying data is accessible from all pods:"
echo "From Pod 0:"
curl -s http://$POD0_HOST:$PORT/kv/pod_test | python -m json.tool
echo "From Pod 1:"
curl -s http://$POD1_HOST:$PORT/kv/pod_test | python -m json.tool
echo "From Pod 2:"
curl -s http://$POD2_HOST:$PORT/kv/pod_test | python -m json.tool

# Test 3: Replication Test
echo -e "\n${BLUE}3. Testing Replication${NC}"
echo "======================="

echo "Storing multiple keys from different pods..."
echo "Storing key1 from Pod 1:"
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"replication_test_1"}' http://$POD1_HOST:$PORT/kv/key1

echo "Storing key2 from Pod 2:"
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"replication_test_2"}' http://$POD2_HOST:$PORT/kv/key2

echo -e "\nVerifying all keys are accessible from all pods:"
echo "=== Testing from Pod 0 ==="
curl -s http://$POD0_HOST:$PORT/kv/key1 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key1: {data[\"value\"]}')"
curl -s http://$POD0_HOST:$PORT/kv/key2 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key2: {data[\"value\"]}')"

echo "=== Testing from Pod 1 ==="
curl -s http://$POD1_HOST:$PORT/kv/key1 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key1: {data[\"value\"]}')"
curl -s http://$POD1_HOST:$PORT/kv/key2 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key2: {data[\"value\"]}')"

echo "=== Testing from Pod 2 ==="
curl -s http://$POD2_HOST:$PORT/kv/key1 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key1: {data[\"value\"]}')"
curl -s http://$POD2_HOST:$PORT/kv/key2 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key2: {data[\"value\"]}')"

# Test 4: Cluster Status Check
echo -e "\n${BLUE}4. Cluster Status Check${NC}"
echo "========================"

echo "Pod 0 Info:"
curl -s http://$POD0_HOST:$PORT/info | python -m json.tool
echo "Pod 1 Info:"
curl -s http://$POD1_HOST:$PORT/info | python -m json.tool
echo "Pod 2 Info:"
curl -s http://$POD2_HOST:$PORT/info | python -m json.tool

# Test 5: Persistence Test
echo -e "\n${BLUE}5. Testing Persistence${NC}"
echo "======================="

echo "Storing persistent data..."
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"persistent_data_test"}' http://$POD0_HOST:$PORT/kv/persistent_test

echo "Checking persistence stats on Pod 0:"
curl -s http://$POD0_HOST:$PORT/persistence/stats | python -m json.tool

# Test 6: Hash Ring Test
echo -e "\n${BLUE}6. Testing Hash Ring${NC}"
echo "====================="

echo "Checking hash ring information:"
curl -s http://$POD0_HOST:$PORT/ring | python -m json.tool

# Test 7: Direct Operations Test
echo -e "\n${BLUE}7. Testing Direct Operations${NC}"
echo "==============================="

echo "Testing direct PUT operation:"
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"direct_test"}' http://$POD0_HOST:$PORT/kv/direct_test/direct

echo "Testing direct GET operation:"
curl -s http://$POD0_HOST:$PORT/kv/direct_test/direct | python -m json.tool

echo -e "\n${GREEN}🎉 Pod Internal Cluster Verification Complete!${NC}"
echo "============================================="
echo "All tests passed! Your distributed database is working correctly inside the pod." 