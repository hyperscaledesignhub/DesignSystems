#!/bin/bash

echo "📋 TRANSACTIONAL ROLLBACK DEMO - STEP 3: Show Logs & Analysis"
echo "=============================================================="

echo "🔍 OBJECT SERVICE LOGS - Looking for rollback behavior:"
echo "========================================================"
echo "Key patterns to look for:"
echo "  ✅ POST requests to storage - Initial storage success"
echo "  ❌ 'Metadata service unavailable' - Connection error detected"
echo "  🔄 DELETE requests to storage - Compensating transaction (rollback)"
echo ""

docker logs object-service 2>&1 | grep -E "(POST|PUT|DELETE|metadata|503|unavailable)" | tail -20

echo ""
echo "🔍 STORAGE SERVICE LOGS - Looking for create/delete patterns:"
echo "============================================================="
echo "Key patterns to look for:"
echo "  ✅ POST /data - Files being stored initially"
echo "  🔄 DELETE /data - Files being cleaned up (rollback)"
echo ""

docker logs storage-service 2>&1 | grep -E "(POST /data|DELETE /data)" | tail -20

echo ""
echo "🔍 METADATA SERVICE LOGS - Should show connection refused:"
echo "=========================================================="
echo "Note: Service is stopped, so these are the last entries before shutdown"
echo ""

docker logs metadata-service 2>&1 | tail -10

echo ""
echo "📊 CURRENT SYSTEM STATE ANALYSIS:"
echo "================================="

echo ""
echo "1️⃣ Services Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(metadata|object|storage)"

echo ""
echo "2️⃣ Files in Storage Service:"
STORAGE_FILES=$(docker exec storage-service find /data/storage -name "*.bin" -type f 2>/dev/null | wc -l)
echo "   Current file count: $STORAGE_FILES"
if [ "$STORAGE_FILES" -eq 0 ]; then
    echo "   ✅ SUCCESS: No files remain (successful rollback cleanup)"
else
    echo "   ⚠️  WARNING: $STORAGE_FILES files remain (check rollback logic)"
fi

echo ""
echo "3️⃣ SQLite Storage Index:"
docker exec storage-service sqlite3 /data/storage_index.db "SELECT COUNT(*) FROM storage_objects;" 2>/dev/null && echo "   Storage index entries found" || echo "   No storage index entries (expected after rollback)"

echo ""
echo "🔍 ROLLBACK VERIFICATION:"
echo "========================"
echo "Expected behavior during metadata service outage:"
echo ""
echo "✅ Phase 1 - Initial Upload:"
echo "   - Object Service receives PUT request"
echo "   - Storage Service creates file and returns 201"
echo "   - Object Service attempts to create metadata"
echo ""
echo "❌ Phase 2 - Metadata Failure:"
echo "   - Metadata Service is down (connection refused)"
echo "   - Object Service detects metadata creation failure"
echo ""
echo "🔄 Phase 3 - Compensating Transaction (Rollback):"
echo "   - Object Service calls DELETE on Storage Service"
echo "   - Storage Service removes the orphaned file"
echo "   - Object Service returns HTTP 500 to client"
echo ""
echo "🎯 Result: No orphaned data despite partial failure!"

echo ""
echo "📝 Next step: Run ./demo_rollback_4_restart_metadata.sh to restore normal operation"