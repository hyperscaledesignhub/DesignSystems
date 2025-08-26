#!/bin/bash

# Essential Wallet System - Start Script

echo "🚀 Starting Essential Wallet System..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Navigate to deployments directory
cd deployments

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Start all services
echo "🔧 Starting microservices..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize (30 seconds)..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
curl -s http://localhost:9080/api/v1/health/services | python3 -m json.tool

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📍 Access points:"
echo "   - Frontend: Run 'cd frontend && npm install && npm run dev'"
echo "   - API Gateway: http://localhost:9080"
echo "   - Health Check: http://localhost:9080/api/v1/health/services"
echo ""
echo "📋 View logs:"
echo "   docker-compose logs -f [service-name]"
echo ""
echo "🛑 To stop:"
echo "   docker-compose down"
echo ""