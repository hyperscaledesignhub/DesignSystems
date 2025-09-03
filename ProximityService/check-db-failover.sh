#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Database Failover Status Checker${NC}"
echo "=================================="

echo -e "\n${YELLOW}1. Checking Docker Container Status${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PRIMARY_STATUS=$(docker ps --filter "name=postgres-primary" --format "{{.Status}}" 2>/dev/null)
REPLICA1_STATUS=$(docker ps --filter "name=postgres-replica1" --format "{{.Status}}" 2>/dev/null)
REPLICA2_STATUS=$(docker ps --filter "name=postgres-replica2" --format "{{.Status}}" 2>/dev/null)

echo -e "Primary DB:   ${PRIMARY_STATUS:-${RED}NOT RUNNING${NC}}"
echo -e "Replica 1:    ${REPLICA1_STATUS:-${RED}NOT RUNNING${NC}}"  
echo -e "Replica 2:    ${REPLICA2_STATUS:-${RED}NOT RUNNING${NC}}"

if [ -z "$PRIMARY_STATUS" ]; then
    echo -e "\n${RED}⚠️  PRIMARY DATABASE IS DOWN!${NC}"
    PRIMARY_DOWN=true
else
    echo -e "\n${GREEN}✅ Primary database is running${NC}"
    PRIMARY_DOWN=false
fi

echo -e "\n${YELLOW}2. Testing Database Connectivity${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test primary database connectivity
if [ "$PRIMARY_DOWN" = false ]; then
    if docker exec 10-proximityservice-postgres-primary-1 pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Primary DB: Accepting connections${NC}"
    else
        echo -e "${RED}❌ Primary DB: Not accepting connections${NC}"
        PRIMARY_DOWN=true
    fi
else
    echo -e "${RED}❌ Primary DB: Container not running${NC}"
fi

# Test replica connectivity
REPLICA_AVAILABLE=false
for replica in "replica1" "replica2"; do
    if docker exec "10-proximityservice-postgres-${replica}-1" pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${replica^} DB: Available for reads${NC}"
        REPLICA_AVAILABLE=true
    else
        echo -e "${RED}❌ ${replica^} DB: Not available${NC}"
    fi
done

echo -e "\n${YELLOW}3. Testing Application Read Operations${NC}"  
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test read operations through business service
READ_RESULT=$(curl -s "http://localhost:8921/nearby?latitude=37.7849&longitude=-122.4094&radius=1000" 2>/dev/null)
if echo "$READ_RESULT" | grep -q "businesses"; then
    BUSINESS_COUNT=$(echo "$READ_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('businesses', [])))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ Read operations: Working (found $BUSINESS_COUNT businesses)${NC}"
    READ_WORKING=true
else
    echo -e "${RED}❌ Read operations: Failed${NC}"
    echo "   Response: ${READ_RESULT:0:100}..."
    READ_WORKING=false
fi

echo -e "\n${YELLOW}4. Testing Application Write Operations${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test write operations
WRITE_TEST_DATA='{
    "name": "Failover Test Business",
    "latitude": 37.7850,
    "longitude": -122.4095,
    "address": "123 Failover St",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "category": "Test"
}'

WRITE_RESULT=$(curl -s -X POST "http://localhost:9823/businesses" \
    -H "Content-Type: application/json" \
    -d "$WRITE_TEST_DATA" 2>/dev/null)

if echo "$WRITE_RESULT" | grep -q "Failover Test Business"; then
    echo -e "${GREEN}✅ Write operations: Working${NC}"
    WRITE_WORKING=true
else
    echo -e "${RED}❌ Write operations: Failed${NC}"
    echo "   Response: ${WRITE_RESULT:0:100}..."
    WRITE_WORKING=false
fi

echo -e "\n${YELLOW}5. Checking Service Health Endpoints${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check business service health
BUSINESS_HEALTH=$(curl -s "http://localhost:9823/health" 2>/dev/null)
if echo "$BUSINESS_HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Business Service: Reports healthy${NC}"
    
    # Parse database health from service
    DB_STATUS=$(echo "$BUSINESS_HEALTH" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    db = data.get('database', {})
    primary = db.get('primary', False)
    promoted = db.get('promoted_primary', False)  
    replicas = db.get('replicas', [])
    healthy_replicas = sum(1 for r in replicas if r.get('healthy', False))
    print(f'Primary: {primary}, Promoted: {promoted}, Healthy Replicas: {healthy_replicas}')
except:
    print('Parse error')
" 2>/dev/null)
    echo "   Database Status: $DB_STATUS"
else
    echo -e "${RED}❌ Business Service: Reports unhealthy${NC}"
fi

echo -e "\n${YELLOW}6. Failover Analysis${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$PRIMARY_DOWN" = true ]; then
    echo -e "${RED}🚨 PRIMARY DATABASE FAILURE DETECTED${NC}"
    echo ""
    
    if [ "$READ_WORKING" = true ] && [ "$REPLICA_AVAILABLE" = true ]; then
        echo -e "${GREEN}✅ FAILOVER SUCCESSFUL:${NC}"
        echo "   • Primary database is down"
        echo "   • Read operations continue via replicas"
        echo "   • Application remains available for queries"
        echo ""
        echo -e "${YELLOW}Expected Behavior:${NC}"
        echo "   • ✅ Search/read operations should work"
        echo "   • ❌ Create/update operations should fail"
        echo "   • ⚠️  System running in degraded mode"
    else
        echo -e "${RED}❌ FAILOVER FAILED:${NC}"
        echo "   • Primary database is down"
        echo "   • Read operations also failing"
        echo "   • Complete service outage"
    fi
    
    echo ""
    echo -e "${BLUE}💡 To restore service:${NC}"
    echo "   docker-compose start postgres-primary"
    echo "   # Or use the UI 'Restore Primary' button"
    
else
    echo -e "${GREEN}✅ NORMAL OPERATION:${NC}"
    echo "   • Primary database is running"
    echo "   • All operations should work normally"
    echo ""
    echo -e "${BLUE}💡 To test failover:${NC}"
    echo "   docker-compose stop postgres-primary"
    echo "   # Or use the UI 'Kill Primary DB' button"
fi

echo -e "\n${BLUE}🔧 Manual Commands:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "# Kill primary database:"
echo "docker-compose stop postgres-primary"
echo ""
echo "# Restore primary database:" 
echo "docker-compose start postgres-primary"
echo ""
echo "# Check container status:"
echo "docker-compose ps | grep postgres"
echo ""
echo "# Check application logs:"
echo "docker-compose logs business-service --tail 20"
echo ""