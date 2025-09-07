#!/bin/bash

# Comprehensive Demo Runner for Nearby Friends System
# This script sets up everything needed for the demo

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║            🎬 NEARBY FRIENDS COMPLETE DEMO SETUP 🎬           ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f "$url" >/dev/null 2>&1; then
            echo "✅ $name is ready!"
            return 0
        fi
        
        echo "   Attempt $attempt/$max_attempts - waiting for $name..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $name failed to start after $max_attempts attempts"
    return 1
}

echo "🔍 Step 1: Checking prerequisites..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi
echo "✅ Docker is running"

# Check if Python 3 is available
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi
echo "✅ Python 3 is available"

echo ""
echo "🛑 Step 2: Stopping any existing services..."
./shutdown.sh

echo ""
echo "🚀 Step 3: Starting all microservices..."
./startup.sh

# Wait for key services to be ready
echo ""
echo "🔄 Step 4: Verifying services are healthy..."

if ! wait_for_service "http://localhost:8900/health" "API Gateway"; then
    echo "❌ API Gateway failed to start. Check logs and try again."
    exit 1
fi

if ! wait_for_service "http://localhost:8901/health" "User Service"; then
    echo "❌ User Service failed to start. Check logs and try again."
    exit 1
fi

if ! wait_for_service "http://localhost:8904/health" "WebSocket Gateway"; then
    echo "❌ WebSocket Gateway failed to start. Check logs and try again."
    exit 1
fi

echo ""
echo "👥 Step 5: Setting up demo data..."
python3 setup_demo_data.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to setup demo data. Check the error messages above."
    exit 1
fi

echo ""
echo "🎬 Step 6: Demo UI is running as a direct Python process!"
echo "✅ UI Service integrated into startup/shutdown scripts"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║                  🎉 DEMO IS READY TO GO! 🎉                   ║"
echo "║                                                                ║"
echo "║  🌐 Open your browser and navigate to:                        ║"
echo "║     http://localhost:3000/demo_ui.html                         ║"
echo "║                                                                ║"
echo "║  📋 Demo Features Available:                                   ║"
echo "║     • Interactive map with real-time location updates          ║"
echo "║     • 10 demo users with realistic friendships                 ║"
echo "║     • Live WebSocket connections                               ║"
echo "║     • System metrics dashboard                                 ║"
echo "║     • Activity feed with real-time events                      ║"
echo "║     • Microservices health monitoring                          ║"
echo "║                                                                ║"
echo "║  🎬 Demo Scenarios:                                            ║"
echo "║     • Rush Hour: Simulates many users moving around           ║"
echo "║     • Friends Meetup: Users converging to a location          ║"
echo "║     • Moving Demo: Shows traveling simulation                  ║"
echo "║                                                                ║"
echo "║  🚀 How to Use:                                                ║"
echo "║     1. Select a user from the dropdown                        ║"
echo "║     2. Click 'Login' to authenticate                          ║"
echo "║     3. Click 'Share Location' to start real-time updates      ║"
echo "║     4. Try the demo scenarios on the bottom right             ║"
echo "║                                                                ║"
echo "║  🔧 Running Services:                                          ║"
echo "║     • API Gateway: http://localhost:8900                      ║"
echo "║     • User Service: http://localhost:8901                     ║"
echo "║     • Friend Service: http://localhost:8902                   ║"
echo "║     • Location Service: http://localhost:8903                 ║"
echo "║     • WebSocket Gateway: ws://localhost:8904/ws               ║"
echo "║     • Demo UI: http://localhost:3000 (Direct Python)          ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    echo "ℹ️  Note: UI Service runs as a Docker container - use ./shutdown.sh to stop all services"
    echo "✨ Cleanup complete"
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

echo "💡 Tips for your demo presentation:"
echo "   • Start with Alice Johnson - she has the most friends"
echo "   • Show the real-time map updates"
echo "   • Demonstrate the Rush Hour scenario for impressive visuals"
echo "   • Point out the microservices status panel"
echo "   • Show the activity feed for real-time system monitoring"
echo ""
echo "📱 The demo is now running. Press Ctrl+C to stop all services."
echo "🌐 Demo URL: http://localhost:3000/demo_ui.html"
echo ""

# Keep script running
wait