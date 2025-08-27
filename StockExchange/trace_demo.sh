#!/bin/bash

# Demo script to generate traces for different flows

echo "=== Stock Exchange Tracing Demo ==="
echo "This script will generate traces for different flows"
echo ""

# Get a token first
echo "1. User Registration and Login Flow"
echo "------------------------------------"

# Register a new user
echo "Registering new user..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8347/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trace_demo@test.com",
    "username": "trace_demo",
    "password": "demo123"
  }')

echo "User registered: $(echo $REGISTER_RESPONSE | jq -r '.username')"

# Login
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8347/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "trace_demo", "password": "demo123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "Got token: ${TOKEN:0:20}..."

sleep 2

echo ""
echo "2. Wallet Creation and Funding Flow"
echo "------------------------------------"

# Add funds (creates wallet automatically)
echo "Adding funds to wallet..."
curl -s -X POST http://localhost:8347/wallet/add-funds \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100000}' | jq '.'

sleep 2

# Check balance
echo "Checking wallet balance..."
curl -s -X GET http://localhost:8347/wallet/balance \
  -H "Authorization: Bearer $TOKEN" | jq '.'

sleep 2

echo ""
echo "3. Order Placement Flow"
echo "------------------------"

# Place a buy order
echo "Placing BUY order for AAPL..."
BUY_ORDER=$(curl -s -X POST http://localhost:8347/v1/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "quantity": 10,
    "price": 150.50
  }')

echo $BUY_ORDER | jq '.'
ORDER_ID=$(echo $BUY_ORDER | jq -r '.id')

sleep 2

echo ""
echo "4. Order Query Flow"
echo "-------------------"

# Get orders
echo "Fetching user orders..."
curl -s -X GET http://localhost:8347/v1/orders \
  -H "Authorization: Bearer $TOKEN" | jq '.'

sleep 2

echo ""
echo "5. Portfolio and Reporting Flow"
echo "--------------------------------"

# Get positions
echo "Fetching portfolio positions..."
curl -s -X GET http://localhost:8347/reports/positions \
  -H "Authorization: Bearer $TOKEN" | jq '.'

sleep 2

# Get trades
echo "Fetching trade history..."
curl -s -X GET http://localhost:8347/reports/trades \
  -H "Authorization: Bearer $TOKEN" | jq '.'

sleep 2

echo ""
echo "6. Order Cancellation Flow"
echo "--------------------------"

if [ ! -z "$ORDER_ID" ]; then
  echo "Cancelling order $ORDER_ID..."
  curl -s -X DELETE http://localhost:8347/v1/order/$ORDER_ID \
    -H "Authorization: Bearer $TOKEN" | jq '.'
fi

echo ""
echo "============================================"
echo "Traces generated successfully!"
echo ""
echo "View traces in Jaeger UI: http://localhost:16686"
echo ""
echo "Select 'client-gateway' service and click 'Find Traces'"
echo "You'll see the complete request flow through all services"
echo "============================================"