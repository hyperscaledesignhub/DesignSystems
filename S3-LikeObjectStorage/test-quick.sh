#!/bin/bash

# Quick test script for immediate validation
# Runs a subset of tests for fast feedback

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

GATEWAY_URL="${GATEWAY_URL:-http://localhost:7841}"

echo -e "${BLUE}🚀 S3 Storage System - Quick Test${NC}"
echo "Gateway URL: $GATEWAY_URL"
echo ""

# Check if services are running
echo -e "${BLUE}Checking services...${NC}"
if ! curl -s "$GATEWAY_URL/health" > /dev/null; then
    echo -e "${RED}❌ Services not reachable at $GATEWAY_URL${NC}"
    echo "Start services first:"
    echo "  docker-compose up -d"
    echo "  kubectl get pods -n s3-storage"
    exit 1
fi
echo -e "${GREEN}✅ Services are running${NC}"

# Get API key
echo -e "${BLUE}Getting API key...${NC}"
if [ -z "$API_KEY" ]; then
    # Try Docker Compose
    if command -v docker-compose &> /dev/null; then
        API_KEY=$(docker-compose logs identity-service 2>/dev/null | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //' || echo "")
    fi
    
    # Try Kubernetes
    if [ -z "$API_KEY" ] && command -v kubectl &> /dev/null; then
        API_KEY=$(kubectl logs -n s3-storage -l app=identity-service 2>/dev/null | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //' || echo "")
    fi
    
    if [ -z "$API_KEY" ]; then
        echo -e "${RED}❌ Could not get API key. Set API_KEY environment variable.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ Got API key${NC}"

# Quick functional test
echo -e "${BLUE}Running quick functional test...${NC}"

BUCKET_NAME="quick-test-$(date +%s)"
AUTH_HEADER="Authorization: Bearer $API_KEY"

# Test 1: Create bucket
echo -n "  Create bucket... "
if curl -s -X POST "$GATEWAY_URL/buckets" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"bucket_name\": \"$BUCKET_NAME\"}" | grep -q '"bucket_name"'; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    exit 1
fi

# Test 2: List buckets
echo -n "  List buckets... "
if curl -s -X GET "$GATEWAY_URL/buckets" \
    -H "$AUTH_HEADER" | grep -q "$BUCKET_NAME"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    exit 1
fi

# Test 3: Upload object
echo -n "  Upload object... "
if echo "Quick test content" | curl -s -X PUT "$GATEWAY_URL/buckets/$BUCKET_NAME/objects/test.txt" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: text/plain" \
    --data-binary @- | grep -q '"etag"'; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    exit 1
fi

# Test 4: Download object
echo -n "  Download object... "
DOWNLOADED_CONTENT=$(curl -s -X GET "$GATEWAY_URL/buckets/$BUCKET_NAME/objects/test.txt" -H "$AUTH_HEADER")
if [ "$DOWNLOADED_CONTENT" = "Quick test content" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    echo "Expected: 'Quick test content'"
    echo "Got: '$DOWNLOADED_CONTENT'"
    exit 1
fi

# Test 5: List objects
echo -n "  List objects... "
if curl -s -X GET "$GATEWAY_URL/buckets/$BUCKET_NAME/objects" \
    -H "$AUTH_HEADER" | grep -q "test.txt"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    exit 1
fi

# Test 6: Delete object
echo -n "  Delete object... "
if curl -s -X DELETE "$GATEWAY_URL/buckets/$BUCKET_NAME/objects/test.txt" \
    -H "$AUTH_HEADER" -w "%{http_code}" | grep -q "204"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    exit 1
fi

# Test 7: Delete bucket
echo -n "  Delete bucket... "
if curl -s -X DELETE "$GATEWAY_URL/buckets/$BUCKET_NAME" \
    -H "$AUTH_HEADER" -w "%{http_code}" | grep -qE "(200|204)"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    exit 1
fi

# Test 8: Authentication check
echo -n "  Authentication check... "
if curl -s -X GET "$GATEWAY_URL/buckets" \
    -H "Authorization: Bearer invalid_key" \
    -w "%{http_code}" | grep -q "401"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 All quick tests passed!${NC}"
echo ""
echo "System is working correctly. For comprehensive testing, run:"
echo -e "${BLUE}  ./run_all_tests.sh${NC}"