#!/bin/bash

# Shutdown script for Nearby Friends demo services
# This script stops and removes all demo Docker containers

echo "🛑 Shutting down Nearby Friends Demo Services..."
echo "============================================"

# Stop and remove containers
echo "📦 Stopping UI Service..."
if [ -f ui_service.pid ]; then
    UI_PID=$(cat ui_service.pid)
    if kill -0 $UI_PID 2>/dev/null; then
        kill $UI_PID 2>/dev/null && echo "✅ UI Service stopped" || echo "⚠️  Failed to stop UI Service"
    else
        echo "⚠️  UI Service was not running"
    fi
    rm -f ui_service.pid
else
    # Fallback: kill any serve_demo.py processes
    pkill -f "python3.*serve_demo.py" 2>/dev/null && echo "✅ UI Service stopped" || echo "⚠️  UI Service was not running"
fi

echo "📦 Stopping API Gateway..."
docker stop api-gateway 2>/dev/null && docker rm api-gateway 2>/dev/null && echo "✅ API Gateway stopped" || echo "⚠️  API Gateway was not running"

echo "📦 Stopping User Service..."
docker stop user-service 2>/dev/null && docker rm user-service 2>/dev/null && echo "✅ User Service stopped" || echo "⚠️  User Service was not running"

echo "📦 Stopping Friend Service..."
docker stop friend-service 2>/dev/null && docker rm friend-service 2>/dev/null && echo "✅ Friend Service stopped" || echo "⚠️  Friend Service was not running"

echo "📦 Stopping Location Service..."
docker stop location-service 2>/dev/null && docker rm location-service 2>/dev/null && echo "✅ Location Service stopped" || echo "⚠️  Location Service was not running"

echo "📦 Stopping WebSocket Gateway..."
docker stop websocket-gateway 2>/dev/null && docker rm websocket-gateway 2>/dev/null && echo "✅ WebSocket Gateway stopped" || echo "⚠️  WebSocket Gateway was not running"

echo "📦 Stopping Redis..."
docker stop redis-nearbyf 2>/dev/null && docker rm redis-nearbyf 2>/dev/null && echo "✅ Redis stopped" || echo "⚠️  Redis was not running"

echo "📦 Stopping PostgreSQL..."
docker stop postgres-nearbyf 2>/dev/null && docker rm postgres-nearbyf 2>/dev/null && echo "✅ PostgreSQL stopped" || echo "⚠️  PostgreSQL was not running"

# Remove network
echo "📦 Removing Docker network..."
docker network rm nearby-friends-network 2>/dev/null && echo "✅ Network removed" || echo "⚠️  Network was not found"

echo ""
echo "============================================"
echo "✨ All services have been shut down!"
echo "============================================"