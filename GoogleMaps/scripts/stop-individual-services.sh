#!/bin/bash
set -e

echo "🛑 Stopping Google Maps Clone - Individual Docker Services"
echo "=========================================================="

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

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
    print_warning "Docker is not running. Services may already be stopped."
    exit 0
fi

print_header "\\n🛑 Stopping Individual Docker Services..."

# List of all containers to stop
containers=(
    "maps-es-head:Elasticsearch Head"
    "maps-redis-commander:Redis Commander"
    "maps-nginx:Nginx Load Balancer"
    "maps-jaeger:Jaeger Tracing"
    "maps-grafana:Grafana Dashboards"
    "maps-prometheus:Prometheus Metrics"
    "maps-kafka:Kafka Message Queue"
    "maps-zookeeper:Zookeeper"
    "maps-neo4j:Neo4j Graph DB"
    "maps-influxdb:InfluxDB Metrics"
    "maps-elasticsearch:Elasticsearch"
    "maps-postgres:PostgreSQL+PostGIS"
    "maps-cassandra:Cassandra Database"
    "maps-redis:Redis Cache"
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

print_header "\\n🗑️  Removing stopped containers..."

for container_info in "${containers[@]}"; do
    container="${container_info%%:*}"
    name="${container_info##*:}"
    
    if docker ps -a --filter "name=${container}" --quiet | grep -q .; then
        print_status "Removing $name container..."
        docker rm "$container" 2>/dev/null || echo "  Failed to remove $container"
    fi
done

print_header "\\n📊 Cleanup Options"
echo "================================================"
echo "Choose cleanup level:"
echo "1) Keep data volumes (recommended)"
echo "2) Remove data volumes (⚠️  deletes all data)"  
echo "3) Remove network and volumes"
echo "4) Skip cleanup"

read -p "Enter choice (1-4): " cleanup_choice

case $cleanup_choice in
    1)
        print_status "Keeping data volumes intact..."
        ;;
    2)
        print_warning "Removing data volumes..."
        docker volume ls -q | grep "^maps_" | xargs -r docker volume rm 2>/dev/null || true
        print_status "Data volumes removed"
        ;;
    3)
        print_warning "Removing network and all volumes..."
        docker volume ls -q | grep "^maps_" | xargs -r docker volume rm 2>/dev/null || true
        docker network rm maps-network 2>/dev/null || true
        print_status "Network and volumes removed"
        ;;
    4)
        print_status "Skipping cleanup..."
        ;;
    *)
        print_status "Invalid choice. Keeping data volumes (default)..."
        ;;
esac

print_header "\\n📈 System Resource Status"
echo "================================================"

# Show remaining Docker resources
print_status "Running containers:"
running_containers=$(docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}" | head -10)
if [ -z "$running_containers" ]; then
    echo "  No running containers"
else
    echo "$running_containers"
fi

echo ""
print_status "Docker volumes:"
docker volume ls --format "table {{.Name}}\\t{{.Driver}}" | grep maps || echo "  No maps volumes found"

echo ""
print_status "Docker network:"
docker network ls --filter name=maps-network --format "table {{.Name}}\\t{{.Driver}}\\t{{.Scope}}" || echo "  maps-network not found"

print_header "\\n🔧 Restart Commands"
echo "================================================"
echo "🚀 Restart all services:      ./start-individual-services.sh"
echo "📊 Start specific service:    docker start [container-name]"
echo "📜 View stopped containers:   docker ps -a"
echo "🔍 Check Docker resources:    docker system df"
echo ""
echo "📋 Available service containers:"
echo "   - maps-redis, maps-cassandra, maps-postgres"
echo "   - maps-elasticsearch, maps-influxdb, maps-neo4j"  
echo "   - maps-kafka, maps-zookeeper"
echo "   - maps-prometheus, maps-grafana, maps-jaeger"
echo "   - maps-nginx, maps-redis-commander, maps-es-head"

# Final status check
stopped_containers=$(docker ps -q | wc -l)
if [ "$stopped_containers" -eq 0 ]; then
    print_header "\\n✅ All Docker Services Stopped Successfully!"
    echo "🎯 No running containers detected"
else
    print_warning "\\n⚠️  Some containers may still be running:"
    docker ps --format "table {{.Names}}\\t{{.Status}}"
fi

echo ""
print_header "🛑 Shutdown Complete!"
echo "💡 Run './start-individual-services.sh' to restart Docker services"
echo "🖥️  Don't forget to stop any running Python processes:"
echo "   - API Gateway (python src/complete_api.py)"
echo "   - Web UI (python ui/maps_ui.py)"
echo ""