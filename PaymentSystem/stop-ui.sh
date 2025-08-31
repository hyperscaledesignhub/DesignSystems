#!/bin/bash

# Payment System Demo - UI Shutdown Script
# This script stops the React UI development server

echo "🛑 Stopping Payment System UI..."
echo "================================"

# Find and kill the process running on port 3001
echo "🔍 Looking for UI process on port 3001..."

# For macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    PID=$(lsof -ti:3001)
    if [ ! -z "$PID" ]; then
        echo "📍 Found UI process with PID: $PID"
        echo "🔽 Stopping UI server..."
        kill -9 $PID
        echo "✅ UI server stopped!"
    else
        echo "ℹ️  No UI server running on port 3001"
    fi
# For Linux
else
    PID=$(netstat -tlnp 2>/dev/null | grep :3001 | awk '{print $7}' | cut -d'/' -f1)
    if [ ! -z "$PID" ]; then
        echo "📍 Found UI process with PID: $PID"
        echo "🔽 Stopping UI server..."
        kill -9 $PID
        echo "✅ UI server stopped!"
    else
        # Alternative method using fuser
        if command -v fuser &> /dev/null; then
            fuser -k 3001/tcp 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "✅ UI server stopped!"
            else
                echo "ℹ️  No UI server running on port 3001"
            fi
        else
            echo "ℹ️  No UI server running on port 3001"
        fi
    fi
fi

echo ""
echo "💡 To start UI again, run: ./start-ui.sh"
echo "💡 To stop all services, run: ./stop-services.sh"