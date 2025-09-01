#!/bin/bash

echo "Starting Hotel Booking System Services..."
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Stop any existing containers
echo "Cleaning up any existing containers..."
docker stop $(docker ps -aq) 2>/dev/null
docker rm $(docker ps -aq) 2>/dev/null

# Create or ensure Docker network exists
echo -e "${GREEN}Creating Docker network...${NC}"
docker network create hotel-network 2>/dev/null || echo "Network already exists"

# Start PostgreSQL database
echo -e "\n${GREEN}Starting PostgreSQL database...${NC}"
docker run -d \
    --name postgres-db \
    --network hotel-network \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=hotel_db \
    -p 5432:5432 \
    postgres:15-alpine

# Start Redis cache
echo -e "${GREEN}Starting Redis cache...${NC}"
docker run -d \
    --name redis-cache \
    --network hotel-network \
    -p 6379:6379 \
    redis:7-alpine

# Wait for database to be ready
echo -e "${GREEN}Waiting for database to be ready...${NC}"
sleep 5

# Initialize databases
echo -e "${GREEN}Initializing databases...${NC}"
docker exec -i postgres-db psql -U postgres < init-databases.sql

# Build all service images
echo -e "\n${GREEN}Building Docker images...${NC}"
docker build -t hotel-service ./services/hotel
docker build -t room-service ./services/room
docker build -t guest-service ./services/guest
docker build -t reservation-service ./services/reservation
docker build -t inventory-service ./services/inventory
docker build -t payment-service ./services/payment

# Start each service individually
echo -e "\n${GREEN}Starting backend services...${NC}"

# Hotel Service - Port 5001
echo "Starting Hotel Service on port 5001..."
docker run -d \
    --name hotel-service \
    --network hotel-network \
    -p 5001:5001 \
    -e PORT=5001 \
    -e DB_HOST=postgres-db \
    -e DB_NAME=hotel_db \
    -e REDIS_HOST=redis-cache \
    hotel-service

# Room Service - Port 5002  
echo "Starting Room Service on port 5002..."
docker run -d \
    --name room-service \
    --network hotel-network \
    -p 5002:5002 \
    -e PORT=5002 \
    -e DB_HOST=postgres-db \
    -e DB_NAME=hotel_db \
    -e REDIS_HOST=redis-cache \
    -e HOTEL_SERVICE_URL=http://hotel-service:5001 \
    room-service

# Guest Service - Port 5003
echo "Starting Guest Service on port 5003..."
docker run -d \
    --name guest-service \
    --network hotel-network \
    -p 5003:5003 \
    -e PORT=5003 \
    -e DB_HOST=postgres-db \
    -e DB_NAME=guest_db \
    -e REDIS_HOST=redis-cache \
    guest-service

# Inventory Service - Port 5004
echo "Starting Inventory Service on port 5004..."
docker run -d \
    --name inventory-service \
    --network hotel-network \
    -p 5004:5004 \
    -e PORT=5004 \
    -e DB_HOST=postgres-db \
    -e DB_NAME=inventory_db \
    -e REDIS_HOST=redis-cache \
    inventory-service

# Reservation Service - Port 5005
echo "Starting Reservation Service on port 5005..."
docker run -d \
    --name reservation-service \
    --network hotel-network \
    -p 5005:5005 \
    -e PORT=5005 \
    -e DB_HOST=postgres-db \
    -e DB_NAME=reservation_db \
    -e REDIS_HOST=redis-cache \
    -e GUEST_SERVICE_URL=http://guest-service:5003 \
    -e ROOM_SERVICE_URL=http://room-service:5002 \
    -e INVENTORY_SERVICE_URL=http://inventory-service:5004 \
    -e PAYMENT_SERVICE_URL=http://payment-service:5006 \
    reservation-service

# Payment Service - Port 5006
echo "Starting Payment Service on port 5006..."
docker run -d \
    --name payment-service \
    --network hotel-network \
    -p 5006:5006 \
    -e PORT=5006 \
    -e DB_HOST=postgres-db \
    -e DB_NAME=payment_db \
    -e REDIS_HOST=redis-cache \
    payment-service

# Wait for services to be ready
echo -e "\n${GREEN}Waiting for services to be ready...${NC}"
sleep 5

# Check service health
echo -e "\n${GREEN}Checking service health...${NC}"
services=("hotel-service:5001" "room-service:5002" "guest-service:5003" "inventory-service:5004" "reservation-service:5005" "payment-service:5006")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is running on port $port"
    else
        echo -e "${RED}✗${NC} $name failed to start on port $port"
    fi
done

# Start Frontend UI
echo -e "\n${GREEN}Starting Frontend UI...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
nohup npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
cd ..

echo -e "\n${GREEN}All services started!${NC}"
echo "========================================="
echo "Services running at:"
echo "  Hotel Service:       http://localhost:5001"
echo "  Room Service:        http://localhost:5002"
echo "  Guest Service:       http://localhost:5003"
echo "  Inventory Service:   http://localhost:5004"
echo "  Reservation Service: http://localhost:5005"
echo "  Payment Service:     http://localhost:5006"
echo "  Frontend UI:         http://localhost:3000"
echo "========================================="
echo "Use ./stop-services.sh to stop all services"