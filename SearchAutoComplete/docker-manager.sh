#!/bin/bash

# Search Autocomplete System - Docker Manager
# Individual Docker containers for all services and infrastructure

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🐳 Search Autocomplete System - Docker Manager${NC}"
echo

# Create network
create_network() {
    echo -e "${YELLOW}Creating Docker network...${NC}"
    docker network create autocomplete-net 2>/dev/null || echo "Network already exists"
}

# Remove all containers and network
cleanup() {
    echo -e "${YELLOW}Cleaning up existing containers...${NC}"
    docker stop $(docker ps -q --filter "name=autocomplete-") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=autocomplete-") 2>/dev/null || true
    docker network rm autocomplete-net 2>/dev/null || true
}

# Start infrastructure services
start_infrastructure() {
    echo -e "${YELLOW}Starting infrastructure services...${NC}"
    
    # PostgreSQL
    docker run -d \
        --name autocomplete-postgres \
        --network autocomplete-net \
        -e POSTGRES_DB=autocomplete_test \
        -e POSTGRES_USER=testuser \
        -e POSTGRES_PASSWORD=testpass \
        -p 15432:5432 \
        postgres:13
    
    # Redis
    docker run -d \
        --name autocomplete-redis \
        --network autocomplete-net \
        -p 16379:6379 \
        redis:7-alpine
    
    # Zookeeper
    docker run -d \
        --name autocomplete-zookeeper \
        --network autocomplete-net \
        -e ZOOKEEPER_CLIENT_PORT=2181 \
        -e ZOOKEEPER_TICK_TIME=2000 \
        confluentinc/cp-zookeeper:latest
    
    # Kafka
    docker run -d \
        --name autocomplete-kafka \
        --network autocomplete-net \
        -p 19092:9092 \
        -e KAFKA_PROCESS_ROLES=broker,controller \
        -e KAFKA_NODE_ID=1 \
        -e KAFKA_CONTROLLER_QUORUM_VOTERS=1@autocomplete-kafka:29093 \
        -e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,PLAINTEXT_HOST://0.0.0.0:9092 \
        -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://autocomplete-kafka:29092,PLAINTEXT_HOST://localhost:9092 \
        -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT \
        -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER \
        -e KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT \
        -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
        -e KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1 \
        -e KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1 \
        -e KAFKA_LOG_DIRS=/var/lib/kafka/data \
        -e CLUSTER_ID=test-kafka-cluster \
        confluentinc/cp-kafka:latest
    
    echo -e "${GREEN}✅ Infrastructure started${NC}"
    echo -e "${YELLOW}Waiting 45 seconds for infrastructure...${NC}"
    sleep 45
    
    # Initialize database tables
    echo -e "${YELLOW}Creating database tables...${NC}"
    docker exec autocomplete-postgres psql -U testuser -d autocomplete_test -c "
        CREATE TABLE IF NOT EXISTS query_frequencies (
            query TEXT PRIMARY KEY,
            frequency INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS trie_data (
            prefix TEXT PRIMARY KEY,
            suggestions JSONB NOT NULL,
            version INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert sample data for testing
        INSERT INTO query_frequencies (query, frequency) VALUES 
        ('javascript', 10),
        ('java', 8),
        ('python', 15),
        ('react', 12),
        ('node', 6)
        ON CONFLICT (query) DO UPDATE SET frequency = EXCLUDED.frequency;
        
        INSERT INTO trie_data (prefix, suggestions, version) VALUES 
        ('j', '[{\"text\":\"javascript\",\"frequency\":10},{\"text\":\"java\",\"frequency\":8}]', 1),
        ('ja', '[{\"text\":\"javascript\",\"frequency\":10},{\"text\":\"java\",\"frequency\":8}]', 1),
        ('jav', '[{\"text\":\"javascript\",\"frequency\":10},{\"text\":\"java\",\"frequency\":8}]', 1),
        ('java', '[{\"text\":\"javascript\",\"frequency\":10},{\"text\":\"java\",\"frequency\":8}]', 1),
        ('javas', '[{\"text\":\"javascript\",\"frequency\":10}]', 1),
        ('javascr', '[{\"text\":\"javascript\",\"frequency\":10}]', 1),
        ('p', '[{\"text\":\"python\",\"frequency\":15}]', 1),
        ('py', '[{\"text\":\"python\",\"frequency\":15}]', 1),
        ('pyt', '[{\"text\":\"python\",\"frequency\":15}]', 1),
        ('pyth', '[{\"text\":\"python\",\"frequency\":15}]', 1),
        ('pytho', '[{\"text\":\"python\",\"frequency\":15}]', 1),
        ('python', '[{\"text\":\"python\",\"frequency\":15}]', 1),
        ('r', '[{\"text\":\"react\",\"frequency\":12}]', 1),
        ('re', '[{\"text\":\"react\",\"frequency\":12}]', 1),
        ('rea', '[{\"text\":\"react\",\"frequency\":12}]', 1),
        ('reac', '[{\"text\":\"react\",\"frequency\":12}]', 1),
        ('react', '[{\"text\":\"react\",\"frequency\":12}]', 1),
        ('n', '[{\"text\":\"node\",\"frequency\":6}]', 1),
        ('no', '[{\"text\":\"node\",\"frequency\":6}]', 1),
        ('nod', '[{\"text\":\"node\",\"frequency\":6}]', 1),
        ('node', '[{\"text\":\"node\",\"frequency\":6}]', 1)
        ON CONFLICT (prefix) DO UPDATE SET suggestions = EXCLUDED.suggestions, version = EXCLUDED.version;
    "
    echo -e "${GREEN}✅ Database tables created with sample data${NC}"
}

# Start application services using existing binaries/scripts
start_services() {
    echo -e "${YELLOW}Starting application services...${NC}"
    
    # Query Service - Python
    docker run -d \
        --name autocomplete-query \
        --network autocomplete-net \
        -p 12893:17893 \
        -v "$SCRIPT_DIR/services/query-service":/app \
        -w /app \
        -e DB_HOST=autocomplete-postgres \
        -e REDIS_HOST=autocomplete-redis \
        python:3.10-slim bash -c "
            pip install -q fastapi uvicorn asyncpg redis pydantic python-multipart && 
            python main_docker.py
        "
    
    # Data Collection Service - Python  
    docker run -d \
        --name autocomplete-data-collection \
        --network autocomplete-net \
        -p 13761:18761 \
        -v "$SCRIPT_DIR/services/data-collection-service":/app \
        -w /app \
        -e REDIS_HOST=autocomplete-redis \
        -e KAFKA_BROKERS=autocomplete-kafka:29092 \
        python:3.10-slim bash -c "
            pip install -q fastapi uvicorn asyncpg redis pydantic python-multipart kafka-python aiokafka && 
            python main_test.py
        "
    
    # Analytics Aggregator - Python
    docker run -d \
        --name autocomplete-analytics \
        --network autocomplete-net \
        -p 14742:16742 \
        -v "$SCRIPT_DIR/services/analytics-aggregator":/app \
        -w /app \
        -e DB_HOST=autocomplete-postgres \
        -e KAFKA_BROKERS=autocomplete-kafka:29092 \
        python:3.10-slim bash -c "
            pip install -q fastapi uvicorn asyncpg kafka-python pydantic python-multipart && 
            python main_test.py
        "
    
    # Trie Cache Service - Go
    docker run -d \
        --name autocomplete-trie-cache \
        --network autocomplete-net \
        -p 15294:18294 \
        -v "$SCRIPT_DIR/services/trie-cache-service":/app \
        -w /app \
        -e REDIS_HOST=autocomplete-redis \
        -e DB_HOST=autocomplete-postgres \
        golang:1.21-alpine sh -c "
            go mod download && 
            go run main.go
        "
    
    # API Gateway - Go
    docker run -d \
        --name autocomplete-api-gateway \
        --network autocomplete-net \
        -p 11845:19845 \
        -v "$SCRIPT_DIR/services/api-gateway":/app \
        -w /app \
        -e REDIS_HOST=autocomplete-redis \
        -e QUERY_SERVICE_HOST=autocomplete-query \
        -e DATA_COLLECTION_HOST=autocomplete-data-collection \
        golang:1.21-alpine sh -c "
            go mod download && 
            go run main.go
        "
    
    echo -e "${GREEN}✅ Application services started${NC}"
    echo -e "${YELLOW}Waiting 30 seconds for services to initialize...${NC}"
    sleep 30
}

# Check service health
check_health() {
    echo -e "${YELLOW}Checking service health...${NC}"
    
    services=(
        "Query Service:12893"
        "Data Collection:13761"
        "Trie Cache:15294"
        "API Gateway:11845"
        "Analytics:14742"
    )
    
    for service_info in "${services[@]}"; do
        service_name="${service_info%:*}"
        port="${service_info#*:}"
        
        if curl -s "http://localhost:$port/health" | grep -q "healthy"; then
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
    echo $! > /tmp/autocomplete_ui_pid
    echo -e "${GREEN}✅ UI Server started on http://localhost:12847${NC}"
}

# Stop UI server
stop_ui() {
    if [ -f "/tmp/autocomplete_ui_pid" ]; then
        kill $(cat /tmp/autocomplete_ui_pid) 2>/dev/null || true
        rm -f /tmp/autocomplete_ui_pid
        echo -e "${GREEN}✅ UI Server stopped${NC}"
    fi
}

# Main commands
case "${1:-help}" in
    "start")
        echo -e "${BLUE}🚀 Starting complete system...${NC}"
        cleanup
        create_network
        start_infrastructure
        start_services
        check_health
        start_ui
        
        echo
        echo -e "${GREEN}🎉 Complete system started!${NC}"
        echo
        echo -e "${BLUE}📊 Access URLs:${NC}"
        echo "  • UI Interface:        http://localhost:12847"
        echo "  • API Gateway:         http://localhost:11845"
        echo "  • Query Service:       http://localhost:12893"
        echo "  • Data Collection:     http://localhost:13761"
        echo "  • Trie Cache:          http://localhost:15294"
        echo "  • Analytics:           http://localhost:14742"
        echo
        echo -e "${YELLOW}📝 Docker containers:${NC}"
        docker ps --filter "name=autocomplete-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        echo -e "${RED}To stop: ./docker-manager.sh stop${NC}"
        ;;
        
    "stop")
        echo -e "${YELLOW}🛑 Stopping complete system...${NC}"
        stop_ui
        cleanup
        echo -e "${GREEN}✅ Complete system stopped${NC}"
        ;;
        
    "restart")
        echo -e "${YELLOW}🔄 Restarting system...${NC}"
        $0 stop
        sleep 5
        $0 start
        ;;
        
    "status")
        echo -e "${BLUE}📊 System Status${NC}"
        echo
        docker ps --filter "name=autocomplete-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        check_health
        
        if [ -f "/tmp/autocomplete_ui_pid" ] && kill -0 $(cat /tmp/autocomplete_ui_pid) 2>/dev/null; then
            echo -e "${GREEN}✅ UI Server: running on http://localhost:12847${NC}"
        else
            echo -e "${RED}❌ UI Server: not running${NC}"
        fi
        ;;
        
    "logs")
        service_name=${2:-""}
        if [ -z "$service_name" ]; then
            echo -e "${YELLOW}Available services for logs:${NC}"
            docker ps --filter "name=autocomplete-" --format "{{.Names}}" | sed 's/autocomplete-/  • /'
            echo
            echo -e "${BLUE}Usage: $0 logs <service_name>${NC}"
            echo -e "${BLUE}Example: $0 logs query${NC}"
        else
            docker logs -f "autocomplete-$service_name" 2>/dev/null || {
                echo -e "${RED}Service 'autocomplete-$service_name' not found${NC}"
                exit 1
            }
        fi
        ;;
        
    "help"|*)
        echo -e "${BLUE}Usage: $0 {start|stop|restart|status|logs}${NC}"
        echo
        echo -e "${YELLOW}Commands:${NC}"
        echo "  start    - Start complete system with Docker containers"
        echo "  stop     - Stop and remove all containers"
        echo "  restart  - Stop and start the system"
        echo "  status   - Show system status and health"
        echo "  logs     - Show logs for a specific service"
        echo
        echo -e "${YELLOW}Examples:${NC}"
        echo "  $0 start           # Start everything"
        echo "  $0 status          # Check system health"
        echo "  $0 logs query      # View Query Service logs"
        echo "  $0 stop            # Stop everything"
        ;;
esac