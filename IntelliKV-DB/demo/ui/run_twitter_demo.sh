#!/bin/bash
"""
Twitter Demo Launch Script
"""

echo "🐦 Twitter Demo - Distributed Database"
echo "======================================="
echo ""

# Check if cluster is running
echo "🔍 Checking cluster health..."
if ! curl -s http://localhost:9999/health > /dev/null 2>&1; then
    echo "❌ Cluster not running. Please start the cluster first:"
    echo "   cd /Users/vijayabhaskarv/hyper-scale/kvdb/DesignSystems/NoSQL-DB"
    echo "   ./scripts/start_local_cluster.sh"
    exit 1
fi

echo "✅ Cluster is running"
echo ""

# Set cluster nodes environment
export CLUSTER_NODES="localhost:9999,localhost:10000,localhost:10001"

# Kill any existing demo instances
echo "🧹 Cleaning up existing instances..."
pkill -f "5-twitter_demo.py" 2>/dev/null || true

echo "🚀 Starting Twitter Demo..."
echo ""
echo "📍 Demo URL: http://localhost:8001"
echo "🎯 Features:"
echo "   - Real-time engagement tracking"
echo "   - Persistent counter increments"
echo "   - Distributed consensus with quorum"
echo "   - Live cluster health monitoring"
echo ""
echo "📊 Demo Tweet ID: tweet_persistent_demo"
echo "🔄 Endpoints: Regular /kv/ (optimized for performance)"
echo ""
echo "Press Ctrl+C to stop the demo"
echo "======================================"

# Start the demo
cd "$(dirname "$0")"
python3 5-twitter_demo.py