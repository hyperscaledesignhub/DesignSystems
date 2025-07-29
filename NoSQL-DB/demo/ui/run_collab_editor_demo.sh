#!/bin/bash
"""
Collaborative Editor Demo Launch Script
"""

echo "📝 Collaborative Editor Demo - Distributed Database"
echo "=================================================="
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
pkill -f "6-collab_editor_demo.py" 2>/dev/null || true

echo "🚀 Starting Collaborative Editor Demo..."
echo ""
echo "📍 Demo URL: http://localhost:8002"
echo "🎯 Features:"
echo "   - Real-time collaborative document editing"
echo "   - Causal consistency for proper edit ordering"
echo "   - Vector clocks for conflict resolution"
echo "   - Multi-author support with live updates"
echo "   - Document versioning and history"
echo ""
echo "👥 Demo Authors: Alice, Bob, Charlie, Diana, Eve, Frank, Grace"
echo "🔄 Endpoints: Causal /causal/kv/ (ensures edit order preservation)"
echo "📊 Sample Documents: Auto-generated for demonstration"
echo ""
echo "🔧 Why Causal Consistency?"
echo "   - Edit order matters in collaborative editing"
echo "   - Alice writes 'Hello' → Bob adds 'World' = 'Hello World'"
echo "   - Vector clocks ensure proper happens-before relationships"
echo ""
echo "Press Ctrl+C to stop the demo"
echo "=================================================="

# Start the demo
cd "$(dirname "$0")"
python3 6-collab_editor_demo.py