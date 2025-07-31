#!/bin/bash

# Start Node Failure Demo Cluster
# Uses config-node-failure.yaml with faster anti-entropy for demo purposes

echo "🚀 Starting Node Failure Demo Cluster..."
echo "📝 Config: yaml/config-node-failure.yaml"
echo "⚡ Anti-entropy interval: 10 seconds (fast recovery)"
echo ""

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "python distributed/node.py" 2>/dev/null || true
sleep 2

# Clean data directories
echo "🗑️ Cleaning data directories..."
rm -rf data/db-node-* 2>/dev/null || true

# Start Node 1
echo "🔴 Starting Node 1 (localhost:9999)..."
CONFIG_FILE=yaml/config-node-failure.yaml SEED_NODE_ID=db-node-1 python distributed/node.py &
NODE1_PID=$!
sleep 3

# Start Node 2
echo "🟢 Starting Node 2 (localhost:10000)..."
CONFIG_FILE=yaml/config-node-failure.yaml SEED_NODE_ID=db-node-2 python distributed/node.py &
NODE2_PID=$!
sleep 3

# Start Node 3
echo "🔵 Starting Node 3 (localhost:10001)..."
CONFIG_FILE=yaml/config-node-failure.yaml SEED_NODE_ID=db-node-3 python distributed/node.py &
NODE3_PID=$!
sleep 3

echo ""
echo "✅ Node Failure Demo Cluster Started!"
echo ""
echo "📍 Node URLs:"
echo "   - Node 1: http://localhost:9999"
echo "   - Node 2: http://localhost:10000"  
echo "   - Node 3: http://localhost:10001"
echo ""
echo "🎯 Demo Features:"
echo "   - Fast anti-entropy recovery (10s)"
echo "   - Optimized for node failure scenarios"
echo "   - Quick data synchronization"
echo ""
echo "🚀 Start the demo with:"
echo "   cd demo/ui && python node_failure_demo.py"
echo "   Then open: http://localhost:8007"
echo ""
echo "🛑 To stop cluster: ./stop-cluster.sh"
echo ""
echo "Process IDs: Node1=$NODE1_PID Node2=$NODE2_PID Node3=$NODE3_PID"

# Keep script running
wait