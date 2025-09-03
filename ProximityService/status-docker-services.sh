#!/bin/bash

# ProximityService - Independent Docker Services Status Script
# This script checks the status of all independent Docker containers

echo "📊 ProximityService Independent Docker Containers Status"
echo "========================================================="

# Function to check container status
check_container_status() {
    local container=$1
    local port=$2
    local description=$3
    
    if docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
        status="🟢 RUNNING"
    elif docker ps -a --format "table {{.Names}}" | grep -q "^${container}$"; then
        status="🔴 STOPPED"
    else
        status="⚪ NOT FOUND"
    fi
    
    printf "%-25s %-10s %-30s %s\n" "$container" "$port" "$description" "$status"
}

# Check each container
check_container_status "postgres-primary" "5832" "PostgreSQL Primary Database"
check_container_status "postgres-replica1" "5833" "PostgreSQL Replica 1 Database"
check_container_status "postgres-replica2" "5834" "PostgreSQL Replica 2 Database"
check_container_status "redis-master" "6739" "Redis Master Cache"
check_container_status "redis-replica1" "6740" "Redis Replica 1 Cache"
check_container_status "redis-replica2" "6741" "Redis Replica 2 Cache"
check_container_status "redis-sentinel1" "26379" "Redis Sentinel 1"
check_container_status "redis-sentinel2" "26380" "Redis Sentinel 2"
check_container_status "redis-sentinel3" "26381" "Redis Sentinel 3"
check_container_status "location-service" "8921" "Location Service API"
check_container_status "business-service-standalone" "9823" "Business Service API"
check_container_status "api-gateway" "7891" "API Gateway"
check_container_status "cache-warmer" "N/A" "Cache Warmer (background)"

# Check UI status
echo ""
echo "🌐 UI Server Status:"
echo "==================="
if [ -f "demo/.ui.pid" ]; then
    UI_PID=$(cat demo/.ui.pid)
    if ps -p $UI_PID > /dev/null 2>&1; then
        echo "UI Server               8081       Demo Web Interface         🟢 RUNNING (PID: $UI_PID)"
    else
        echo "UI Server               8081       Demo Web Interface         🔴 STOPPED (stale PID)"
    fi
else
    echo "UI Server               8081       Demo Web Interface         ⚪ NOT FOUND"
fi

# Check Docker network
echo ""
echo "📡 Docker Network Status:"
echo "========================="
if docker network ls | grep -q "proximity-network"; then
    echo "proximity-network       Custom Network                     🟢 EXISTS"
else
    echo "proximity-network       Custom Network                     ⚪ NOT FOUND"
fi

# Check Docker volumes
echo ""
echo "💾 Docker Volumes Status:"
echo "========================="
VOLUMES=("postgres_primary_data" "postgres_replica1_data" "postgres_replica2_data" "redis_master_data" "redis_replica1_data" "redis_replica2_data")
for volume in "${VOLUMES[@]}"; do
    if docker volume ls | grep -q "$volume"; then
        status="🟢 EXISTS"
    else
        status="⚪ NOT FOUND"
    fi
    printf "%-25s %s\n" "$volume" "$status"
done

# Health check endpoints
echo ""
echo "🔍 Quick Health Check:"
echo "======================"
echo "Testing service endpoints..."

# Function to check endpoint
check_endpoint() {
    local url=$1
    local service=$2
    if curl -s --connect-timeout 3 "$url" > /dev/null 2>&1; then
        echo "✅ $service - $url"
    else
        echo "❌ $service - $url"
    fi
}

check_endpoint "http://localhost:8921/health" "Location Service"
check_endpoint "http://localhost:9823/health" "Business Service"
check_endpoint "http://localhost:7891/health" "API Gateway"
check_endpoint "http://localhost:8081" "Demo UI"

echo ""
echo "🔧 Management Commands:"
echo "======================"
echo "Start all services:  ./start-docker-services.sh"
echo "Stop all services:   ./stop-docker-services.sh"
echo "View logs:           docker logs <container-name>"
echo "Shell into container: docker exec -it <container-name> /bin/sh"