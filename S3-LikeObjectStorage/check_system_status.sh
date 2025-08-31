#!/bin/bash

echo "📊 S3-LIKE OBJECT STORAGE SYSTEM STATUS CHECK"
echo "=============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    case $2 in
        "success") echo -e "${GREEN}✅ $1${NC}" ;;
        "error") echo -e "${RED}❌ $1${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $1${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $1${NC}" ;;
        *) echo "$1" ;;
    esac
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local health_url=$2
    local port=$3
    
    if curl -s $health_url > /dev/null 2>&1; then
        health_response=$(curl -s $health_url 2>/dev/null)
        print_status "$service_name (port $port): Healthy" "success"
        return 0
    else
        print_status "$service_name (port $port): Unhealthy or not responding" "error"
        return 1
    fi
}

echo ""
print_status "🐳 DOCKER CONTAINER STATUS" "info"
echo "─────────────────────────────────────────"

# Check if containers are running
services=("postgres-db" "api-gateway" "identity-service" "bucket-service" "object-service" "storage-service" "metadata-service")
running_services=0
total_services=${#services[@]}

echo "Container Status:"
for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --format "{{.Names}}" | grep -q "^$service$"; then
        status=$(docker ps --filter "name=$service" --format "{{.Status}}")
        print_status "$service: Running ($status)" "success"
        ((running_services++))
    else
        if docker ps -a --filter "name=$service" --format "{{.Names}}" | grep -q "^$service$"; then
            status=$(docker ps -a --filter "name=$service" --format "{{.Status}}")
            print_status "$service: Stopped ($status)" "error"
        else
            print_status "$service: Not found" "error"
        fi
    fi
done

echo ""
echo "Service Summary: $running_services/$total_services containers running"

if [ $running_services -eq $total_services ]; then
    print_status "All Docker services are running" "success"
elif [ $running_services -eq 0 ]; then
    print_status "No Docker services are running" "error"
else
    print_status "$running_services out of $total_services services are running" "warning"
fi

echo ""
print_status "🏥 SERVICE HEALTH CHECKS" "info"
echo "─────────────────────────────────────────"

# Health check for each service
healthy_services=0
health_checks=(
    "API Gateway:http://localhost:7841/health:7841"
    "Identity:http://localhost:7851/health:7851"
    "Bucket:http://localhost:7861/health:7861"
    "Object:http://localhost:7871/health:7871"
    "Storage:http://localhost:7881/health:7881"
    "Metadata:http://localhost:7891/health:7891"
)

for check in "${health_checks[@]}"; do
    service_name=$(echo $check | cut -d: -f1)
    health_url=$(echo $check | cut -d: -f2-)
    port=$(echo $check | cut -d: -f3)
    
    if check_service_health "$service_name" "$health_url" "$port"; then
        ((healthy_services++))
    fi
done

echo ""
print_status "🌐 DEMO UI STATUS" "info"
echo "─────────────────────────────────────────"

# Check UI server
if [ -f "ui_server.pid" ]; then
    UI_PID=$(cat ui_server.pid)
    if kill -0 $UI_PID 2>/dev/null; then
        if curl -s http://localhost:8080 > /dev/null 2>&1; then
            print_status "Demo UI Server: Running (PID: $UI_PID, http://localhost:8080)" "success"
        else
            print_status "Demo UI Server: Process running but not responding (PID: $UI_PID)" "warning"
        fi
    else
        print_status "Demo UI Server: PID file exists but process not running" "error"
        rm -f ui_server.pid
    fi
else
    if pgrep -f "python.*serve_ui.py" > /dev/null; then
        UI_PID=$(pgrep -f "python.*serve_ui.py")
        if curl -s http://localhost:8080 > /dev/null 2>&1; then
            print_status "Demo UI Server: Running (PID: $UI_PID, http://localhost:8080)" "success"
        else
            print_status "Demo UI Server: Process found but not responding (PID: $UI_PID)" "warning"
        fi
    else
        print_status "Demo UI Server: Not running" "error"
    fi
fi

echo ""
print_status "💾 STORAGE STATUS" "info"
echo "─────────────────────────────────────────"

# Quick storage stats (reuse existing logic from quick_storage_check.sh)
if [ $running_services -gt 0 ]; then
    # Count buckets
    BUCKET_COUNT=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COUNT(*) FROM buckets;" 2>/dev/null | tr -d ' ' || echo "0")
    
    # Count objects in metadata
    METADATA_OBJECTS=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COUNT(*) FROM object_metadata;" 2>/dev/null | tr -d ' ' || echo "0")
    
    # Count physical files
    PHYSICAL_FILES=$(docker exec storage-service find /data/storage -type f 2>/dev/null | wc -l || echo "0")
    
    # Calculate total size
    TOTAL_SIZE=$(docker exec postgres-db psql -U s3user -d s3storage -t -c "SELECT COALESCE(SUM(size_bytes), 0) FROM object_metadata;" 2>/dev/null | tr -d ' ' || echo "0")
    
    echo "Storage Statistics:"
    echo "   📦 Buckets: $BUCKET_COUNT"
    echo "   📄 Objects (metadata): $METADATA_OBJECTS"
    echo "   💾 Physical files: $PHYSICAL_FILES"
    echo "   📊 Total size: $(numfmt --to=iec $TOTAL_SIZE 2>/dev/null || echo "$TOTAL_SIZE bytes")"
    
    # Storage consistency check
    if [ "$METADATA_OBJECTS" -eq "$PHYSICAL_FILES" ]; then
        print_status "Storage consistency: Good (metadata matches files)" "success"
    else
        print_status "Storage consistency: Warning ($METADATA_OBJECTS metadata vs $PHYSICAL_FILES files)" "warning"
    fi
    
    if [ "$BUCKET_COUNT" -gt 0 ] && [ "$METADATA_OBJECTS" -gt 0 ]; then
        print_status "System data status: Active (contains data)" "info"
    else
        print_status "System data status: Empty (no data)" "info"
    fi
else
    print_status "Cannot check storage - services not running" "error"
fi

echo ""
print_status "🔗 DOCKER RESOURCES" "info"
echo "─────────────────────────────────────────"

# Check Docker network
if docker network ls | grep -q "s3-network"; then
    print_status "Docker network (s3-network): Exists" "success"
else
    print_status "Docker network (s3-network): Missing" "error"
fi

# Check Docker volumes
volumes=("postgres_data" "identity_data" "storage_data")
existing_volumes=0
for volume in "${volumes[@]}"; do
    if docker volume ls | grep -q "$volume"; then
        print_status "Volume ($volume): Exists" "success"
        ((existing_volumes++))
    else
        print_status "Volume ($volume): Missing" "error"
    fi
done

echo ""
print_status "📋 SYSTEM SUMMARY" "info"
echo "─────────────────────────────────────────"

# Overall system status
if [ $running_services -eq $total_services ] && [ $healthy_services -eq ${#health_checks[@]} ]; then
    print_status "🎉 SYSTEM STATUS: FULLY OPERATIONAL" "success"
    echo "   ✅ All containers running"
    echo "   ✅ All services healthy"
    echo "   ✅ Demo UI accessible"
elif [ $running_services -gt 0 ] && [ $healthy_services -gt 0 ]; then
    print_status "⚠️  SYSTEM STATUS: PARTIALLY OPERATIONAL" "warning"
    echo "   📊 $running_services/$total_services containers running"
    echo "   🏥 $healthy_services/${#health_checks[@]} services healthy"
else
    print_status "❌ SYSTEM STATUS: NOT OPERATIONAL" "error"
    echo "   🛑 Most or all services are down"
fi

echo ""
echo "🛠️  MANAGEMENT COMMANDS:"
echo "   ./start_all_services.sh    - Start all services"
echo "   ./stop_all_services.sh     - Stop all services"
echo "   ./quick_storage_check.sh   - Quick storage check"
echo "   ./inspect_storage.sh       - Detailed storage analysis"
echo ""

if [ $running_services -gt 0 ]; then
    echo "🌐 ACCESS POINTS:"
    echo "   Demo UI:        http://localhost:8080/demo-ui.html"
    echo "   API Gateway:    http://localhost:7841/health"
    echo "   Storage Stats:  http://localhost:7891/metadata/stats"
fi

# Save status check timestamp
echo "$(date): Status check completed - $running_services/$total_services containers running, $healthy_services/${#health_checks[@]} services healthy" >> startup.log