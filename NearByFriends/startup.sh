#!/bin/bash

# Startup script for Nearby Friends demo services
# This script starts all required services as individual Docker containers

echo "🚀 Starting Nearby Friends Demo Services..."
echo "==========================================="

# Create a Docker network
echo "📦 Creating Docker network..."
docker network create nearby-friends-network 2>/dev/null || echo "Network already exists"

# Start PostgreSQL
echo "🗄️  Starting PostgreSQL..."
docker run -d \
  --name postgres-nearbyf \
  --network nearby-friends-network \
  -e POSTGRES_DB=nearbyfriendsdb \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5732:5432 \
  postgres:15

# Start Redis
echo "💾 Starting Redis..."
docker run -d \
  --name redis-nearbyf \
  --network nearby-friends-network \
  -p 6679:6379 \
  redis:7-alpine

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 5

# Check if PostgreSQL is ready
until docker exec postgres-nearbyf pg_isready -U user -d nearbyfriendsdb > /dev/null 2>&1; do
  echo "   Waiting for PostgreSQL..."
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Check if Redis is ready
until docker exec redis-nearbyf redis-cli ping > /dev/null 2>&1; do
  echo "   Waiting for Redis..."
  sleep 2
done
echo "✅ Redis is ready!"

# Build and start User Service
echo "👤 Building and starting User Service..."
cd user-service
docker build -t user-service:latest .
docker run -d \
  --name user-service \
  --network nearby-friends-network \
  -e POSTGRES_URL=postgresql://user:password@postgres-nearbyf:5432/nearbyfriendsdb \
  -e REDIS_URL=redis://redis-nearbyf:6379 \
  -e JWT_SECRET=super-secret-key-change-in-production \
  -p 8901:8901 \
  user-service:latest
cd ..

# Wait for User Service to be ready
echo "⏳ Waiting for User Service to be ready..."
until curl -f http://localhost:8901/health > /dev/null 2>&1; do
  echo "   Waiting for User Service..."
  sleep 2
done
echo "✅ User Service is ready!"

# Build and start Friend Service
echo "👥 Building and starting Friend Service..."
cd friend-service
docker build -t friend-service:latest .
docker run -d \
  --name friend-service \
  --network nearby-friends-network \
  -e POSTGRES_URL=postgresql://user:password@postgres-nearbyf:5432/nearbyfriendsdb \
  -e JWT_SECRET=super-secret-key-change-in-production \
  -p 8902:8902 \
  friend-service:latest
cd ..

# Wait for Friend Service to be ready
echo "⏳ Waiting for Friend Service to be ready..."
until curl -f http://localhost:8902/health > /dev/null 2>&1; do
  echo "   Waiting for Friend Service..."
  sleep 2
done
echo "✅ Friend Service is ready!"

# Build and start Location Service
echo "📍 Building and starting Location Service..."
cd location-service
docker build -t location-service:latest .
docker run -d \
  --name location-service \
  --network nearby-friends-network \
  -e POSTGRES_URL=postgresql://user:password@postgres-nearbyf:5432/nearbyfriendsdb \
  -e REDIS_URL=redis://redis-nearbyf:6379 \
  -e JWT_SECRET=super-secret-key-change-in-production \
  -e FRIEND_SERVICE_URL=http://friend-service:8902 \
  -p 8903:8903 \
  location-service:latest
cd ..

# Wait for Location Service to be ready
echo "⏳ Waiting for Location Service to be ready..."
until curl -f http://localhost:8903/health > /dev/null 2>&1; do
  echo "   Waiting for Location Service..."
  sleep 2
done
echo "✅ Location Service is ready!"

# Build and start WebSocket Gateway
echo "🔗 Building and starting WebSocket Gateway..."
cd websocket-gateway
docker build -t websocket-gateway:latest .
docker run -d \
  --name websocket-gateway \
  --network nearby-friends-network \
  -e REDIS_URL=redis://redis-nearbyf:6379 \
  -e JWT_SECRET=super-secret-key-change-in-production \
  -e LOCATION_SERVICE_URL=http://location-service:8903 \
  -e FRIEND_SERVICE_URL=http://friend-service:8902 \
  -p 8904:8904 \
  websocket-gateway:latest
cd ..

# Wait for WebSocket Gateway to be ready
echo "⏳ Waiting for WebSocket Gateway to be ready..."
until curl -f http://localhost:8904/health > /dev/null 2>&1; do
  echo "   Waiting for WebSocket Gateway..."
  sleep 2
done
echo "✅ WebSocket Gateway is ready!"

# Build and start API Gateway
echo "🌐 Building and starting API Gateway..."
cd api-gateway
docker build -t api-gateway:latest .
docker run -d \
  --name api-gateway \
  --network nearby-friends-network \
  -e REDIS_URL=redis://redis-nearbyf:6379 \
  -e USER_SERVICE_URL=http://user-service:8901 \
  -e FRIEND_SERVICE_URL=http://friend-service:8902 \
  -e LOCATION_SERVICE_URL=http://location-service:8903 \
  -e WEBSOCKET_GATEWAY_URL=http://websocket-gateway:8904 \
  -p 8900:8900 \
  api-gateway:latest
cd ..

# Wait for API Gateway to be ready
echo "⏳ Waiting for API Gateway to be ready..."
until curl -f http://localhost:8900/health > /dev/null 2>&1; do
  echo "   Waiting for API Gateway..."
  sleep 2
done
echo "✅ API Gateway is ready!"

# Start UI Service (direct Python process)
echo "🖥️  Starting UI Service..."
python3 serve_demo.py > ui_service.log 2>&1 &
UI_SERVICE_PID=$!
echo $UI_SERVICE_PID > ui_service.pid

# Wait for UI Service to be ready
echo "⏳ Waiting for UI Service to be ready..."
until curl -f http://localhost:3000/demo_ui.html > /dev/null 2>&1; do
  echo "   Waiting for UI Service..."
  sleep 2
done
echo "✅ UI Service is ready!"

echo ""
echo "==========================================="
echo "✨ All services started successfully!"
echo ""

# Setup demo data automatically
echo "🔧 Setting up demo data..."
sleep 3  # Give services a moment to be fully ready
python3 setup_demo_data.py
if [ $? -eq 0 ]; then
    echo "✅ Demo data populated successfully!"
else
    echo "⚠️  Warning: Demo data setup had issues. You may need to run: python3 setup_demo_data.py manually"
fi

echo ""
echo "📊 Service Status:"
echo "  - PostgreSQL: http://localhost:5732 (DB port)"
echo "  - Redis: http://localhost:6679"
echo "  - API Gateway: http://localhost:8900 (Main Entry Point)"
echo "  - User Service: http://localhost:8901 (Docker)"
echo "  - Friend Service: http://localhost:8902 (Docker)"
echo "  - Location Service: http://localhost:8903 (Docker)"
echo "  - WebSocket Gateway: ws://localhost:8904/ws (Docker)"
echo "  - UI Service: http://localhost:3000 (Direct Python Process)"
echo ""
echo "📝 Health Check Endpoints:"
echo "  - API Gateway: http://localhost:8900/health"
echo "  - User Service: http://localhost:8901/health"
echo "  - Friend Service: http://localhost:8902/health"
echo "  - Location Service: http://localhost:8903/health"
echo "  - WebSocket Gateway: http://localhost:8904/health"
echo "  - UI Service: http://localhost:3000/demo_ui.html"
echo ""
echo "🎉 Demo data has been automatically populated with:"
echo "  - 10 demo users with initial locations"
echo "  - 25 friend relationships"
echo "  - Sample activity data"
echo ""
echo "🎬 Demo Interface: http://localhost:3000/demo_ui.html"
echo "🔧 To stop all services, run: ./shutdown.sh"
echo "==========================================="