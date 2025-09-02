#!/bin/bash

# Search Autocomplete System - Docker Setup Script
# Creates individual Docker containers for all services and infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$SCRIPT_DIR/services"

echo -e "${BLUE}🐳 Search Autocomplete System - Docker Setup${NC}"
echo

# Create Docker network
create_network() {
    echo -e "${YELLOW}Creating Docker network...${NC}"
    docker network create autocomplete-network 2>/dev/null || echo -e "${YELLOW}Network already exists${NC}"
    echo -e "${GREEN}✅ Network ready${NC}"
}

# Build service images
build_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"
    
    # Query Service
    echo -e "${BLUE}Building Query Service...${NC}"
    cat > "$SERVICES_DIR/query-service/Dockerfile" << 'EOF'
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 17893
CMD ["python", "main_docker.py"]
EOF

    # Copy Docker-specific main file if it doesn't exist
    if [ ! -f "$SERVICES_DIR/query-service/main_docker.py" ]; then
        cp "$SERVICES_DIR/query-service/main_test.py" "$SERVICES_DIR/query-service/main_docker.py"
        sed -i.bak 's/localhost/autocomplete-redis/g; s/localhost/autocomplete-postgres/g' "$SERVICES_DIR/query-service/main_docker.py"
    fi
    
    docker build -t autocomplete-query-service "$SERVICES_DIR/query-service"
    
    # Data Collection Service
    echo -e "${BLUE}Building Data Collection Service...${NC}"
    cat > "$SERVICES_DIR/data-collection-service/Dockerfile" << 'EOF'
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 18761
CMD ["python", "main_test.py"]
EOF

    docker build -t autocomplete-data-collection "$SERVICES_DIR/data-collection-service"
    
    # Trie Cache Service
    echo -e "${BLUE}Building Trie Cache Service...${NC}"
    cat > "$SERVICES_DIR/trie-cache-service/Dockerfile" << 'EOF'
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o trie-cache-service main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/trie-cache-service .

EXPOSE 18294
CMD ["./trie-cache-service"]
EOF

    docker build -t autocomplete-trie-cache "$SERVICES_DIR/trie-cache-service"
    
    # API Gateway
    echo -e "${BLUE}Building API Gateway...${NC}"
    cat > "$SERVICES_DIR/api-gateway/Dockerfile" << 'EOF'
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o api-gateway main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/api-gateway .

EXPOSE 19845
CMD ["./api-gateway"]
EOF

    docker build -t autocomplete-api-gateway "$SERVICES_DIR/api-gateway"
    
    # Analytics Aggregator
    echo -e "${BLUE}Building Analytics Aggregator...${NC}"
    cat > "$SERVICES_DIR/analytics-aggregator/Dockerfile" << 'EOF'
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 16742
CMD ["python", "main_test.py"]
EOF

    docker build -t autocomplete-analytics "$SERVICES_DIR/analytics-aggregator"
    
    echo -e "${GREEN}✅ All images built successfully${NC}"
}

# Start infrastructure services
start_infrastructure() {
    echo -e "${YELLOW}Starting infrastructure services...${NC}"
    
    # PostgreSQL
    echo -e "${BLUE}Starting PostgreSQL...${NC}"
    docker run -d \
        --name autocomplete-postgres \
        --network autocomplete-network \
        -e POSTGRES_DB=autocomplete_test \
        -e POSTGRES_USER=testuser \
        -e POSTGRES_PASSWORD=testpass \
        -p 5432:5432 \
        postgres:13
    
    # Redis
    echo -e "${BLUE}Starting Redis...${NC}"
    docker run -d \
        --name autocomplete-redis \
        --network autocomplete-network \
        -p 6379:6379 \
        redis:7-alpine
    
    # Zookeeper (required for Kafka)
    echo -e "${BLUE}Starting Zookeeper...${NC}"
    docker run -d \
        --name autocomplete-zookeeper \
        --network autocomplete-network \
        -p 2181:2181 \
        -e ZOOKEEPER_CLIENT_PORT=2181 \
        -e ZOOKEEPER_TICK_TIME=2000 \
        confluentinc/cp-zookeeper:latest
    
    # Kafka
    echo -e "${BLUE}Starting Kafka...${NC}"
    docker run -d \
        --name autocomplete-kafka \
        --network autocomplete-network \
        -p 9092:9092 \
        -e KAFKA_BROKER_ID=1 \
        -e KAFKA_ZOOKEEPER_CONNECT=autocomplete-zookeeper:2181 \
        -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
        -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
        confluentinc/cp-kafka:latest
    
    echo -e "${GREEN}✅ Infrastructure services started${NC}"
    echo -e "${YELLOW}Waiting 30 seconds for infrastructure to initialize...${NC}"
    sleep 30
}

# Start application services
start_services() {
    echo -e "${YELLOW}Starting application services...${NC}"
    
    # Trie Cache Service
    echo -e "${BLUE}Starting Trie Cache Service...${NC}"
    docker run -d \
        --name autocomplete-trie-cache \
        --network autocomplete-network \
        -p 18294:18294 \
        -e REDIS_HOST=autocomplete-redis \
        -e DB_HOST=autocomplete-postgres \
        autocomplete-trie-cache
    
    # Query Service
    echo -e "${BLUE}Starting Query Service...${NC}"
    docker run -d \
        --name autocomplete-query-service \
        --network autocomplete-network \
        -p 17893:17893 \
        -e DB_HOST=autocomplete-postgres \
        -e REDIS_HOST=autocomplete-redis \
        autocomplete-query-service
    
    # Data Collection Service
    echo -e "${BLUE}Starting Data Collection Service...${NC}"
    docker run -d \
        --name autocomplete-data-collection \
        --network autocomplete-network \
        -p 18761:18761 \
        -e REDIS_HOST=autocomplete-redis \
        -e KAFKA_BROKERS=autocomplete-kafka:9092 \
        autocomplete-data-collection
    
    # Analytics Aggregator
    echo -e "${BLUE}Starting Analytics Aggregator...${NC}"
    docker run -d \
        --name autocomplete-analytics \
        --network autocomplete-network \
        -p 16742:16742 \
        -e DB_HOST=autocomplete-postgres \
        -e KAFKA_BROKERS=autocomplete-kafka:9092 \
        autocomplete-analytics
    
    # API Gateway
    echo -e "${BLUE}Starting API Gateway...${NC}"
    docker run -d \
        --name autocomplete-api-gateway \
        --network autocomplete-network \
        -p 19845:19845 \
        -e REDIS_HOST=autocomplete-redis \
        -e QUERY_SERVICE_HOST=autocomplete-query-service \
        -e DATA_COLLECTION_HOST=autocomplete-data-collection \
        autocomplete-api-gateway
    
    echo -e "${GREEN}✅ Application services started${NC}"
    echo -e "${YELLOW}Waiting 20 seconds for services to initialize...${NC}"
    sleep 20
}

# Check service health
check_health() {
    echo -e "${YELLOW}Checking service health...${NC}"
    
    services=(
        "Query Service:http://localhost:17893/health"
        "Data Collection:http://localhost:18761/health"
        "Trie Cache:http://localhost:18294/health"
        "API Gateway:http://localhost:19845/health"
        "Analytics:http://localhost:16742/health"
    )
    
    for service_info in "${services[@]}"; do
        service_name="${service_info%:*}"
        service_url="${service_info#*:}"
        
        if curl -s "$service_url" | grep -q "healthy"; then
            echo -e "${GREEN}✅ $service_name: healthy${NC}"
        else
            echo -e "${RED}❌ $service_name: unhealthy${NC}"
        fi
    done
}

# Start UI server
start_ui() {
    echo -e "${YELLOW}Starting UI Server...${NC}"
    cd "$SCRIPT_DIR/ui"
    python3 server.py &
    UI_PID=$!
    echo "$UI_PID" > /tmp/autocomplete_ui_pid
    echo -e "${GREEN}✅ UI Server started (PID: $UI_PID)${NC}"
}

# Main execution
case "${1:-start}" in
    "start")
        echo -e "${BLUE}🚀 Starting complete system...${NC}"
        create_network
        build_images
        start_infrastructure
        start_services
        check_health
        start_ui
        
        echo
        echo -e "${GREEN}🎉 Complete system started successfully!${NC}"
        echo
        echo -e "${BLUE}📊 Service URLs:${NC}"
        echo "  • UI Interface:        http://localhost:8080"
        echo "  • API Gateway:         http://localhost:19845"
        echo "  • Query Service:       http://localhost:17893"
        echo "  • Data Collection:     http://localhost:18761"
        echo "  • Trie Cache Service:  http://localhost:18294"
        echo "  • Analytics Aggregator: http://localhost:16742"
        echo
        echo -e "${BLUE}🐳 Docker Containers:${NC}"
        docker ps --filter "name=autocomplete-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        echo -e "${RED}⚠️  To stop all services, run: ./docker-setup.sh stop${NC}"
        ;;
        
    "stop")
        echo -e "${YELLOW}🛑 Stopping complete system...${NC}"
        
        # Stop UI server
        if [ -f "/tmp/autocomplete_ui_pid" ]; then
            UI_PID=$(cat /tmp/autocomplete_ui_pid)
            kill "$UI_PID" 2>/dev/null || true
            rm -f /tmp/autocomplete_ui_pid
            echo -e "${GREEN}✅ UI Server stopped${NC}"
        fi
        
        # Stop and remove all containers
        echo -e "${YELLOW}Stopping Docker containers...${NC}"
        docker stop $(docker ps -q --filter "name=autocomplete-") 2>/dev/null || true
        docker rm $(docker ps -aq --filter "name=autocomplete-") 2>/dev/null || true
        
        # Remove network
        docker network rm autocomplete-network 2>/dev/null || true
        
        echo -e "${GREEN}🎉 Complete system stopped successfully!${NC}"
        ;;
        
    "restart")
        echo -e "${YELLOW}🔄 Restarting complete system...${NC}"
        $0 stop
        sleep 5
        $0 start
        ;;
        
    "status")
        echo -e "${BLUE}📊 System Status${NC}"
        echo
        echo -e "${YELLOW}Docker Containers:${NC}"
        docker ps --filter "name=autocomplete-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        check_health
        ;;
        
    *)
        echo -e "${BLUE}Usage: $0 {start|stop|restart|status}${NC}"
        echo
        echo -e "${YELLOW}Commands:${NC}"
        echo "  start   - Build and start all services with Docker"
        echo "  stop    - Stop and remove all containers"
        echo "  restart - Stop and start the complete system"
        echo "  status  - Show current system status"
        exit 1
        ;;
esac