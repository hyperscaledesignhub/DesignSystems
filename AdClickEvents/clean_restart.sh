#!/bin/bash
set -e

echo "🔄 Restarting AdClick Demo with clean data..."

# Stop all services
echo "⏹️  Stopping services..."
docker-compose down

# Remove InfluxDB volume to ensure clean startup
echo "🗑️  Removing old data volume..."
docker volume rm demo_influxdb_data 2>/dev/null || true

# Start all services
echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to initialize..."
sleep 30

echo "✅ AdClick Demo ready!"
echo "📊 Dashboard: http://localhost:3000"
echo "🔧 API Health: http://localhost:8900/health"
echo ""
echo "🎯 Ready for demo with clean data!"