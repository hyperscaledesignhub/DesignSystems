#!/bin/bash
"""
Inventory Management Demo Launch Script
"""

echo "📦 Inventory Management Demo - Distributed Database"
echo "================================================="
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
pkill -f "8-inventory_demo.py" 2>/dev/null || true

echo "🚀 Starting Inventory Management Demo..."
echo ""
echo "📍 Demo URL: http://localhost:8003"
echo "🎯 Features:"
echo "   - Multi-warehouse inventory tracking"
echo "   - Real-time stock updates (orders/shipments)"
echo "   - Load-balanced operations across cluster"
echo "   - Automatic stock level management"
echo ""
echo "🏪 Warehouses: New York, Los Angeles, Chicago"
echo "📱 Products:"
echo "   - iPhone 14 Pro"
echo "   - MacBook Pro" 
echo "   - AirPods Pro"
echo "   - iPad Air"
echo "   - Apple Watch"
echo ""
echo "🔄 Endpoints: Regular /kv/ (optimized for high-volume inventory operations)"
echo "📊 Operations: Orders (reduce stock), Shipments (increase stock)"
echo ""
echo "💡 Use Case: E-commerce inventory management across multiple distribution centers"
echo ""
echo "Press Ctrl+C to stop the demo"
echo "================================================="

# Start the demo
cd "$(dirname "$0")"
python3 8-inventory_demo.py