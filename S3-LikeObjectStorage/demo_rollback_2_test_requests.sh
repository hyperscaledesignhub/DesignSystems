#!/bin/bash

echo "🧪 TRANSACTIONAL ROLLBACK DEMO - STEP 2: Test API Requests"
echo "=========================================================="

echo "📝 Creating test files for upload..."
echo "This is test file 1 for rollback demo" > /tmp/rollback_test1.txt
echo "This is test file 2 for rollback demo" > /tmp/rollback_test2.txt
echo "This is test file 3 for rollback demo" > /tmp/rollback_test3.txt

echo "✅ Test files created:"
ls -la /tmp/rollback_test*.txt

echo ""
echo "🔍 Current storage service files before test:"
docker exec storage-service ls -la /data/storage/ 2>/dev/null | wc -l

echo ""
echo "🚀 Attempting to upload objects (should trigger rollback)..."
echo "============================================================"

echo ""
echo "📤 Upload Test 1: rollback_test1.txt"
echo "Command: curl -X PUT -H 'X-User-ID: admin' --data-binary @/tmp/rollback_test1.txt http://localhost:7871/buckets/object-test-bucket/objects/rollback-test-1.txt"
curl -X PUT \
    -H "X-User-ID: admin" \
    -H "Content-Type: text/plain" \
    --data-binary @/tmp/rollback_test1.txt \
    http://localhost:7871/buckets/object-test-bucket/objects/rollback-test-1.txt \
    -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" 2>/dev/null

echo ""
echo "📤 Upload Test 2: rollback_test2.txt"
echo "Command: curl -X PUT -H 'X-User-ID: admin' --data-binary @/tmp/rollback_test2.txt http://localhost:7871/buckets/object-test-bucket/objects/rollback-test-2.txt"
curl -X PUT \
    -H "X-User-ID: admin" \
    -H "Content-Type: text/plain" \
    --data-binary @/tmp/rollback_test2.txt \
    http://localhost:7871/buckets/object-test-bucket/objects/rollback-test-2.txt \
    -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" 2>/dev/null

echo ""
echo "📤 Upload Test 3: rollback_test3.txt"  
echo "Command: curl -X PUT -H 'X-User-ID: admin' --data-binary @/tmp/rollback_test3.txt http://localhost:7871/buckets/object-test-bucket/objects/rollback-test-3.txt"
curl -X PUT \
    -H "X-User-ID: admin" \
    -H "Content-Type: text/plain" \
    --data-binary @/tmp/rollback_test3.txt \
    http://localhost:7871/buckets/object-test-bucket/objects/rollback-test-3.txt \
    -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" 2>/dev/null

echo ""
echo "🔍 Checking storage service files after failed uploads:"
echo "Expected: Files should be created then deleted (rollback)"
docker exec storage-service find /data/storage -name "*.bin" -type f 2>/dev/null | wc -l

echo ""
echo "📊 Summary of what should have happened:"
echo "   ✅ 1. Object Service received upload requests"
echo "   ✅ 2. Storage Service created files successfully"
echo "   ❌ 3. Metadata Service failed (service down)"
echo "   🔄 4. Object Service triggered rollback - deleted files from Storage"
echo "   ⚠️  5. HTTP 500 errors returned to client"

echo ""
echo "📝 Next step: Run ./demo_rollback_3_show_logs.sh to see the rollback in action"