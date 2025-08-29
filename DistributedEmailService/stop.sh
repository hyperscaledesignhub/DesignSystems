#!/bin/bash

# Quick Stop Script for Distributed Email System
# Stops containers only (preserves data for quick restart)

cd "$(dirname "$0")"

echo "🛑 Stopping Distributed Email System containers..."
docker-compose stop

echo "✅ All containers stopped successfully!"
echo ""
echo "💡 Quick restart: ./start.sh"
echo "🧹 Full cleanup options: ./scripts/stop-demo.sh"