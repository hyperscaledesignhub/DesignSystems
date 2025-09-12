#!/bin/bash

echo "🐳 Starting Google Maps System - All Services"
echo "============================================="

# Create network if it doesn't exist
docker network create maps-network 2>/dev/null || echo "Network maps-network already exists"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker stop redis location-service navigation-service places-service traffic-service 2>/dev/null || true
docker rm redis location-service navigation-service places-service traffic-service 2>/dev/null || true

# Build and start all services
echo ""
echo "🏗️  Building and starting services..."

# Redis Service (Port 6379) - Required for Places Service
echo "▶️  Starting Redis..."
docker run -d \
  --name redis \
  --network maps-network \
  -p 6379:6379 \
  redis:alpine

# Location Service (Port 8086)
echo "▶️  Starting Location Service..."
docker build -f Dockerfile.location -t location-service .
docker run -d \
  --name location-service \
  --network maps-network \
  -p 8086:8086 \
  location-service

# Navigation Service (Port 8081)
echo "▶️  Starting Navigation Service..."
docker build -f Dockerfile.navigation -t navigation-service .
docker run -d \
  --name navigation-service \
  --network maps-network \
  -p 8081:8081 \
  navigation-service

# Places Service (Port 8083)
echo "▶️  Starting Places Service..."
docker build -f Dockerfile.places -t places-service .
docker run -d \
  --name places-service \
  --network maps-network \
  -e REDIS_HOST=redis \
  -p 8083:8083 \
  places-service

# Traffic Service (Port 8084)
echo "▶️  Starting Traffic Service..."
docker build -f Dockerfile.traffic -t traffic-service .
docker run -d \
  --name traffic-service \
  --network maps-network \
  -p 8084:8084 \
  traffic-service

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "🔍 Checking service health..."
echo "Redis: redis://localhost:6379"
echo "Location Service: http://localhost:8086/health"
echo "Navigation Service: http://localhost:8081/health"  
echo "Places Service: http://localhost:8083/health"
echo "Traffic Service: http://localhost:8084/health"

echo ""
echo "✅ All services started! Docker containers running:"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

# UI Service (Port 3002) - Web Interface
echo "▶️  Starting UI Service..."
cd ui && python3 start_ui.py &
UI_PID=$!
cd ..
echo "UI Service started with PID: $UI_PID"

echo ""
echo "🌐 All services are now running:"
echo "• UI: http://localhost:3002"
echo "• Redis: redis://localhost:6379"  
echo "• Location Service: http://localhost:8086/health"
echo "• Navigation Service: http://localhost:8081/health"
echo "• Places Service: http://localhost:8083/health"
echo "• Traffic Service: http://localhost:8084/health"
