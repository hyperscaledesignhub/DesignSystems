#!/bin/bash

echo "🚀 Starting All Microservices (Individual Docker Containers)"
echo "============================================================="

# Stop any existing containers first
echo "🧹 Cleaning up existing containers..."
docker stop crawler-gateway crawler-deduplication crawler-parser crawler-downloader crawler-frontier crawler-redis 2>/dev/null
docker rm crawler-gateway crawler-deduplication crawler-parser crawler-parser crawler-downloader crawler-frontier crawler-redis 2>/dev/null

# Create network
echo ""
echo "Step 1: Creating Docker network..."
docker network create crawler-network --driver bridge 2>/dev/null || echo "✅ Network already exists"

echo ""
echo "Step 2: Building Docker images..."

# Build Redis (just tag the official image)
docker pull redis:7-alpine
docker tag redis:7-alpine crawler-redis:latest

# Build microservices
services=("frontier" "downloader" "parser" "deduplication" "extractor" "storage" "gateway")
for service in "${services[@]}"; do
    echo "Building $service..."
    docker build --build-arg SERVICE_NAME=$service -t crawler-$service:latest . || exit 1
done

echo ""
echo "Step 3: Starting services..."

# Start Redis first
echo "📦 Starting Redis..."
docker run -d \
    --name crawler-redis \
    --network crawler-network \
    -p 6379:6379 \
    -v crawler-redis-data:/data \
    --restart unless-stopped \
    crawler-redis:latest

sleep 5

# Start Frontier
echo "📋 Starting Frontier..."
docker run -d \
    --name crawler-frontier \
    --network crawler-network \
    -p 5001:5000 \
    -e REDIS_HOST=crawler-redis \
    -e REDIS_PORT=6379 \
    -e PORT=5000 \
    --restart unless-stopped \
    crawler-frontier:latest

# Start Downloader
echo "⬇️  Starting Downloader..."
docker run -d \
    --name crawler-downloader \
    --network crawler-network \
    -p 5002:5000 \
    -e REDIS_HOST=crawler-redis \
    -e REDIS_PORT=6379 \
    -e PORT=5000 \
    --restart unless-stopped \
    crawler-downloader:latest

# Start Parser
echo "📄 Starting Parser..."
docker run -d \
    --name crawler-parser \
    --network crawler-network \
    -p 5003:5000 \
    -e PORT=5000 \
    --restart unless-stopped \
    crawler-parser:latest

# Start Deduplication
echo "🔍 Starting Deduplication..."
docker run -d \
    --name crawler-deduplication \
    --network crawler-network \
    -p 5004:5000 \
    -e REDIS_HOST=crawler-redis \
    -e REDIS_PORT=6379 \
    -e PORT=5000 \
    --restart unless-stopped \
    crawler-deduplication:latest

# Start Extractor
echo "🔗 Starting URL Extractor..."
docker run -d \
    --name crawler-extractor \
    --network crawler-network \
    -p 5005:5000 \
    -e PORT=5000 \
    --restart unless-stopped \
    crawler-extractor:latest

# Start Storage
echo "💾 Starting Content Storage..."
docker run -d \
    --name crawler-storage \
    --network crawler-network \
    -p 5006:5000 \
    -e PORT=5000 \
    -e STORAGE_PATH=/app/data \
    -v crawler-storage-data:/app/data \
    --restart unless-stopped \
    crawler-storage:latest

sleep 5

# Start Gateway last
echo "🌐 Starting Gateway..."
docker run -d \
    --name crawler-gateway \
    --network crawler-network \
    -p 5010:5000 \
    -e FRONTIER_URL=http://crawler-frontier:5000 \
    -e DOWNLOADER_URL=http://crawler-downloader:5000 \
    -e PARSER_URL=http://crawler-parser:5000 \
    -e DEDUP_URL=http://crawler-deduplication:5000 \
    -e REDIS_HOST=crawler-redis \
    -e REDIS_PORT=6379 \
    -e PORT=5000 \
    --restart unless-stopped \
    crawler-gateway:latest

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "🎯 Service Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep crawler-

echo ""
echo "✅ All services started successfully!"

# Start the UI Dashboard
echo ""
echo "🖥️  Starting UI Dashboard..."
# Check if UI is already running
UI_PID=$(lsof -ti :8090 2>/dev/null)
if [ ! -z "$UI_PID" ]; then
    echo "UI already running on port 8090 (PID: $UI_PID)"
else
    # Start the dashboard in background
    cd "$(dirname "$0")/.." && nohup python3 microservices_dashboard.py > ui.log 2>&1 &
    echo "UI Dashboard starting on port 8090..."
    sleep 3
    # Verify it started
    UI_PID=$(lsof -ti :8090 2>/dev/null)
    if [ ! -z "$UI_PID" ]; then
        echo "UI Dashboard started successfully (PID: $UI_PID)"
    else
        echo "⚠️  UI Dashboard failed to start. Check ui.log for details"
    fi
fi

echo ""
echo "📊 Service Endpoints:"
echo "   🖥️  UI Dashboard:     http://localhost:8090"
echo "   🌐 API Gateway:     http://localhost:5010/health"
echo "   📋 URL Frontier:    http://localhost:5001/health"
echo "   ⬇️  Downloader:      http://localhost:5002/health"
echo "   📄 Parser:          http://localhost:5003/health"
echo "   🔍 Deduplication:   http://localhost:5004/health"
echo "   🔗 URL Extractor:   http://localhost:5005/health"
echo "   💾 Content Storage: http://localhost:5006/health"
echo "   🗄️  Redis:           redis://localhost:6379"