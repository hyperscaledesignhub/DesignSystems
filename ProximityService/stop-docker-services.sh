#!/bin/bash

# ProximityService - Independent Docker Services Stop Script
# This script stops all independent Docker containers

echo "🛑 Stopping ProximityService independent Docker containers..."

# Define container names
CONTAINERS=(
    "api-gateway"
    "business-service-standalone" 
    "location-service"
    "cache-warmer"
    "redis-sentinel3"
    "redis-sentinel2"
    "redis-sentinel1"
    "redis-replica2"
    "redis-replica1"
    "redis-master"
    "postgres-replica2"
    "postgres-replica1"
    "postgres-primary"
)

# Stop containers in reverse dependency order
for container in "${CONTAINERS[@]}"; do
    echo "🔄 Stopping $container..."
    docker stop $container 2>/dev/null || echo "   $container was not running"
    docker rm $container 2>/dev/null || echo "   $container already removed"
done

# Stop UI if running
echo "🌐 Stopping UI server..."
if [ -f "demo/.ui.pid" ]; then
    UI_PID=$(cat demo/.ui.pid)
    if ps -p $UI_PID > /dev/null 2>&1; then
        kill $UI_PID
        echo "✅ UI server stopped (PID: $UI_PID)"
    else
        echo "   UI server was not running"
    fi
    rm -f demo/.ui.pid
else
    echo "   UI PID file not found"
fi

# Remove network
echo "📡 Removing Docker network..."
docker network rm proximity-network 2>/dev/null || echo "   Network proximity-network already removed or doesn't exist"

# Optional: Remove volumes (uncomment if you want to clear all data)
# echo "💾 Removing Docker volumes..."
# docker volume rm postgres_primary_data postgres_replica1_data postgres_replica2_data 2>/dev/null || true
# docker volume rm redis_master_data redis_replica1_data redis_replica2_data 2>/dev/null || true

echo ""
echo "✅ All ProximityService containers stopped!"
echo ""
echo "💡 Note: Data volumes are preserved. To remove all data, uncomment the volume removal section in this script."
echo "📊 To see remaining containers: docker ps -a"
echo "💾 To see remaining volumes: docker volume ls"