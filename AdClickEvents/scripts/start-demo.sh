#!/bin/bash

# AdClick Demo Startup Script
set -e

echo "🎬 Starting AdClick Demo System..."

# Check if already running
if docker-compose ps | grep -q "Up"; then
    echo "⚠️  Demo is already running. Stopping existing containers..."
    docker-compose down
fi

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 45

# Health checks
echo "🔍 Performing health checks..."

check_service() {
    local service_name=$1
    local url=$2
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is healthy"
            return 0
        fi
        echo "⏳ Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name health check failed"
    return 1
}

# Check all services
check_service "InfluxDB" "http://localhost:8086/health"
check_service "Demo API" "http://localhost:8900/health" 
check_service "Demo UI" "http://localhost:3000"
check_service "Query Service" "http://localhost:8908/health"

echo ""
echo "🎉 AdClick Demo System is Ready!"
echo ""
echo "📊 Demo Dashboard: http://localhost:3000"
echo "🔧 Demo API: http://localhost:8900"
echo "📈 Query Service: http://localhost:8908"
echo ""
echo "🎯 Quick Start:"
echo "  1. Open http://localhost:3000"
echo "  2. Go to 'Demo Controls'"
echo "  3. Select a business scenario"
echo "  4. Click 'Start Simulation'"
echo "  5. Explore different dashboard tabs"
echo ""
echo "🎬 Demo Scenarios Available:"
echo "  • E-commerce Holiday Sale"
echo "  • Mobile Gaming Campaign"  
echo "  • Financial Services"
echo "  • Social Media Platform"
echo ""
echo "📋 Useful Commands:"
echo "  • View logs: docker-compose logs -f [service]"
echo "  • Stop demo: docker-compose down"
echo "  • Restart: ./scripts/start-demo.sh"
echo ""