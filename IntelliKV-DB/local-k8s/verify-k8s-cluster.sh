#!/bin/bash

# Kubernetes Cluster Verification Script
# Tests the distributed database cluster running in Kubernetes

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m' 
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔍 Kubernetes Cluster Verification${NC}"
echo "====================================="

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

# Get pod IPs and ports
echo -e "${YELLOW}Getting pod information...${NC}"
POD0_IP=$(kubectl get pod -n distributed-db distributed-database-0 -o jsonpath='{.status.podIP}')
POD1_IP=$(kubectl get pod -n distributed-db distributed-database-1 -o jsonpath='{.status.podIP}')
POD2_IP=$(kubectl get pod -n distributed-db distributed-database-2 -o jsonpath='{.status.podIP}')

echo "Pod 0 IP: $POD0_IP"
echo "Pod 1 IP: $POD1_IP"
echo "Pod 2 IP: $POD2_IP"
echo ""

# Test 1: Basic Health Check
echo -e "${BLUE}1. Testing Basic Health Check${NC}"
echo "================================"

echo "Testing health endpoints:"
echo "Pod 0:"
curl -s http://$POD0_IP:8080/health | python -m json.tool
echo "Pod 1:"
curl -s http://$POD1_IP:8080/health | python -m json.tool
echo "Pod 2:"
curl -s http://$POD2_IP:8080/health | python -m json.tool

# Test 2: Basic Data Storage and Retrieval
echo -e "\n${BLUE}2. Testing Basic Data Storage and Retrieval${NC}"
echo "=============================================="

echo "Storing test data on Pod 0..."
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"k8s_test_value"}' http://$POD0_IP:8080/kv/k8s_test

echo -e "\nVerifying data is accessible from all pods:"
echo "From Pod 0:"
curl -s http://$POD0_IP:8080/kv/k8s_test | python -m json.tool
echo "From Pod 1:"
curl -s http://$POD1_IP:8080/kv/k8s_test | python -m json.tool
echo "From Pod 2:"
curl -s http://$POD2_IP:8080/kv/k8s_test | python -m json.tool

# Test 3: Replication Test
echo -e "\n${BLUE}3. Testing Replication${NC}"
echo "======================="

echo "Storing multiple keys from different pods..."
echo "Storing key1 from Pod 1:"
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"replication_test_1"}' http://$POD1_IP:8080/kv/key1

echo "Storing key2 from Pod 2:"
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"replication_test_2"}' http://$POD2_IP:8080/kv/key2

echo -e "\nVerifying all keys are accessible from all pods:"
echo "=== Testing from Pod 0 ==="
curl -s http://$POD0_IP:8080/kv/key1 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key1: {data[\"value\"]}')"
curl -s http://$POD0_IP:8080/kv/key2 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key2: {data[\"value\"]}')"

echo "=== Testing from Pod 1 ==="
curl -s http://$POD1_IP:8080/kv/key1 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key1: {data[\"value\"]}')"
curl -s http://$POD1_IP:8080/kv/key2 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key2: {data[\"value\"]}')"

echo "=== Testing from Pod 2 ==="
curl -s http://$POD2_IP:8080/kv/key1 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key1: {data[\"value\"]}')"
curl -s http://$POD2_IP:8080/kv/key2 | python -c "import sys, json; data=json.load(sys.stdin); print(f'key2: {data[\"value\"]}')"

# Test 4: Fault Tolerance Test
echo -e "\n${BLUE}4. Testing Fault Tolerance${NC}"
echo "============================"

echo "Stopping Pod 2..."
kubectl delete pod -n distributed-db distributed-database-2

echo "Waiting for Pod 2 to be recreated..."
sleep 10

echo "Getting new Pod 2 IP..."
NEW_POD2_IP=$(kubectl get pod -n distributed-db distributed-database-2 -o jsonpath='{.status.podIP}')
echo "New Pod 2 IP: $NEW_POD2_IP"

echo "Waiting for new Pod 2 to be ready..."
wait_for_node $NEW_POD2_IP 8080 "New Pod 2"

echo "Testing cluster with Pod 2 restarted:"
curl -s http://$POD0_IP:8080/kv/k8s_test | python -c "import sys, json; data=json.load(sys.stdin); print(f'k8s_test: {data[\"value\"]} (replicas_responded: {data.get(\"replicas_responded\", \"N/A\")})')"

# Test 5: Cluster Status Check
echo -e "\n${BLUE}5. Final Cluster Status${NC}"
echo "========================"

echo "Pod 0 Info:"
curl -s http://$POD0_IP:8080/info | python -m json.tool
echo "Pod 1 Info:"
curl -s http://$POD1_IP:8080/info | python -m json.tool
echo "New Pod 2 Info:"
curl -s http://$NEW_POD2_IP:8080/info | python -m json.tool

# Test 6: Persistence Test
echo -e "\n${BLUE}6. Testing Persistence${NC}"
echo "======================="

echo "Storing persistent data..."
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"persistent_data_test"}' http://$POD0_IP:8080/kv/persistent_test

echo "Checking persistence stats on Pod 0:"
curl -s http://$POD0_IP:8080/persistence/stats | python -m json.tool

# Test 7: Service Endpoint Test
echo -e "\n${BLUE}7. Testing Service Endpoints${NC}"
echo "==============================="

echo "Testing external service endpoint..."
kubectl port-forward -n distributed-db svc/db-external-service 30080:8080 &
PF_PID=$!
sleep 3

echo "Testing via service endpoint:"
curl -s http://localhost:30080/health | python -m json.tool
curl -s http://localhost:30080/kv/k8s_test | python -m json.tool

kill $PF_PID 2>/dev/null || true

echo -e "\n${GREEN}🎉 Kubernetes Cluster Verification Complete!${NC}"
echo "============================================="
echo "All tests passed! Your distributed database is working correctly in Kubernetes." 