#!/bin/bash

# Clean Stop Script for Distributed Email System
# Stops containers and removes volumes (but keeps images for faster restart)

cd "$(dirname "$0")"

echo "🛑 Stopping containers and removing volumes..."
docker-compose down --volumes --remove-orphans

echo "✅ Clean stop complete!"
echo ""
echo "📋 What was removed:"
echo "  • All containers stopped"
echo "  • All volumes removed (database data, etc.)"
echo ""
echo "📋 What was preserved:"
echo "  • Docker images (faster next startup)"
echo "  • Networks"
echo ""
echo "💡 Quick restart: ./start.sh"
echo "🧹 Full cleanup: ./scripts/stop-demo.sh"