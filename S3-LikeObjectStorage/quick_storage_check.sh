#!/bin/bash

echo "⚡ QUICK STORAGE CHECK - S3 Object Storage"
echo "=========================================="

# Quick service status
echo "🔧 Services Running:"
docker ps --format "{{.Names}}: {{.Status}}" | grep -E "(postgres|identity|bucket|object|storage|metadata|gateway)" | sed 's/^/   /'

echo ""
echo "📊 Quick Stats:"

# Count buckets
BUCKET_COUNT=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COUNT(*) FROM buckets;" 2>/dev/null | tr -d ' ' || echo "0")
echo "   Buckets: $BUCKET_COUNT"

# Count objects in metadata
METADATA_OBJECTS=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COUNT(*) FROM object_metadata;" 2>/dev/null | tr -d ' ' || echo "0")
echo "   Objects (metadata): $METADATA_OBJECTS"

# Count physical files (stored as UUID files, not .bin)
PHYSICAL_FILES=$(docker exec storage-service find /data/storage -type f 2>/dev/null | wc -l)
echo "   Physical files: $PHYSICAL_FILES"

# Calculate total size
TOTAL_SIZE=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COALESCE(SUM(size_bytes), 0) FROM object_metadata;" 2>/dev/null | tr -d ' ' || echo "0")
echo "   Total storage: $(numfmt --to=iec $TOTAL_SIZE 2>/dev/null || echo "$TOTAL_SIZE bytes")"

# Count users
USER_COUNT=$(docker exec identity-service sqlite3 /data/identity.db "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
echo "   Users: $USER_COUNT"

echo ""
echo "🩺 Health Check:"
if [ "$METADATA_OBJECTS" -eq "$PHYSICAL_FILES" ]; then
    echo "   ✅ Storage consistency: GOOD"
else
    echo "   ⚠️  Storage consistency: MISMATCH ($METADATA_OBJECTS metadata vs $PHYSICAL_FILES files)"
fi

if [ "$BUCKET_COUNT" -gt 0 ] && [ "$METADATA_OBJECTS" -gt 0 ]; then
    echo "   ✅ System status: ACTIVE (has data)"
else
    echo "   📭 System status: EMPTY (no data)"
fi

echo ""
echo "💡 Run './inspect_storage.sh' for detailed analysis"