#!/bin/bash

echo "🧹 Cleaning up Docker resources..."

# Stop all running containers
echo "Stopping all containers..."
docker stop $(docker ps -aq) 2>/dev/null || true

# Remove all containers
echo "Removing all containers..."
docker rm $(docker ps -aq) 2>/dev/null || true

# Remove all images related to the gaming board
echo "Removing gaming board images..."
docker rmi $(docker images | grep -E "gaming-board|leaderboard|game-service|score-service|user-service|api-gateway|websocket|tournament|analytics|demo" | awk '{print $3}') 2>/dev/null || true

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove unused networks
echo "Removing unused networks..."
docker network prune -f

# Clean build cache
echo "Cleaning build cache..."
docker builder prune -f

echo "✅ Docker cleanup completed!"