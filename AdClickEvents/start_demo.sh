#!/bin/bash

# AdClick Demo System Startup Script

echo "🎯 AdClick Demo System"
echo "======================"
echo ""

# Check if virtual environment exists
if [ ! -d "demo_env" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv demo_env
    source demo_env/bin/activate
    pip install flask flask-cors kafka-python influxdb-client requests
else
    echo "📦 Using existing virtual environment..."
    source demo_env/bin/activate
fi

echo ""
echo "🚀 Starting AdClick Demo System..."
echo ""
echo "📊 Demo Dashboard: http://localhost:8900"
echo "🔧 Health Check: http://localhost:8900/health"
echo "📋 API Documentation: http://localhost:8900/api/*"
echo ""
echo "🎬 Customer Demo Features:"
echo "  • Real-time ad click processing"
echo "  • 4 business scenario simulations"
echo "  • Live fraud detection alerts"  
echo "  • Performance monitoring dashboard"
echo "  • Interactive controls for demonstrations"
echo ""
echo "🛑 Press Ctrl+C to stop the demo"
echo ""

# Start the demo system
python simple_demo_api.py