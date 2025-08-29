#!/bin/bash

echo "🎮 Real-time Gaming Leaderboard Demo Launcher 🎮"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

# Function to clean up existing containers
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up existing containers...${NC}"
    docker-compose -f demo/docker-compose.yml down 2>/dev/null || true
    ./demo/cleanup.sh
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Function to build and start services
start_services() {
    echo -e "${YELLOW}🔨 Building services...${NC}"
    cd demo
    
    # Build and start all services
    docker-compose build --parallel
    
    echo -e "${YELLOW}🚀 Starting services...${NC}"
    docker-compose up -d
    
    cd ..
}

# Function to wait for services to be ready
wait_for_services() {
    echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
    
    # Wait for critical services
    services=(
        "http://localhost:23451/health"  # user-service
        "http://localhost:23452/health"  # game-service
        "http://localhost:23453/health"  # leaderboard-service
        "http://localhost:23454/health"  # score-service
        "http://localhost:23455/health"  # api-gateway
        "http://localhost:23456/health"  # websocket-service
        "http://localhost:23457/health"  # tournament-service
        "http://localhost:23458/health"  # demo-generator
    )
    
    for service in "${services[@]}"; do
        echo -n "Checking $service... "
        retries=30
        while [ $retries -gt 0 ]; do
            if curl -s "$service" > /dev/null 2>&1; then
                echo -e "${GREEN}Ready${NC}"
                break
            fi
            retries=$((retries - 1))
            sleep 2
        done
        if [ $retries -eq 0 ]; then
            echo -e "${RED}Failed${NC}"
        fi
    done
}

# Function to populate demo data
populate_demo_data() {
    echo -e "${YELLOW}📊 Populating demo data...${NC}"
    
    # Wait a bit for database initialization
    sleep 5
    
    # Trigger demo data population
    curl -X POST http://localhost:23458/api/v1/demo/populate \
         -H "Content-Type: application/json" \
         -d '{"users": 50, "games": 10, "tournaments": 5}' \
         2>/dev/null || echo "Demo data population will continue in background"
    
    echo -e "${GREEN}✅ Demo data population initiated${NC}"
}

# Function to display access URLs
display_urls() {
    echo ""
    echo -e "${GREEN}🎉 Demo is ready! Access the following URLs:${NC}"
    echo ""
    echo "📱 Main Demo UI:        http://localhost:3000"
    echo "🔍 Jaeger Tracing UI:   http://localhost:16686"
    echo "📊 Grafana Dashboard:   http://localhost:3001 (admin/admin)"
    echo "📈 Prometheus Metrics:  http://localhost:9090"
    echo ""
    echo "API Endpoints:"
    echo "  - API Gateway:        http://localhost:23455"
    echo "  - WebSocket:          ws://localhost:23456/ws"
    echo "  - Demo Generator:     http://localhost:23458"
    echo ""
    echo -e "${YELLOW}Demo Use Cases:${NC}"
    echo "1. Live Leaderboard - Real-time score updates and rankings"
    echo "2. Tournament System - Competitive gaming with prizes"
    echo "3. WebSocket Updates - Live event streaming"
    echo "4. Stress Testing - Load testing capabilities"
    echo "5. Distributed Tracing - View request flows in Jaeger"
    echo ""
    echo -e "${GREEN}Tips:${NC}"
    echo "• Click 'Populate Demo Data' in the UI to create sample data"
    echo "• Click 'Start Simulation' to see real-time updates"
    echo "• Use 'Simulate Burst' to test high-load scenarios"
    echo "• View traces in Jaeger to understand service interactions"
    echo ""
}

# Function to monitor logs
monitor_logs() {
    echo -e "${YELLOW}Would you like to monitor the logs? (y/n)${NC}"
    read -r response
    if [[ "$response" == "y" ]]; then
        echo "Showing logs (Ctrl+C to exit)..."
        cd demo
        docker-compose logs -f --tail=50
        cd ..
    fi
}

# Main execution
main() {
    echo ""
    check_docker
    echo ""
    
    echo -e "${YELLOW}This will clean up old containers and start fresh. Continue? (y/n)${NC}"
    read -r response
    if [[ "$response" != "y" ]]; then
        echo "Cancelled."
        exit 0
    fi
    
    cleanup
    echo ""
    
    start_services
    echo ""
    
    wait_for_services
    echo ""
    
    populate_demo_data
    echo ""
    
    display_urls
    
    monitor_logs
}

# Run main function
main