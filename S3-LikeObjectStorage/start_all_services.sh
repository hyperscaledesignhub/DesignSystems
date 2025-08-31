#!/bin/bash

echo "🚀 STARTING S3-LIKE OBJECT STORAGE SYSTEM"
echo "=========================================="

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

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..." "info"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s $health_url > /dev/null 2>&1; then
            print_status "$service_name is ready!" "success"
            return 0
        fi
        
        if [ $attempt -eq 1 ]; then
            echo -n "   "
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo ""
    print_status "$service_name failed to start within $((max_attempts * 2)) seconds" "error"
    return 1
}

# Check if script is run from correct directory
if [ ! -f "docker-compose.yml" ] && [ ! -d "services" ]; then
    print_status "Error: Please run this script from the project root directory" "error"
    print_status "Expected to find 'services/' directory and docker files" "info"
    exit 1
fi

echo ""
print_status "STEP 1: Cleanup any existing services" "info"
echo "─────────────────────────────────────────"

# Stop any existing services (suppress errors if they don't exist)
docker stop postgres-db api-gateway identity-service bucket-service object-service storage-service metadata-service 2>/dev/null || true
docker rm postgres-db api-gateway identity-service bucket-service object-service storage-service metadata-service 2>/dev/null || true

print_status "Existing services cleaned up" "success"

echo ""
print_status "STEP 2: Create Docker network" "info"
echo "─────────────────────────────────────────"

# Create docker network if it doesn't exist
if ! docker network ls | grep -q "s3-network"; then
    docker network create s3-network
    print_status "Created s3-network" "success"
else
    print_status "s3-network already exists" "info"
fi

echo ""
print_status "STEP 3: Build all Docker images" "info"
echo "─────────────────────────────────────────"

# Build all services
services=("api-gateway" "identity" "bucket" "object" "storage" "metadata")

for service in "${services[@]}"; do
    echo "Building $service service..."
    if docker build -t ${service}-service services/${service}/ > /dev/null 2>&1; then
        print_status "$service service built successfully" "success"
    else
        print_status "Failed to build $service service" "error"
        exit 1
    fi
done

echo ""
print_status "STEP 4: Start PostgreSQL database" "info"
echo "─────────────────────────────────────────"

# Start PostgreSQL database
docker run -d \
    --name postgres-db \
    --network s3-network \
    -p 5432:5432 \
    -e POSTGRES_DB=s3storage \
    -e POSTGRES_USER=s3user \
    -e POSTGRES_PASSWORD=s3password \
    -v postgres_data:/var/lib/postgresql/data \
    postgres:13

if wait_for_service "PostgreSQL" "http://localhost:5432" || sleep 10; then
    print_status "PostgreSQL database started" "success"
else
    print_status "PostgreSQL may need more time to initialize" "warning"
fi

echo ""
print_status "STEP 5: Start core services" "info"
echo "─────────────────────────────────────────"

# Start Identity Service
print_status "Starting Identity Service..." "info"
docker run -d \
    --name identity-service \
    --network s3-network \
    -p 7851:7851 \
    -v identity_data:/data \
    identity-service

wait_for_service "Identity Service" "http://localhost:7851/health"

# Start Bucket Service  
print_status "Starting Bucket Service..." "info"
docker run -d \
    --name bucket-service \
    --network s3-network \
    -p 7861:7861 \
    -e DATABASE_URL="postgresql://s3user:s3password@postgres-db:5432/s3storage" \
    bucket-service

wait_for_service "Bucket Service" "http://localhost:7861/health"

# Start Storage Service
print_status "Starting Storage Service..." "info"
docker run -d \
    --name storage-service \
    --network s3-network \
    -p 7881:7881 \
    -v storage_data:/data \
    storage-service

wait_for_service "Storage Service" "http://localhost:7881/health"

# Start Metadata Service
print_status "Starting Metadata Service..." "info"
docker run -d \
    --name metadata-service \
    --network s3-network \
    -p 7891:7891 \
    -e DATABASE_URL="postgresql://s3user:s3password@postgres-db:5432/s3storage" \
    metadata-service

wait_for_service "Metadata Service" "http://localhost:7891/health"

# Start Object Service
print_status "Starting Object Service..." "info"
docker run -d \
    --name object-service \
    --network s3-network \
    -p 7871:7871 \
    object-service

wait_for_service "Object Service" "http://localhost:7871/health"

# Start API Gateway
print_status "Starting API Gateway..." "info"
docker run -d \
    --name api-gateway \
    --network s3-network \
    -p 7841:7841 \
    api-gateway

wait_for_service "API Gateway" "http://localhost:7841/health"

echo ""
print_status "STEP 6: Start Demo UI Server" "info"
echo "─────────────────────────────────────────"

# Kill any existing UI server
pkill -f "python.*serve_ui.py" 2>/dev/null || true

# Start UI server in background
if [ -f "serve_ui.py" ]; then
    python serve_ui.py > ui_server.log 2>&1 &
    UI_PID=$!
    echo $UI_PID > ui_server.pid
    
    # Wait a moment and check if UI server started
    sleep 3
    if kill -0 $UI_PID 2>/dev/null; then
        print_status "Demo UI Server started on http://localhost:3000" "success"
        print_status "UI Server PID: $UI_PID (saved to ui_server.pid)" "info"
    else
        print_status "Failed to start UI Server" "error"
    fi
else
    print_status "serve_ui.py not found - skipping UI server" "warning"
fi

echo ""
print_status "STEP 7: System Status Check" "info"
echo "─────────────────────────────────────────"

# Final status check
echo "Service Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(postgres|identity|bucket|object|storage|metadata|gateway)"

echo ""
echo "Health Check Results:"
services_health=(
    "API Gateway:http://localhost:7841/health"
    "Identity:http://localhost:7851/health"
    "Bucket:http://localhost:7861/health"
    "Object:http://localhost:7871/health"
    "Storage:http://localhost:7881/health"
    "Metadata:http://localhost:7891/health"
)

for service_health in "${services_health[@]}"; do
    service_name=$(echo $service_health | cut -d: -f1)
    health_url=$(echo $service_health | cut -d: -f2-)
    
    if curl -s $health_url > /dev/null 2>&1; then
        print_status "$service_name: Healthy" "success"
    else
        print_status "$service_name: Unhealthy" "error"
    fi
done

# Check UI server
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_status "Demo UI: Available" "success"
else
    print_status "Demo UI: Not available" "error"
fi

echo ""
print_status "🎉 S3-LIKE OBJECT STORAGE SYSTEM STARTUP COMPLETE!" "success"
echo "=========================================================="
echo ""
echo "📋 ACCESS POINTS:"
echo "   🌐 Demo UI:        http://localhost:3000/demo-ui.html"
echo "   🚪 API Gateway:    http://localhost:7841"
echo "   👤 Identity:       http://localhost:7851"
echo "   🪣 Bucket Service: http://localhost:7861"
echo "   📄 Object Service: http://localhost:7871"
echo "   💾 Storage:        http://localhost:7881"
echo "   📊 Metadata:       http://localhost:7891"
echo "   🗄️  PostgreSQL:    localhost:5432"
echo ""
echo "🛠️  MANAGEMENT COMMANDS:"
echo "   ./stop_all_services.sh     - Stop all services"
echo "   ./quick_storage_check.sh   - Check system status"  
echo "   ./inspect_storage.sh       - Detailed storage analysis"
echo ""
echo "📝 LOGS:"
echo "   UI Server log: ui_server.log"
echo "   Docker logs:   docker logs <service-name>"

# Save startup timestamp
echo "$(date): System started successfully" >> startup.log