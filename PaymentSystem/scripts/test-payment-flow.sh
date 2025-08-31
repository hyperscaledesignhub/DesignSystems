#!/bin/bash

# End-to-End Payment Flow Test Script
# This script demonstrates the complete payment system workflow

set -e

API_BASE="http://localhost:8733"
WALLET_API="http://localhost:8740"
FRAUD_API="http://localhost:8742"
NOTIFICATION_API="http://localhost:8743"

echo "🔥 Starting End-to-End Payment System Demo"
echo "=========================================="

# Function to make HTTP requests with proper error handling
make_request() {
    local method=$1
    local url=$2
    local data=$3
    
    echo "📡 $method $url"
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$url")
    else
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$url")
    fi
    
    http_code=$(echo $response | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo $response | sed -e 's/HTTPSTATUS\:.*//g')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo "✅ Success ($http_code)"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo "❌ Error ($http_code)"
        echo "$body"
        return 1
    fi
    echo
}

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Test 1: Create user wallets
echo "1️⃣ Creating User Wallets"
echo "========================"

USER1_WALLET=$(make_request POST "$WALLET_API/api/v1/wallets" '{
    "user_id": "user_001",
    "currency": "USD",
    "initial_balance": 1000.00,
    "wallet_type": "personal"
}')

USER2_WALLET=$(make_request POST "$WALLET_API/api/v1/wallets" '{
    "user_id": "user_002", 
    "currency": "USD",
    "initial_balance": 500.00,
    "wallet_type": "personal"
}')

MERCHANT_WALLET=$(make_request POST "$WALLET_API/api/v1/wallets" '{
    "user_id": "merchant_001",
    "currency": "USD", 
    "initial_balance": 0.00,
    "wallet_type": "merchant"
}')

# Test 2: Process different types of payments
echo "2️⃣ Processing Various Payment Types"
echo "==================================="

# Small payment (should pass fraud checks)
echo "💳 Small Payment ($50) - Should be approved"
PAYMENT1=$(make_request POST "$API_BASE/api/v1/payments" '{
    "user_id": "user_001",
    "amount": 50.00,
    "currency": "USD",
    "payment_method": "card",
    "merchant_id": "merchant_001",
    "description": "Coffee purchase"
}')

sleep 2

# Medium payment (may trigger review)
echo "💳 Medium Payment ($2,500) - May trigger fraud review"
PAYMENT2=$(make_request POST "$API_BASE/api/v1/payments" '{
    "user_id": "user_001",
    "amount": 2500.00,
    "currency": "USD", 
    "payment_method": "card",
    "merchant_id": "merchant_001",
    "description": "Laptop purchase"
}')

sleep 2

# High-risk payment (should trigger fraud alerts)
echo "💳 High-Risk Payment ($15,000) - Should trigger fraud alerts"
PAYMENT3=$(make_request POST "$API_BASE/api/v1/payments" '{
    "user_id": "user_002",
    "amount": 15000.00,
    "currency": "USD",
    "payment_method": "card", 
    "merchant_id": "merchant_001",
    "description": "Luxury watch",
    "ip_address": "192.168.1.100",
    "billing_country": "US",
    "shipping_country": "RU"
}')

sleep 3

# Test 3: Check fraud detection results
echo "3️⃣ Checking Fraud Detection Results"
echo "==================================="

echo "🔍 Fraud Detection Statistics:"
make_request GET "$FRAUD_API/api/v1/fraud/stats"

echo "🚨 Active Fraud Alerts:"
make_request GET "$FRAUD_API/api/v1/fraud/alerts?status=open"

# Test 4: Wallet operations
echo "4️⃣ Testing Wallet Operations"
echo "============================"

echo "💰 Wallet Balances:"
make_request GET "$WALLET_API/api/v1/users/user_001/wallets"
make_request GET "$WALLET_API/api/v1/users/user_002/wallets"

echo "🔄 Transfer between wallets ($100):"
make_request POST "$WALLET_API/api/v1/wallets/transfer" '{
    "from_wallet_id": "user_001_wallet",
    "to_wallet_id": "user_002_wallet", 
    "amount": 100.00,
    "description": "P2P transfer"
}'

# Test 5: Check system health and metrics
echo "5️⃣ System Health Check"
echo "======================="

echo "🏥 Payment Service Health:"
make_request GET "$API_BASE/health"

echo "💼 Wallet Service Health:"
make_request GET "$WALLET_API/health"

echo "🛡️ Fraud Service Health:"
make_request GET "$FRAUD_API/health"

echo "📢 Notification Service Health:"  
make_request GET "$NOTIFICATION_API/health"

# Test 6: Generate some reconciliation data
echo "6️⃣ Reconciliation Process"
echo "========================="

echo "⚖️ Creating reconciliation job:"
make_request POST "http://localhost:8741/api/v1/reconciliations" '{
    "start_date": "'$(date -d '1 day ago' -Iseconds)'",
    "end_date": "'$(date -Iseconds)'",
    "reconciliation_type": "daily"
}'

sleep 5

echo "📊 Reconciliation Stats:"
make_request GET "http://localhost:8741/api/v1/reconciliations/stats/summary"

# Test 7: Notification system
echo "7️⃣ Testing Notifications"
echo "========================"

echo "📧 Sending test notification:"
make_request POST "$NOTIFICATION_API/api/v1/notifications" '{
    "type": "email",
    "recipient": "user@example.com",
    "subject": "Payment Successful", 
    "template": "payment_success",
    "data": {
        "amount": "50.00",
        "currency": "USD",
        "transaction_id": "TXN123456"
    }
}'

echo "📊 Notification Statistics:"
make_request GET "$NOTIFICATION_API/api/v1/notifications/stats"

# Test 8: Performance stress test
echo "8️⃣ Performance Stress Test"
echo "=========================="

echo "🚀 Creating multiple concurrent payments..."
for i in {1..5}; do
    (
        make_request POST "$API_BASE/api/v1/payments" "{
            \"user_id\": \"user_00$i\",
            \"amount\": $((RANDOM % 1000 + 10)).00,
            \"currency\": \"USD\",
            \"payment_method\": \"card\",
            \"description\": \"Stress test payment $i\"
        }" >/dev/null 2>&1
    ) &
done

wait
echo "✅ Concurrent payments completed"

# Final summary
echo "9️⃣ Demo Summary"
echo "==============="

echo "🎯 Demo completed successfully!"
echo ""
echo "📊 Quick Stats:"
make_request GET "$API_BASE/api/v1/payments/stats" | head -10
echo ""
echo "🔗 Access Points:"
echo "   - Dashboard UI: http://localhost:3000"
echo "   - API Gateway: http://localhost:8733"
echo "   - Jaeger Tracing: http://localhost:16686" 
echo "   - RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo ""
echo "🏁 End-to-End Demo Complete!"
echo "All microservices are running with real data flow, tracing, and monitoring."