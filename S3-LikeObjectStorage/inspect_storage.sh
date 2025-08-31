#!/bin/bash

echo "🔍 S3-LIKE OBJECT STORAGE - PHYSICAL STORAGE INSPECTION"
echo "======================================================="
echo "This script inspects all physical storage layers to show what's actually stored"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📁 $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Function to print subsection headers
print_subsection() {
    echo ""
    echo "🔸 $1"
    echo "────────────────────────────────────────────────────────────"
}

# Check if services are running
print_section "SERVICE STATUS"
echo "Checking which services are currently running..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(postgres|identity|bucket|object|storage|metadata|gateway)"

# 1. POSTGRESQL DATABASE INSPECTION
print_section "1. POSTGRESQL DATABASE (Bucket & Object Metadata)"

print_subsection "1.1 Database Connection & Tables"
echo "Available databases:"
docker exec postgres-db psql -U s3user -d s3storage -c "\l" 2>/dev/null || echo "❌ Cannot connect to PostgreSQL"

echo ""
echo "Tables in s3storage database:"
docker exec postgres-db psql -U s3user -d s3storage -c "\dt" 2>/dev/null || echo "❌ Cannot query tables"

print_subsection "1.2 Bucket Data (PostgreSQL)"
echo "All buckets stored:"
docker exec postgres-db psql -U s3user -d s3storage -c "
SELECT 
    bucket_id,
    bucket_name,
    owner_id,
    created_at
FROM buckets 
ORDER BY created_at DESC;" 2>/dev/null || echo "❌ Cannot query buckets table"

print_subsection "1.3 Object Metadata (PostgreSQL)" 
echo "All object metadata stored:"
docker exec postgres-db psql -U s3user -d s3storage -c "
SELECT 
    object_id,
    bucket_name,
    object_name,
    content_type,
    size_bytes,
    etag,
    created_at
FROM object_metadata 
ORDER BY created_at DESC
LIMIT 20;" 2>/dev/null || echo "❌ Cannot query object_metadata table"

echo ""
echo "Object count by bucket:"
docker exec postgres-db psql -U s3user -d s3storage -c "
SELECT 
    bucket_name,
    COUNT(*) as object_count,
    SUM(size_bytes) as total_size_bytes,
    MAX(created_at) as latest_upload
FROM object_metadata 
GROUP BY bucket_name 
ORDER BY object_count DESC;" 2>/dev/null || echo "❌ Cannot query aggregated object stats"

# 2. STORAGE SERVICE FILE SYSTEM
print_section "2. STORAGE SERVICE - PHYSICAL FILE SYSTEM"

print_subsection "2.1 Storage Directory Structure"
echo "Storage service file system layout:"
docker exec storage-service find /data -type d 2>/dev/null | head -20 || echo "❌ Cannot access storage-service file system"

print_subsection "2.2 Actual Object Files"
echo "All stored object files (UUID files):"
STORED_FILES=$(docker exec storage-service find /data/storage -type f 2>/dev/null)
if [ -n "$STORED_FILES" ]; then
    echo "$STORED_FILES" | while read file; do
        SIZE=$(docker exec storage-service stat -f%z "$file" 2>/dev/null || docker exec storage-service stat -c%s "$file" 2>/dev/null || echo "unknown")
        MODIFIED=$(docker exec storage-service stat -f%Sm "$file" 2>/dev/null || docker exec storage-service stat -c%y "$file" 2>/dev/null || echo "unknown")
        echo "📄 $file (${SIZE} bytes, modified: ${MODIFIED})"
    done
else
    echo "📂 No object files found in storage"
fi

print_subsection "2.3 Storage Index (SQLite)"
echo "Storage service SQLite index contents:"
docker exec storage-service sqlite3 /data/storage_index.db "
.tables
" 2>/dev/null || echo "❌ Cannot access storage SQLite database"

echo ""
echo "Storage objects in SQLite index:"
docker exec storage-service sqlite3 /data/storage_index.db "
SELECT 
    object_id,
    file_path,
    size_bytes,
    checksum,
    created_at
FROM storage_objects 
ORDER BY created_at DESC;" 2>/dev/null || echo "❌ No storage_objects table or empty"

# 3. IDENTITY SERVICE DATA
print_section "3. IDENTITY SERVICE - USER DATA"

print_subsection "3.1 Identity SQLite Database"
echo "Users registered in system:"
docker exec identity-service sqlite3 /data/identity.db "
.tables
" 2>/dev/null || echo "❌ Cannot access identity SQLite database"

echo ""
docker exec identity-service sqlite3 /data/identity.db "
SELECT 
    user_id,
    username,
    created_at
FROM users 
ORDER BY created_at DESC;" 2>/dev/null || echo "❌ No users table or empty"

# 4. DOCKER VOLUMES INSPECTION
print_section "4. DOCKER VOLUMES & PERSISTENCE"

print_subsection "4.1 Docker Volumes"
echo "Docker volumes used for persistence:"
docker volume ls | grep -E "(storage|identity|postgres)"

print_subsection "4.2 Volume Inspection"
for volume in $(docker volume ls -q | grep -E "(storage|identity|postgres)"); do
    echo ""
    echo "🗂️  Volume: $volume"
    docker run --rm -v $volume:/data alpine ls -la /data 2>/dev/null | head -10 || echo "   ❌ Cannot inspect volume $volume"
done

# 5. STORAGE STATISTICS & ANALYSIS
print_section "5. STORAGE ANALYSIS & STATISTICS"

print_subsection "5.1 File System Usage"
echo "Storage service disk usage:"
docker exec storage-service df -h /data 2>/dev/null || echo "❌ Cannot get disk usage"

print_subsection "5.2 Object Count Analysis"
# Count files vs metadata entries
PHYSICAL_FILES=$(docker exec storage-service find /data/storage -type f 2>/dev/null | wc -l)
METADATA_COUNT=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COUNT(*) FROM object_metadata;" 2>/dev/null | tr -d ' ' || echo "0")

echo "📊 Storage Consistency Check:"
echo "   Physical files (.bin): $PHYSICAL_FILES"
echo "   Metadata entries:       $METADATA_COUNT"

if [ "$PHYSICAL_FILES" -eq "$METADATA_COUNT" ]; then
    echo "   ✅ CONSISTENT: File count matches metadata count"
else
    echo "   ⚠️  INCONSISTENT: File count ($PHYSICAL_FILES) != Metadata count ($METADATA_COUNT)"
    if [ "$PHYSICAL_FILES" -gt "$METADATA_COUNT" ]; then
        echo "      → Orphaned files detected (files without metadata)"
    else
        echo "      → Missing files detected (metadata without files)"
    fi
fi

print_subsection "5.3 Storage Size Analysis"
TOTAL_PHYSICAL_SIZE=$(docker exec storage-service find /data/storage -type f -exec stat -f%z {} + 2>/dev/null | awk '{sum+=$1} END {print sum+0}' || echo "0")
TOTAL_METADATA_SIZE=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COALESCE(SUM(size_bytes), 0) FROM object_metadata;" 2>/dev/null | tr -d ' ' || echo "0")

echo "💾 Storage Size Analysis:"
echo "   Physical storage used:  $(numfmt --to=iec $TOTAL_PHYSICAL_SIZE 2>/dev/null || echo "$TOTAL_PHYSICAL_SIZE bytes")"
echo "   Metadata reported size: $(numfmt --to=iec $TOTAL_METADATA_SIZE 2>/dev/null || echo "$TOTAL_METADATA_SIZE bytes")"

if [ "$TOTAL_PHYSICAL_SIZE" -eq "$TOTAL_METADATA_SIZE" ]; then
    echo "   ✅ CONSISTENT: Physical size matches metadata size"
else
    echo "   ⚠️  SIZE MISMATCH: Physical ($TOTAL_PHYSICAL_SIZE) != Metadata ($TOTAL_METADATA_SIZE)"
fi

# 6. SAMPLE FILE INSPECTION
print_section "6. SAMPLE FILE CONTENT INSPECTION"

print_subsection "6.1 Sample Object Content"
SAMPLE_FILE=$(docker exec storage-service find /data/storage -name "*.bin" -type f 2>/dev/null | head -n 1)
if [ -n "$SAMPLE_FILE" ]; then
    echo "📄 Inspecting sample file: $SAMPLE_FILE"
    echo "   First 100 characters of content:"
    docker exec storage-service head -c 100 "$SAMPLE_FILE" 2>/dev/null | cat -A || echo "   ❌ Cannot read file content"
    echo ""
    echo "   File checksum (MD5):"
    docker exec storage-service md5sum "$SAMPLE_FILE" 2>/dev/null || echo "   ❌ Cannot calculate checksum"
else
    echo "📂 No files available for content inspection"
fi

# 7. CLEANUP RECOMMENDATIONS
print_section "7. STORAGE HEALTH & RECOMMENDATIONS"

print_subsection "7.1 Potential Issues"
echo "🔍 Checking for common storage issues..."

# Check for orphaned files
if [ "$PHYSICAL_FILES" -gt "$METADATA_COUNT" ]; then
    echo "⚠️  FOUND: $((PHYSICAL_FILES - METADATA_COUNT)) orphaned files (files without metadata)"
    echo "   Recommendation: Run cleanup script to remove orphaned files"
fi

# Check for missing files
if [ "$METADATA_COUNT" -gt "$PHYSICAL_FILES" ]; then
    echo "⚠️  FOUND: $((METADATA_COUNT - PHYSICAL_FILES)) missing files (metadata without files)"  
    echo "   Recommendation: Check storage service logs for deletion errors"
fi

# Check for empty files
EMPTY_FILES=$(docker exec storage-service find /data/storage -name "*.bin" -size 0 2>/dev/null | wc -l)
if [ "$EMPTY_FILES" -gt 0 ]; then
    echo "⚠️  FOUND: $EMPTY_FILES empty files (0 bytes)"
    echo "   Recommendation: Investigate upload failures"
fi

if [ "$PHYSICAL_FILES" -eq "$METADATA_COUNT" ] && [ "$EMPTY_FILES" -eq 0 ]; then
    echo "✅ HEALTHY: No storage issues detected"
fi

print_subsection "7.2 Storage Summary"
echo "📈 FINAL STORAGE REPORT:"
echo "   📦 Total Buckets:        $(docker exec postgres-db psql -U s3user -d s3storage -t -c 'SELECT COUNT(*) FROM buckets;' 2>/dev/null | tr -d ' ' || echo '0')"
echo "   📄 Total Objects:        $METADATA_COUNT"
echo "   💾 Physical Files:       $PHYSICAL_FILES" 
echo "   🗃️  Total Storage Used:   $(numfmt --to=iec $TOTAL_PHYSICAL_SIZE 2>/dev/null || echo "$TOTAL_PHYSICAL_SIZE bytes")"
echo "   👥 Registered Users:     $(docker exec identity-service sqlite3 /data/identity.db 'SELECT COUNT(*) FROM users;' 2>/dev/null || echo '0')"

echo ""
echo "🎯 INSPECTION COMPLETE!"
echo "=============================="
echo "This report shows the actual physical storage state across all services."
echo "Use this information to verify data consistency and troubleshoot issues."