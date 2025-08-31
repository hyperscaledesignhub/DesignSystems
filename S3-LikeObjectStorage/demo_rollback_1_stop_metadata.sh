#!/bin/bash

echo "🛑 TRANSACTIONAL ROLLBACK DEMO - STEP 1: Stop Metadata Service"
echo "=============================================================="

echo "📊 Current services status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(metadata|object|storage)"

echo ""
echo "🛑 Stopping metadata service to simulate failure..."
docker stop metadata-service

echo ""
echo "📊 Services status after stopping metadata:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(metadata|object|storage)"

echo ""
echo "🔍 Checking metadata service is stopped:"
if docker ps | grep -q "metadata-service"; then
    echo "❌ Metadata service is still running"
else
    echo "✅ Metadata service is stopped - ready for rollback demo"
fi

echo ""
echo "📝 Next steps:"
echo "   1. Run: ./demo_rollback_2_test_requests.sh"
echo "   2. Run: ./demo_rollback_3_show_logs.sh"  
echo "   3. Run: ./demo_rollback_4_restart_metadata.sh"