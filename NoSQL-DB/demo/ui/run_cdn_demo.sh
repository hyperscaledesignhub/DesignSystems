#!/bin/bash
"""
CDN Distribution Demo Launch Script
"""

echo "🌐 CDN Distribution Demo - Distributed Database"
echo "=============================================="
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
pkill -f "7-cdn_demo.py" 2>/dev/null || true

echo "🚀 Starting CDN Distribution Demo..."
echo ""
echo "📍 Demo URL: http://localhost:8004"
echo "🎯 Features:"
echo "   - Content distribution and edge caching"
echo "   - Cache hit/miss tracking"
echo "   - Multi-region content delivery"
echo "   - Content invalidation across regions"
echo "   - Performance optimization simulation"
echo ""
echo "🌍 CDN Regions:"
echo "   - US-East    → Node localhost:9999"
echo "   - US-West    → Node localhost:10000"
echo "   - EU-West    → Node localhost:10001"
echo "   - Asia-Pacific → Fallback routing"
echo ""
echo "📦 Content Types:"
echo "   - Images (user avatars, product photos)"
echo "   - Videos (promotional content)"
echo "   - Documents (CSS, JS files)"
echo "   - Webpages (landing pages)"
echo "   - API Responses (cached data)"
echo ""
echo "🔄 Endpoints: Regular /kv/ (optimized for high-frequency cache operations)"
echo "⚡ Cache Performance: Faster responses for cache hits vs origin fetches"
echo ""
echo "💡 Use Case: Global content delivery network with distributed caching"
echo ""
echo "Press Ctrl+C to stop the demo"
echo "=============================================="

# Start the demo
cd "$(dirname "$0")"
python3 7-cdn_demo.py