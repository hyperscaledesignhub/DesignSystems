#!/bin/bash

# Payment System Demo - UI Startup Script
# This script starts the React UI development server

echo "🎨 Starting Payment System UI..."
echo "================================"

# Check if we're in the right directory
if [ ! -f "ui/package.json" ]; then
    echo "❌ Error: UI directory not found!"
    echo "Please run this script from the demo directory"
    exit 1
fi

# Navigate to UI directory
cd ui

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing UI dependencies..."
    npm install
fi

# Start the React development server on port 3001
echo "🚀 Starting React development server on port 3001..."
echo "📱 UI will be available at: http://localhost:3001"
echo ""
echo "🔗 Service endpoints the UI will connect to:"
echo "• Wallet Service:         http://localhost:8740"
echo "• Fraud Detection:        http://localhost:8742"
echo "• Reconciliation:         http://localhost:8741"
echo "• Notification Service:   http://localhost:8743"
echo ""
echo "⚠️  Make sure microservices are running first!"
echo "   Run: ./start-services.sh"
echo ""

# Start the UI
PORT=3001 npm start