#!/bin/bash

echo "🛑 Stopping Hotel Booking System Demo..."

# Stop React Frontend (if running)
echo "🌐 Stopping React Frontend..."
if [ -f frontend.pid ]; then
    FRONTEND_PID=$(cat frontend.pid)
    kill $FRONTEND_PID 2>/dev/null || echo "Frontend process not found"
    rm frontend.pid
fi
pkill -f "npm start" 2>/dev/null || echo "Cleaning up any remaining npm processes"
pkill -f "react-scripts start" 2>/dev/null || echo "Cleaning up any remaining react-scripts processes"

# Stop all service containers
echo "🚀 Stopping microservices..."
services=("hotel-service" "room-service" "guest-service" "inventory-service" "reservation-service" "payment-service")

for service in "${services[@]}"; do
    echo "Stopping $service..."
    docker stop $service 2>/dev/null || echo "$service not running"
    docker rm $service 2>/dev/null || echo "$service not found"
done

# Stop databases
echo "🗄️ Stopping databases..."
docker stop postgres-db 2>/dev/null || echo "PostgreSQL not running"
docker rm postgres-db 2>/dev/null || echo "PostgreSQL not found"

docker stop redis-cache 2>/dev/null || echo "Redis not running"
docker rm redis-cache 2>/dev/null || echo "Redis not found"

# Remove network
echo "📡 Removing Docker network..."
docker network rm hotel-network 2>/dev/null || echo "Network not found"

echo ""
echo "✅ Demo Stopped Successfully!"
echo ""
echo "🧹 To clean up Docker images: docker rmi hotel-service room-service guest-service inventory-service reservation-service payment-service"