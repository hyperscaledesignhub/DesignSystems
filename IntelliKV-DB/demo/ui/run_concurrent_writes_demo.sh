#!/bin/bash
"""
Concurrent Writes Demo Launch Script
"""

echo "🔥 Concurrent Writes & Quorum Consensus Demo - Distributed Database"
echo "=================================================================="
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
pkill -f "1-concurrent_writes_demo.py" 2>/dev/null || true

echo "🚀 Starting Concurrent Writes Demo..."
echo ""
echo "📍 Demo URL: http://localhost:8005"
echo "🎯 Features:"
echo "   - Quorum-based reads and writes (2/3 nodes)"
echo "   - Concurrent write operations simulation"
echo "   - Real-time data consistency visualization"
echo "   - Multiple demo scenarios:"
echo "     • Banking Account Balance"
echo "     • E-commerce Inventory Management"
echo "     • Social Media Counters"
echo "   - Operations logging and quorum monitoring"
echo ""
echo "🔧 Quorum Configuration:"
echo "   - Cluster Size: 3 nodes"
echo "   - Read Quorum: 2 nodes (majority)"
echo "   - Write Quorum: 2 nodes (majority)"
echo "   - Replication Factor: 3 (full replication)"
echo ""
echo "💡 Demo Scenarios:"
echo "   🏦 Banking: Concurrent deposits/withdrawals to account balance"
echo "   🛒 E-commerce: Concurrent stock updates (purchases/restocking)"
echo "   📱 Social Media: Concurrent like/unlike operations on posts"
echo ""
echo "🎮 How to Use:"
echo "   1. Initialize a scenario (Banking, E-commerce, or Social Media)"
echo "   2. Perform manual operations or run concurrent simulations"
echo "   3. Watch quorum consensus in action"
echo "   4. Monitor data consistency across all nodes"
echo ""
echo "⚙️ Consistency Guarantees:"
echo "   - Strong consistency through quorum consensus"
echo "   - Tolerates 1 node failure (availability)"
echo "   - All successful writes are immediately consistent"
echo "   - Failed writes do not affect data integrity"
echo ""
echo "🔄 Endpoints: Regular /kv/ (with quorum-based operations)"
echo "📊 Monitoring: Real-time quorum status and consistency checks"
echo ""
echo "💡 Use Case: Demonstrates how quorum consensus ensures data consistency"
echo "              under high-concurrency scenarios like banking transactions,"
echo "              inventory management, and social media interactions"
echo ""
echo "Press Ctrl+C to stop the demo"
echo "=================================================================="

# Start the demo
cd "$(dirname "$0")"
python3 1-concurrent_writes_demo.py