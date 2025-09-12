#!/bin/bash

echo "🐳 Starting Google Maps Clone - Individual Docker Containers"
echo "=============================================================="

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
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Create Docker network if it doesn't exist
print_status "Creating Docker network 'maps-network'..."
docker network create maps-network 2>/dev/null && print_status "Network created" || print_warning "Network already exists"

# Build base Docker image
print_header "\n🏗️  Building Base Docker Image..."
docker build -t google-maps-clone:latest . || {
    print_error "Failed to build base image"
    exit 1
}

print_header "\n🚀 Starting Individual Docker Services..."

# 1. Redis (Shared Database)
print_status "Starting Redis container..."
docker run -d \
    --name maps-redis \
    --network maps-network \
    -p 6379:6379 \
    --restart unless-stopped \
    redis:7-alpine

# 2. API Gateway Service
print_status "Starting API Gateway Service (Port 8080)..."
docker run -d \
    --name maps-api-gateway \
    --network maps-network \
    -p 8080:8080 \
    --restart unless-stopped \
    -e REDIS_HOST=maps-redis \
    -e REDIS_PORT=6379 \
    google-maps-clone:latest \
    python simple_api.py

# 3. Navigation Service
print_status "Starting Navigation Service (Port 8081)..."
docker run -d \
    --name maps-navigation \
    --network maps-network \
    -p 8081:8081 \
    --restart unless-stopped \
    -e REDIS_HOST=maps-redis \
    -e REDIS_PORT=6379 \
    google-maps-clone:latest \
    python navigation_service.py

# 4. AI/ML Service
print_status "Starting AI/ML Service (Port 8082)..."
docker run -d \
    --name maps-ai-ml \
    --network maps-network \
    -p 8082:8082 \
    --restart unless-stopped \
    -e REDIS_HOST=maps-redis \
    -e REDIS_PORT=6379 \
    google-maps-clone:latest \
    python ai_ml_service.py

# 5. Places & Business Service
print_status "Starting Places & Business Service (Port 8083)..."
docker run -d \
    --name maps-places \
    --network maps-network \
    -p 8083:8083 \
    --restart unless-stopped \
    -e REDIS_HOST=maps-redis \
    -e REDIS_PORT=6379 \
    google-maps-clone:latest \
    python places_business_service.py

# 6. Traffic & Real-Time Service
print_status "Starting Traffic & Real-Time Service (Port 8084)..."
docker run -d \
    --name maps-traffic \
    --network maps-network \
    -p 8084:8084 \
    --restart unless-stopped \
    -e REDIS_HOST=maps-redis \
    -e REDIS_PORT=6379 \
    google-maps-clone:latest \
    python traffic_realtime_service.py

# 7. Maps & Visualization Service
print_status "Starting Maps & Visualization Service (Port 8085)..."
docker run -d \
    --name maps-visualization \
    --network maps-network \
    -p 8085:8085 \
    --restart unless-stopped \
    -e REDIS_HOST=maps-redis \
    -e REDIS_PORT=6379 \
    google-maps-clone:latest \
    python maps_visualization_service.py

# 8. Web UI Service
print_status "Starting Web UI Service (Port 3002)..."
docker run -d \
    --name maps-web-ui \
    --network maps-network \
    -p 3002:3002 \
    --restart unless-stopped \
    google-maps-clone:latest \
    bash -c "cd ui && python maps_ui.py"

# Wait for services to start
print_header "\n⏳ Waiting for services to start..."
sleep 10

# Check service health
print_header "\n🔍 Checking Service Health..."
services=(
    "maps-redis:6379"
    "maps-api-gateway:8080/health"
    "maps-navigation:8081/health"
    "maps-ai-ml:8082/health"
    "maps-places:8083/health"
    "maps-traffic:8084/health"
    "maps-visualization:8085/health"
    "maps-web-ui:3002"
)

for service in "${services[@]}"; do
    container="${service%%:*}"
    endpoint="${service##*:}"
    
    if docker ps --filter "name=${container}" --format "table {{.Names}}" | grep -q "${container}"; then
        if [[ $endpoint == *"health"* ]] || [[ $endpoint == "3002" ]] || [[ $endpoint == "6379" ]]; then
            print_status "✅ ${container} is running"
        fi
    else
        print_error "❌ ${container} is not running"
    fi
done

print_header "\n📊 Docker Container Status"
echo "================================================"
docker ps --filter "name=maps-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

print_header "\n🌐 Service Endpoints"
echo "================================================"
echo "🔗 API Gateway:        http://localhost:8080"
echo "🗺️  Navigation:         http://localhost:8081"
echo "🤖 AI/ML:              http://localhost:8082"
echo "🏢 Places & Business:  http://localhost:8083"
echo "🚦 Traffic & Real-Time: http://localhost:8084"
echo "🗺️  Maps & Visualization: http://localhost:8085"
echo "🌐 Web UI:             http://localhost:3002"
echo ""
echo "📋 API Documentation:"
echo "   • Navigation API:    http://localhost:8081/docs"
echo "   • AI/ML API:         http://localhost:8082/docs"
echo "   • Places API:        http://localhost:8083/docs"
echo "   • Traffic API:       http://localhost:8084/docs"
echo "   • Maps API:          http://localhost:8085/docs"

print_header "\n🧪 Quick Test Commands"
echo "================================================"
echo "# Test all services:"
echo "curl http://localhost:8081/api/v1/navigation/test-all"
echo "curl http://localhost:8082/api/v1/ai/test-all"
echo "curl http://localhost:8083/api/v1/places/test-all"
echo "curl http://localhost:8084/api/v1/traffic/test-all"
echo "curl http://localhost:8085/api/v1/maps/test-all"

print_header "\n🛑 Stop Services"
echo "================================================"
echo "Use: ./stop-individual-dockers.sh"
echo "Or:  docker stop maps-redis maps-api-gateway maps-navigation maps-ai-ml maps-places maps-traffic maps-visualization maps-web-ui"

print_header "\n✅ All Google Maps Clone Services Started Successfully!"
echo "🎯 Access the Web UI at: http://localhost:3002"