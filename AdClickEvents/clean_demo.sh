#!/bin/bash
set -e

echo "🔄 Starting Clean AdClick Demo..."

# Function to clear InfluxDB data
clear_influx_data() {
    echo "🧹 Clearing InfluxDB data..."
    docker exec demo-influxdb-1 influx delete --bucket adclick-demo --start 1970-01-01T00:00:00Z --stop 2030-01-01T00:00:00Z --org demo-org --token demo-token --predicate '_measurement="adclick_events"' 2>/dev/null || true
}

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "🚀 Starting services..."
    docker-compose up -d
    echo "⏳ Waiting for services to initialize..."
    sleep 30
fi

# Clear any existing data
clear_influx_data

echo "✅ Clean AdClick Demo ready!"
echo "📊 Dashboard: http://localhost:3000" 
echo "🔧 API Health: http://localhost:8900/health"
echo ""
echo "🎯 Instructions:"
echo "1. Choose a scenario in the dropdown"
echo "2. Start simulation"
echo "3. See ONLY that scenario's ads"
echo "4. To switch scenarios cleanly: ./clean_demo.sh again"
echo ""
echo "🔥 Perfect demo with no mixed categories!"