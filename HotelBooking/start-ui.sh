#!/bin/bash

echo "🌐 Starting Hotel Booking System Frontend..."

# Check if services are running
if ! curl -s http://localhost:8001/health >/dev/null; then
    echo "❌ Backend services not running. Please start them first:"
    echo "   ./start-demo.sh"
    exit 1
fi

echo "✅ Backend services detected"
echo "🚀 Starting React Frontend..."

cd frontend
npm start