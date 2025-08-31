#!/bin/bash

echo "🧹 ORPHANED FILE CLEANUP - S3 Object Storage"
echo "============================================"

# Safety check
echo "⚠️  WARNING: This script will delete orphaned files from storage!"
echo "Files that exist physically but have no metadata will be removed."
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cleanup cancelled"
    exit 0
fi

echo ""
echo "🔍 Analyzing storage consistency..."

# Get all physical files
echo "📁 Scanning physical files..."
docker exec storage-service find /data/storage -name "*.bin" -type f > /tmp/physical_files.txt 2>/dev/null
PHYSICAL_COUNT=$(wc -l < /tmp/physical_files.txt)
echo "   Found $PHYSICAL_COUNT physical files"

# Get all object IDs from metadata
echo "📊 Scanning metadata..."
docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT object_id FROM object_metadata;" 2>/dev/null | tr -d ' ' | grep -v '^$' > /tmp/metadata_objects.txt
METADATA_COUNT=$(wc -l < /tmp/metadata_objects.txt)
echo "   Found $METADATA_COUNT metadata entries"

# Find orphaned files
echo ""
echo "🔍 Finding orphaned files..."
ORPHANED=0

while IFS= read -r file_path; do
    # Extract UUID from file path (last part before .bin)
    filename=$(basename "$file_path" .bin)
    
    # Check if this UUID exists in metadata
    if ! grep -q "^$filename$" /tmp/metadata_objects.txt; then
        echo "🗑️  ORPHANED: $file_path (UUID: $filename)"
        
        # Delete the orphaned file
        if docker exec storage-service rm "$file_path" 2>/dev/null; then
            echo "   ✅ Deleted successfully"
            ((ORPHANED++))
        else
            echo "   ❌ Failed to delete"
        fi
    fi
done < /tmp/physical_files.txt

# Clean up temp files
rm -f /tmp/physical_files.txt /tmp/metadata_objects.txt

echo ""
echo "🧹 CLEANUP COMPLETE!"
echo "===================="
echo "   📄 Total physical files scanned: $PHYSICAL_COUNT"
echo "   📊 Total metadata entries:       $METADATA_COUNT"
echo "   🗑️  Orphaned files removed:       $ORPHANED"

if [ "$ORPHANED" -eq 0 ]; then
    echo "   ✅ No orphaned files found - storage is clean!"
else
    echo "   🧹 Removed $ORPHANED orphaned files"
    echo "   💾 Storage space reclaimed"
fi

echo ""
echo "💡 Run './quick_storage_check.sh' to verify cleanup results"