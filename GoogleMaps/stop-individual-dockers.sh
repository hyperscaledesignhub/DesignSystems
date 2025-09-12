#!/bin/bash

echo "🛑 Stopping Google Maps Clone - Individual Docker Containers"
echo "============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_warning "Docker is not running. Containers may already be stopped."
    exit 0
fi

print_header "\n🛑 Stopping Individual Docker Services..."

# List of all containers to stop
containers=(
    "maps-web-ui:Web UI Service"
    "maps-visualization:Maps & Visualization Service"
    "maps-traffic:Traffic & Real-Time Service"
    "maps-places:Places & Business Service"
    "maps-ai-ml:AI/ML Service"
    "maps-navigation:Navigation Service"
    "maps-api-gateway:API Gateway"
    "maps-redis:Redis Database"
)

print_status "Stopping containers in reverse order..."

for container_info in "${containers[@]}"; do
    container="${container_info%%:*}"
    name="${container_info##*:}"
    
    if docker ps --filter "name=${container}" --quiet | grep -q .; then
        print_status "Stopping $name..."
        docker stop "$container" 2>/dev/null || echo "  Failed to stop $container"
    else
        echo "  $name is not running"
    fi
done

print_header "\n🗑️  Removing stopped containers..."

for container_info in "${containers[@]}"; do
    container="${container_info%%:*}"
    name="${container_info##*:}"
    
    if docker ps -a --filter "name=${container}" --quiet | grep -q .; then
        print_status "Removing $name container..."
        docker rm "$container" 2>/dev/null || echo "  Failed to remove $container"
    fi
done

print_header "\n📊 Cleanup Options"
echo "================================================"
echo "Choose cleanup level:"
echo "1) Keep Docker network and volumes (recommended)"
echo "2) Remove Docker network"
echo "3) Remove Docker network and unused volumes"
echo "4) Skip cleanup"

read -p "Enter choice (1-4): " cleanup_choice

case $cleanup_choice in
    1)
        print_status "Keeping Docker network and volumes intact..."
        ;;
    2)
        print_warning "Removing Docker network..."
        docker network rm maps-network 2>/dev/null || true
        print_status "Docker network removed"
        ;;
    3)
        print_warning "Removing Docker network and unused volumes..."
        docker network rm maps-network 2>/dev/null || true
        docker volume prune -f 2>/dev/null || true
        print_status "Network and unused volumes removed"
        ;;
    4)
        print_status "Skipping cleanup..."
        ;;
    *)
        print_status "Invalid choice. Keeping network and volumes (default)..."
        ;;
esac

print_header "\n📈 System Status"
echo "================================================"

# Show remaining Docker containers
print_status "Running containers:"
running_containers=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10)
if [ -z "$running_containers" ]; then
    echo "  No running containers"
else
    echo "$running_containers"
fi

echo ""
print_status "Docker networks:"
docker network ls --filter name=maps-network --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}" || echo "  maps-network not found"

print_header "\n🔧 Restart Commands"
echo "================================================"
echo "🚀 Restart all services:      ./run-individual-dockers.sh"
echo "📊 Start specific service:    docker start [container-name]"
echo "📜 View stopped containers:   docker ps -a"
echo "🔍 Check Docker resources:    docker system df"
echo ""
echo "📋 Available service containers:"
echo "   - maps-redis, maps-api-gateway, maps-navigation"
echo "   - maps-ai-ml, maps-places, maps-traffic"
echo "   - maps-visualization, maps-web-ui"

# Final status check
stopped_containers=$(docker ps -q | wc -l)
if [ "$stopped_containers" -eq 0 ]; then
    print_header "\n✅ All Docker Services Stopped Successfully!"
    echo "🎯 No running containers detected"
else
    print_warning "\n⚠️  Some containers may still be running:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
fi

echo ""
print_header "🛑 Shutdown Complete!"
echo "💡 Run './run-individual-dockers.sh' to restart all services"