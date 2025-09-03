#!/bin/bash

echo "=========================================="
echo "   PROXIMITY SERVICE DEMO LAUNCHER"
echo "=========================================="

# Navigate to parent directory
cd /Users/vijayabhaskarv/python-projects/venv/sysdesign/10-ProximityService

# Start all services
echo "📦 Starting all services..."
docker-compose up -d

# Wait for services to initialize
echo "⏳ Waiting for services to initialize (15 seconds)..."
sleep 15

# Generate demo data
echo "🔧 Generating demo data..."
cd demo
python3 generate_data.py

echo ""
echo "=========================================="
echo "✅ DEMO READY!"
echo "=========================================="
echo ""
echo "📱 Open the demo UI:"
echo "   file://$PWD/index.html"
echo ""
echo "🎯 Service Endpoints:"
echo "   • API Gateway:      http://localhost:7891"
echo "   • Business Service: http://localhost:9823"
echo "   • Location Service: http://localhost:8921"
echo ""
echo "💾 Database Endpoints:"
echo "   • PostgreSQL Primary:  localhost:5832"
echo "   • PostgreSQL Replica1: localhost:5833"
echo "   • PostgreSQL Replica2: localhost:5834"
echo ""
echo "🔴 Redis Endpoints:"
echo "   • Redis Master:    localhost:6739"
echo "   • Redis Replica1:  localhost:6740"
echo "   • Redis Replica2:  localhost:6741"
echo ""
echo "📊 Monitoring:"
echo "   • Health Check:    http://localhost:7891/health"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo ""
echo "=========================================="