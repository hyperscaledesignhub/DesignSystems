#!/bin/bash

# AdClick Demo Setup Script
set -e

echo "🚀 Setting up AdClick Demo System..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data/influxdb
mkdir -p data/kafka

# Set permissions
chmod 755 logs
chmod 755 data/influxdb
chmod 755 data/kafka

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check InfluxDB
if curl -f http://localhost:8086/health > /dev/null 2>&1; then
    echo "✅ InfluxDB is healthy"
else
    echo "⚠️  InfluxDB may not be ready yet"
fi

# Check Demo API
if curl -f http://localhost:8900/health > /dev/null 2>&1; then
    echo "✅ Demo API is healthy"
else
    echo "⚠️  Demo API may not be ready yet"
fi

# Check Demo UI
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Demo UI is healthy"
else
    echo "⚠️  Demo UI may not be ready yet"
fi

echo ""
echo "🎉 AdClick Demo Setup Complete!"
echo ""
echo "📊 Access the demo dashboard at: http://localhost:3000"
echo "🔧 API endpoints available at: http://localhost:8900"
echo "📈 Original query service at: http://localhost:8908"
echo ""
echo "🎯 Demo Features:"
echo "  • Real-time dashboard with live metrics"
echo "  • Multiple business scenario simulations"
echo "  • Campaign performance comparison"
echo "  • Fraud detection and alerting"
echo "  • System health monitoring"
echo "  • Interactive demo controls"
echo ""
echo "🎬 To start a demo:"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Go to 'Demo Controls' to select a scenario"
echo "  3. Click 'Start Simulation' to begin"
echo "  4. Navigate through different tabs to explore features"
echo ""
echo "📝 Logs can be viewed with: docker-compose logs -f [service-name]"
echo "🛑 To stop the demo: docker-compose down"
echo ""