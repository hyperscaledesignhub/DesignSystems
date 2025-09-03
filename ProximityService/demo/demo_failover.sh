#!/bin/bash

# Demo script for testing failover scenarios

API_BASE="http://localhost:7891"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  PROXIMITY SERVICE FAILOVER DEMO   ${NC}"
echo -e "${GREEN}=====================================${NC}"

function test_operation() {
    echo -e "\n${YELLOW}Testing: $1${NC}"
    curl -s "$2" > /dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Success${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
    fi
}

function health_check() {
    echo -e "\n${YELLOW}Health Check:${NC}"
    response=$(curl -s "$API_BASE/health")
    echo "$response" | python3 -m json.tool | head -20
}

# 1. Normal operation test
echo -e "\n${GREEN}1. TESTING NORMAL OPERATION${NC}"
test_operation "Search nearby businesses" "$API_BASE/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000"
test_operation "Get business details" "$API_BASE/businesses/test-id"
health_check

# 2. Database failover test
echo -e "\n${GREEN}2. DATABASE FAILOVER TEST${NC}"
echo -e "${YELLOW}Stopping primary database...${NC}"
docker-compose stop postgres-primary

sleep 3

echo -e "${YELLOW}Testing read operations (should work with replicas)...${NC}"
test_operation "Search nearby (READ)" "$API_BASE/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000"

echo -e "${YELLOW}Testing write operations (should fail gracefully)...${NC}"
curl -s -X POST "$API_BASE/businesses" \
    -H "Content-Type: application/json" \
    -d '{"name":"Test","latitude":37.7749,"longitude":-122.4194,"address":"Test","city":"SF","state":"CA","country":"USA","category":"Test"}' \
    | python3 -m json.tool

health_check

echo -e "\n${YELLOW}Restoring primary database...${NC}"
docker-compose start postgres-primary
sleep 5

echo -e "${YELLOW}Testing operations after recovery...${NC}"
test_operation "Write operation (POST)" "$API_BASE/businesses"
health_check

# 3. Redis failover test
echo -e "\n${GREEN}3. REDIS CACHE FAILOVER TEST${NC}"
echo -e "${YELLOW}Stopping Redis master...${NC}"
docker-compose stop redis-master

sleep 3

echo -e "${YELLOW}Testing operations with Redis replica...${NC}"
test_operation "Search nearby (with replica cache)" "$API_BASE/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000"

health_check

echo -e "\n${YELLOW}Restoring Redis master...${NC}"
docker-compose start redis-master
sleep 5

health_check

# 4. Rate limiting test
echo -e "\n${GREEN}4. RATE LIMITING TEST${NC}"
echo -e "${YELLOW}Sending 20 rapid requests...${NC}"

success=0
rate_limited=0

for i in {1..20}; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/health")
    if [ "$response" = "200" ]; then
        ((success++))
    elif [ "$response" = "429" ]; then
        ((rate_limited++))
    fi
done

echo -e "${GREEN}✓ Successful requests: $success${NC}"
echo -e "${RED}✗ Rate limited: $rate_limited${NC}"

# 5. Load test
echo -e "\n${GREEN}5. PERFORMANCE TEST${NC}"
echo -e "${YELLOW}Testing response times...${NC}"

total_time=0
count=10

for i in {1..10}; do
    start=$(date +%s%N)
    curl -s "$API_BASE/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000" > /dev/null
    end=$(date +%s%N)
    elapsed=$((($end - $start) / 1000000))
    total_time=$(($total_time + $elapsed))
    echo -e "Request $i: ${elapsed}ms"
done

avg_time=$(($total_time / $count))
echo -e "${GREEN}Average response time: ${avg_time}ms${NC}"

echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}     FAILOVER DEMO COMPLETE!         ${NC}"
echo -e "${GREEN}=====================================${NC}"