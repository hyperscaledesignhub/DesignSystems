#!/bin/bash

echo "🛑 Stopping All Microservices"
echo "=============================="

# Reset crawler statistics first (before stopping services)
echo "📊 Resetting crawler statistics..."
RESET_RESPONSE=$(curl -s -X POST http://localhost:5010/stats/reset 2>/dev/null)
if [ $? -eq 0 ] && echo "$RESET_RESPONSE" | grep -q '"success": true'; then
    echo "✅ Statistics reset successfully"
else
    echo "⚠️  Could not reset statistics (Gateway may not be running)"
fi

# Stop the UI service first (running on port 8090)
echo "🖥️  Stopping UI Dashboard..."
UI_PID=$(lsof -ti :8090 2>/dev/null)
if [ ! -z "$UI_PID" ]; then
    echo "Stopping UI service (PID: $UI_PID) on port 8090..."
    kill $UI_PID 2>/dev/null
    sleep 2
    # Force kill if still running
    if kill -0 $UI_PID 2>/dev/null; then
        echo "Force stopping UI service..."
        kill -9 $UI_PID 2>/dev/null
    fi
    echo "UI service stopped"
else
    echo "UI service is not running on port 8090"
fi

# Stop Docker containers
containers=("crawler-gateway" "crawler-deduplication" "crawler-parser" "crawler-downloader" "crawler-frontier" "crawler-extractor" "crawler-storage" "crawler-redis")

for container in "${containers[@]}"; do
    if docker ps -q -f name=$container | grep -q .; then
        echo "Stopping $container..."
        docker stop $container
        docker rm $container
    else
        echo "$container is not running"
    fi
done

echo ""
echo "🧹 Cleaning up network and volumes..."
docker network rm crawler-network 2>/dev/null || echo "Network already removed"
docker volume rm crawler-redis-data 2>/dev/null || echo "Volume already removed or in use"
docker volume rm crawler-storage-data 2>/dev/null || echo "Storage volume already removed or in use"

echo ""
echo "✅ All services stopped and cleaned up"