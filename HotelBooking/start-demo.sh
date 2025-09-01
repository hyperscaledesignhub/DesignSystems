#!/bin/bash

echo "🚀 Starting Hotel Booking System Demo..."

# Create Docker network
echo "📡 Creating Docker network..."
docker network create hotel-network 2>/dev/null || echo "Network already exists"

# Build all services
echo "🔨 Building Docker images..."
services=("hotel" "room" "guest" "inventory" "reservation" "payment")

for service in "${services[@]}"; do
    echo "Building $service service..."
    cd services/$service
    docker build -t "${service}-service" .
    cd ../..
done

# Start PostgreSQL
echo "🗄️ Starting PostgreSQL..."
docker run -d \
    --name postgres-db \
    --network hotel-network \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=postgres \
    -p 5432:5432 \
    postgres:13

# Start Redis
echo "🔴 Starting Redis..."
docker run -d \
    --name redis-cache \
    --network hotel-network \
    -p 6379:6379 \
    redis:7-alpine

# Wait for databases to be ready
echo "⏳ Waiting for databases to initialize..."
sleep 10

# Initialize databases
echo "🏗️ Initializing databases..."
docker exec postgres-db createdb -U postgres hotel_db 2>/dev/null || echo "hotel_db already exists"
docker exec postgres-db createdb -U postgres guest_db 2>/dev/null || echo "guest_db already exists"
docker exec postgres-db createdb -U postgres inventory_db 2>/dev/null || echo "inventory_db already exists"
docker exec postgres-db createdb -U postgres reservation_db 2>/dev/null || echo "reservation_db already exists"
docker exec postgres-db createdb -U postgres payment_db 2>/dev/null || echo "payment_db already exists"

# Start all services
echo "🚀 Starting microservices..."

docker run -d \
    --name hotel-service \
    --network hotel-network \
    -p 8001:8001 \
    -e PORT=8001 \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres-db:5432/hotel_db \
    -e REDIS_URL=redis://redis-cache:6379 \
    hotel-service

docker run -d \
    --name room-service \
    --network hotel-network \
    -p 8002:8002 \
    -e PORT=8002 \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres-db:5432/hotel_db \
    -e HOTEL_SERVICE=http://hotel-service:8001 \
    room-service

docker run -d \
    --name guest-service \
    --network hotel-network \
    -p 8003:8003 \
    -e PORT=8003 \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres-db:5432/guest_db \
    guest-service

docker run -d \
    --name inventory-service \
    --network hotel-network \
    -p 8004:8004 \
    -e PORT=8004 \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres-db:5432/inventory_db \
    -e HOTEL_SERVICE=http://hotel-service:8001 \
    -e ROOM_SERVICE=http://room-service:8002 \
    inventory-service

docker run -d \
    --name reservation-service \
    --network hotel-network \
    -p 8005:8005 \
    -e PORT=8005 \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres-db:5432/reservation_db \
    -e HOTEL_SERVICE=http://hotel-service:8001 \
    -e ROOM_SERVICE=http://room-service:8002 \
    -e GUEST_SERVICE=http://guest-service:8003 \
    -e INVENTORY_SERVICE=http://inventory-service:8004 \
    reservation-service

docker run -d \
    --name payment-service \
    --network hotel-network \
    -p 8006:8006 \
    -e PORT=8006 \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres-db:5432/payment_db \
    -e RESERVATION_SERVICE=http://reservation-service:8005 \
    payment-service

echo "⏳ Waiting for services to initialize..."
sleep 15

# Install and start React Frontend
echo "🌐 Installing React Frontend dependencies..."
cd frontend
npm install
echo "🌐 Starting React Frontend..."
npm start &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
cd ..

echo "⏳ Waiting for React Frontend to start..."
sleep 10

echo ""
echo "✅ Demo Started Successfully!"
echo ""
echo "🌐 Frontend UI: http://localhost:3000"
echo "🏨 Hotel Service: http://localhost:8001"
echo "🏠 Room Service: http://localhost:8002"
echo "👤 Guest Service: http://localhost:8003"
echo "📦 Inventory Service: http://localhost:8004"
echo "🎫 Reservation Service: http://localhost:8005"
echo "💳 Payment Service: http://localhost:8006"
echo ""
echo "🎯 Demo Features Available:"
echo "   • Hotel Management (List & View Hotels)"
echo "   • Room Management (Browse & Create Room Types)"
echo "   • Guest Registration & Login"
echo "   • Complete Booking Workflow (6 Steps)"
echo "   • Inventory Management (Check Availability, Reserve/Release)"
echo "   • Payment Processing (Mock Implementation)"
echo "   • Reservation Management (Create, View, Cancel)"
echo "   • Concurrency Control Demo"
echo ""
echo "📱 Login with: demo@example.com / password123"
echo ""
echo "🛑 To stop demo: ./stop-demo.sh"