#!/bin/bash

# Gaming Leaderboard Demo - Startup Script
# This script starts all services for the gaming leaderboard demo

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to wait for a service to be healthy
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=0
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f -o /dev/null "$url" 2>/dev/null; then
            print_success "$service_name is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    print_warning "$service_name may not be fully ready (timeout reached)"
    return 1
}

# Main script
echo "============================================"
echo "   Gaming Leaderboard Demo - Startup"
echo "============================================"
echo ""

# Check if docker and docker-compose are installed
print_status "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Prerequisites checked!"

# Check if Docker daemon is running
print_status "Checking Docker daemon..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker daemon is not running. Please start Docker."
    exit 1
fi
print_success "Docker daemon is running!"

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Build all services
print_status "Building all services..."
docker-compose build --parallel

# Start infrastructure services first
print_status "Starting infrastructure services (PostgreSQL, Redis, Jaeger)..."
docker-compose up -d postgres redis jaeger

# Wait for infrastructure services
wait_for_service "PostgreSQL" "http://localhost:5432" || true
wait_for_service "Redis" "http://localhost:6379" || true
wait_for_service "Jaeger UI" "http://localhost:16686"

# Start core services
print_status "Starting core services..."
docker-compose up -d user-service tournament-service websocket-service

# Wait for core services
sleep 5  # Give services time to initialize

# Start API Gateway
print_status "Starting API Gateway..."
docker-compose up -d api-gateway

# Wait for API Gateway
wait_for_service "API Gateway" "http://localhost:23455/health"

# Start demo services
print_status "Starting demo services..."
docker-compose up -d demo-generator

# Start UI
print_status "Starting UI service..."
docker-compose up -d ui

# Wait for UI
wait_for_service "UI" "http://localhost:3000"

# Start monitoring services (optional)
print_status "Starting monitoring services (Prometheus, Grafana)..."
docker-compose up -d prometheus grafana || print_warning "Monitoring services are optional"

# Display service status
echo ""
echo "============================================"
echo "   Service Status"
echo "============================================"
docker-compose ps

# Display access URLs
echo ""
echo "============================================"
echo "   Access URLs"
echo "============================================"
echo -e "${GREEN}UI Dashboard:${NC} http://localhost:3000"
echo -e "${GREEN}API Gateway:${NC} http://localhost:23455"
echo -e "${GREEN}Jaeger UI:${NC} http://localhost:16686"
echo -e "${GREEN}Grafana:${NC} http://localhost:3001 (admin/admin)"
echo -e "${GREEN}Prometheus:${NC} http://localhost:9090"
echo ""
echo -e "${BLUE}WebSocket:${NC} ws://localhost:23456/ws/{channel}"
echo -e "${BLUE}PostgreSQL:${NC} localhost:5432 (gaming/gaming123)"
echo -e "${BLUE}Redis:${NC} localhost:6379"

# Health check summary
echo ""
echo "============================================"
echo "   Health Check"
echo "============================================"

# Check critical services
services=(
    "API Gateway|http://localhost:23455/health"
    "User Service|http://localhost:23451/health"
    "Tournament Service|http://localhost:23457/health"
    "WebSocket Service|http://localhost:23456/health"
)

all_healthy=true
for service_info in "${services[@]}"; do
    IFS='|' read -r name url <<< "$service_info"
    if curl -s -f -o /dev/null "$url" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $name"
    else
        echo -e "${RED}✗${NC} $name"
        all_healthy=false
    fi
done

echo ""
if [ "$all_healthy" = true ]; then
    print_success "All services are up and running!"
    echo ""
    echo "You can now:"
    echo "1. Open the UI at http://localhost:3000"
    echo "2. Click 'Populate Data' to create demo users"
    echo "3. Click 'Start Simulation' to see real-time updates"
    echo "4. Open Jaeger UI at http://localhost:16686 to see traces"
else
    print_warning "Some services may not be fully ready. Check docker logs for details."
    echo "Run 'docker-compose logs -f <service-name>' to see logs"
fi

echo ""
echo "To stop all services, run: ./cleanup.sh"
echo "============================================"