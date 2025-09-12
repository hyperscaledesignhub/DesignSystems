#!/bin/bash

echo "🛑 Stopping Google Maps System - All Services"
echo "============================================="

# Stop Docker containers
echo "🐳 Stopping Docker containers..."
docker stop redis location-service navigation-service places-service traffic-service 2>/dev/null || true
docker rm redis location-service navigation-service places-service traffic-service 2>/dev/null || true

# Kill any standalone Python processes
echo "🔪 Killing standalone Python processes..."
pkill -f "python.*service" 2>/dev/null || true
pkill -f "start_ui.py" 2>/dev/null || true
pkill -f "maps_ui.py" 2>/dev/null || true

# Kill processes on specific ports
echo "🔌 Freeing up ports..."
lsof -ti:3002,6379,8081,8083,8084,8086 2>/dev/null | xargs kill 2>/dev/null || true

echo ""
echo "✅ All services stopped!"

# Clean up network
docker network rm maps-network 2>/dev/null || echo "Network already cleaned"

echo "🧹 Cleanup complete!"
