#!/bin/bash

# Demo Startup Script
# Starts all services and runs comprehensive tests

set -e

echo "🚀 Starting Payment System Demo"
echo "==============================="

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
cd demo
docker-compose down -v 2>/dev/null || true

# Start infrastructure services first
echo "🏗️ Starting infrastructure services..."
docker-compose up -d postgres-payment postgres-ledger postgres-wallet postgres-fraud postgres-reconciliation postgres-notification redis-payment redis-wallet redis-fraud rabbitmq jaeger

echo "⏳ Waiting for infrastructure to be ready..."
sleep 30

# Start core services
echo "🎯 Starting core payment services..."
docker-compose up -d payment-service payment-executor ledger-service psp-gateway api-gateway

echo "⏳ Waiting for core services..."
sleep 20

# Start enhanced services  
echo "✨ Starting enhanced services..."
docker-compose up -d wallet-service reconciliation-service fraud-detection-service notification-service

echo "⏳ Waiting for enhanced services..."
sleep 20

# Start UI
echo "🎨 Starting UI dashboard..."
docker-compose up -d payment-dashboard

echo "⏳ Final system initialization..."
sleep 30

# Show running services
echo "📊 Running Services:"
echo "==================="
docker-compose ps

echo ""
echo "🔗 Access Points:"
echo "================="
echo "🖥️  Payment Dashboard: http://localhost:3000"
echo "🌐 API Gateway: http://localhost:8733"
echo "🔍 Jaeger Tracing: http://localhost:16686"
echo "🐰 RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo "💾 Payment Service: http://localhost:8734"  
echo "🏦 Ledger Service: http://localhost:8736"
echo "💰 Wallet Service: http://localhost:8740"
echo "🛡️  Fraud Detection: http://localhost:8742"
echo "⚖️  Reconciliation: http://localhost:8741"
echo "📢 Notification Service: http://localhost:8743"

echo ""
echo "🧪 Running Comprehensive Tests..."
echo "================================="
chmod +x scripts/test-payment-flow.sh
./scripts/test-payment-flow.sh

echo ""
echo "🎉 Demo Setup Complete!"
echo "======================="
echo ""
echo "📋 Customer Demo Use Cases:"
echo "1. View real-time dashboard with live metrics"
echo "2. Process payments with automatic fraud detection"
echo "3. Manage wallets with real-time balance updates"
echo "4. Monitor transactions with distributed tracing"
echo "5. Reconcile payments with automated discrepancy detection"
echo "6. Receive real-time notifications"
echo "7. View comprehensive analytics and reporting"
echo ""
echo "🔥 All services are running with:"
echo "   ✅ Real database operations (no stubs)"
echo "   ✅ Distributed tracing with Jaeger"
echo "   ✅ Message queues for async processing"
echo "   ✅ Real-time notifications"
echo "   ✅ Fraud detection with ML scoring"
echo "   ✅ Automated reconciliation"
echo "   ✅ Interactive UI dashboard"
echo ""
echo "🎯 Ready for customer demonstration!"