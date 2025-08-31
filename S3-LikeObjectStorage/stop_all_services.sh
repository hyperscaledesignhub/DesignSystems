#!/bin/bash

echo "🛑 STOPPING S3-LIKE OBJECT STORAGE SYSTEM"
echo "==========================================="

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

echo ""
print_status "STEP 1: Stop Demo UI Server" "info"
echo "─────────────────────────────────────────"

# Stop UI server using PID file
if [ -f "ui_server.pid" ]; then
    UI_PID=$(cat ui_server.pid)
    if kill $UI_PID 2>/dev/null; then
        print_status "Demo UI Server stopped (PID: $UI_PID)" "success"
    else
        print_status "Demo UI Server was not running or already stopped" "warning"
    fi
    rm -f ui_server.pid
else
    # Try to kill by process name as fallback
    if pkill -f "python.*serve_ui.py" 2>/dev/null; then
        print_status "Demo UI Server stopped (found by process name)" "success"
    else
        print_status "No Demo UI Server process found" "info"
    fi
fi

# Remove log file
rm -f ui_server.log

echo ""
print_status "STEP 2: Stop Docker Services" "info"
echo "─────────────────────────────────────────"

# List of all services to stop (in reverse dependency order)
services=(
    "api-gateway"
    "object-service" 
    "metadata-service"
    "storage-service"
    "bucket-service"
    "identity-service"
    "postgres-db"
)

echo "Stopping Docker containers..."
for service in "${services[@]}"; do
    if docker ps -q --filter "name=$service" | grep -q .; then
        print_status "Stopping $service..." "info"
        if docker stop $service > /dev/null 2>&1; then
            print_status "$service stopped successfully" "success"
        else
            print_status "Failed to stop $service" "error"
        fi
    else
        print_status "$service was not running" "info"
    fi
done

echo ""
print_status "STEP 3: Remove Docker Containers" "info"
echo "─────────────────────────────────────────"

echo "Removing stopped containers..."
for service in "${services[@]}"; do
    if docker ps -aq --filter "name=$service" | grep -q .; then
        if docker rm $service > /dev/null 2>&1; then
            print_status "$service container removed" "success"
        else
            print_status "Failed to remove $service container" "error"
        fi
    fi
done

echo ""
print_status "STEP 4: Cleanup Options" "info"
echo "─────────────────────────────────────────"

echo "What would you like to do with persistent data?"
echo "1) Keep all data (volumes and networks)"
echo "2) Remove Docker network only"  
echo "3) Remove network and volumes (DESTROYS ALL DATA)"
echo "4) Skip cleanup"

read -p "Choose option (1-4) [default: 1]: " cleanup_choice
cleanup_choice=${cleanup_choice:-1}

case $cleanup_choice in
    1)
        print_status "Keeping all persistent data" "info"
        ;;
    2)
        print_status "Removing Docker network..." "info"
        if docker network rm s3-network 2>/dev/null; then
            print_status "s3-network removed" "success"
        else
            print_status "s3-network was not found or failed to remove" "warning"
        fi
        ;;
    3)
        print_status "🚨 REMOVING ALL DATA - This will destroy all stored objects!" "warning"
        read -p "Are you absolutely sure? Type 'YES' to confirm: " confirm
        if [ "$confirm" = "YES" ]; then
            # Remove network
            docker network rm s3-network 2>/dev/null && print_status "s3-network removed" "success"
            
            # Remove volumes
            volumes=("postgres_data" "identity_data" "storage_data")
            for volume in "${volumes[@]}"; do
                if docker volume rm $volume 2>/dev/null; then
                    print_status "$volume removed" "success"
                else
                    print_status "$volume was not found" "info"
                fi
            done
            print_status "ALL DATA DESTROYED" "error"
        else
            print_status "Cleanup cancelled - data preserved" "info"
        fi
        ;;
    4)
        print_status "Skipping cleanup" "info"
        ;;
    *)
        print_status "Invalid choice - skipping cleanup" "warning"
        ;;
esac

echo ""
print_status "STEP 5: Final Status Check" "info"
echo "─────────────────────────────────────────"

# Check if any services are still running
remaining_containers=$(docker ps --filter "name=postgres-db" --filter "name=identity-service" --filter "name=bucket-service" --filter "name=object-service" --filter "name=storage-service" --filter "name=metadata-service" --filter "name=api-gateway" --format "{{.Names}}" 2>/dev/null)

if [ -n "$remaining_containers" ]; then
    print_status "⚠️  Some containers are still running:" "warning"
    echo "$remaining_containers"
else
    print_status "All containers stopped successfully" "success"
fi

# Check for remaining volumes
echo ""
echo "Remaining Docker volumes:"
docker volume ls | grep -E "(postgres_data|identity_data|storage_data)" || print_status "No S3 storage volumes found" "info"

# Check for network
echo ""
if docker network ls | grep -q "s3-network"; then
    print_status "s3-network still exists" "info"
else
    print_status "s3-network removed" "info"
fi

echo ""
print_status "🏁 S3-LIKE OBJECT STORAGE SYSTEM SHUTDOWN COMPLETE!" "success"
echo "======================================================"
echo ""
echo "📋 SUMMARY:"
echo "   🐳 Docker containers: Stopped and removed"
echo "   🌐 Demo UI server: Stopped"
echo "   📝 Log files: Cleaned up"
echo "   💾 Data persistence: Based on your cleanup choice"
echo ""
echo "🔄 TO RESTART:"
echo "   ./start_all_services.sh"
echo ""
echo "📊 TO CHECK STATUS:"
echo "   docker ps --all"
echo "   docker volume ls"
echo "   docker network ls"

# Save shutdown timestamp
echo "$(date): System stopped successfully" >> startup.log