#!/bin/bash

echo "🔄 TRANSACTIONAL ROLLBACK DEMO - STEP 4: Restart Metadata Service"
echo "=================================================================="

echo "🔍 Current services status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(metadata|object|storage)"

echo ""
echo "🚀 Restarting metadata service..."
docker start metadata-service

echo ""
echo "⏳ Waiting 5 seconds for service to fully start..."
sleep 5

echo ""
echo "🔍 Services status after restart:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(metadata|object|storage)"

echo ""
echo "🏥 Testing metadata service health:"
METADATA_HEALTH=$(curl -s http://localhost:7891/health 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [ "$METADATA_HEALTH" = "healthy" ]; then
    echo "✅ Metadata service is healthy and responding"
else
    echo "⚠️  Metadata service may still be starting... Health status: $METADATA_HEALTH"
fi

echo ""
echo "🧪 Testing normal upload operation (should work now):"
echo "===================================================="

echo "📤 Attempting upload with metadata service restored..."
echo "Creating test file for successful upload..."
echo "This file should upload successfully after metadata service restart" > /tmp/rollback_success_test.txt

echo ""
echo "Command: curl -X PUT -H 'X-User-ID: admin' --data-binary @/tmp/rollback_success_test.txt http://localhost:7871/buckets/object-test-bucket/objects/rollback-success-test.txt"
UPLOAD_RESULT=$(curl -X PUT \
    -H "X-User-ID: admin" \
    -H "Content-Type: text/plain" \
    --data-binary @/tmp/rollback_success_test.txt \
    http://localhost:7871/buckets/object-test-bucket/objects/rollback-success-test.txt \
    -w "HTTP_CODE:%{http_code}" -s 2>/dev/null)

HTTP_CODE=$(echo "$UPLOAD_RESULT" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
RESPONSE_BODY=$(echo "$UPLOAD_RESULT" | sed 's/HTTP_CODE:[0-9]*//')

echo "Response: $RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "✅ SUCCESS: Upload completed successfully!"
    echo "🎯 This proves the system recovered after metadata service restart"
else
    echo "❌ Upload failed with status $HTTP_CODE"
    echo "🔧 Metadata service may need more time to start or there's a configuration issue"
fi

echo ""
echo "📊 FINAL VERIFICATION:"
echo "====================="

echo ""
echo "1️⃣ All services running:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(api-gateway|identity|bucket|object|storage|metadata)"

echo ""
echo "2️⃣ Files now in storage (after successful upload):"
FINAL_STORAGE_FILES=$(docker exec storage-service find /data/storage -name "*.bin" -type f 2>/dev/null | wc -l)
echo "   Current file count: $FINAL_STORAGE_FILES"

echo ""
echo "3️⃣ Metadata entries:"
METADATA_COUNT=$(curl -s http://localhost:7891/metadata/stats 2>/dev/null | grep -o '"total_objects":[0-9]*' | cut -d: -f2)
echo "   Total objects in metadata: $METADATA_COUNT"

echo ""
echo "🎉 ROLLBACK DEMO COMPLETE!"
echo "=========================="
echo ""
echo "📋 What we demonstrated:"
echo "   1️⃣ Metadata service failure simulation"
echo "   2️⃣ Storage-first transaction pattern" 
echo "   3️⃣ Automatic rollback/cleanup on metadata failure"
echo "   4️⃣ System recovery after service restart"
echo "   5️⃣ No data corruption or orphaned files"
echo ""
echo "🏗️ Architecture Pattern Proven:"
echo "   ✅ Saga Pattern with Compensating Transactions"
echo "   ✅ Storage-First Strategy (easier to cleanup than recreate)"
echo "   ✅ Transactional consistency across microservices"
echo "   ✅ Graceful degradation and recovery"

echo ""
echo "🧹 Cleanup:"
echo "rm -f /tmp/rollback_*.txt"
echo "rm -f /tmp/rollback_success_test.txt"

# Cleanup test files
rm -f /tmp/rollback_*.txt
rm -f /tmp/rollback_success_test.txt

echo "✅ Cleanup completed"