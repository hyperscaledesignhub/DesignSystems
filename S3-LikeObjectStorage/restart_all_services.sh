#!/bin/bash

echo "🔄 RESTARTING S3-LIKE OBJECT STORAGE SYSTEM"
echo "============================================"

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    case $2 in
        "success") echo -e "${GREEN}✅ $1${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $1${NC}" ;;
        *) echo "$1" ;;
    esac
}

print_status "Step 1: Stopping all services..." "info"
./stop_all_services.sh

echo ""
print_status "Step 2: Waiting 5 seconds for cleanup..." "info"
sleep 5

echo ""
print_status "Step 3: Starting all services..." "info"
./start_all_services.sh

echo ""
print_status "🎉 RESTART COMPLETE!" "success"
print_status "Run './check_system_status.sh' to verify everything is working" "info"