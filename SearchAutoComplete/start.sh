#!/bin/bash

# Search Autocomplete System - Simple Start Script
# Starts all Docker services + Native UI

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🚀 Starting Search Autocomplete System${NC}"
echo

# Create network
create_network() {
    echo -e "${YELLOW}Creating Docker network...${NC}"
    docker network create autocomplete-net 2>/dev/null || echo "Network already exists"
}

# Clean up any existing containers
cleanup() {
    echo -e "${YELLOW}Cleaning up existing containers...${NC}"
    docker stop $(docker ps -q --filter "name=autocomplete-") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=autocomplete-") 2>/dev/null || true
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
}

# Initialize database
init_database() {
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
        
        -- Insert sample data
        INSERT INTO query_frequencies (query, frequency) VALUES 
        ('typescript', 25), ('python', 15), ('javascript', 10), ('java', 8),
        ('docker', 24), ('kubernetes', 19), ('react', 12), ('angular', 18),
        ('vue', 14), ('nextjs', 21), ('django', 22), ('flask', 16),
        ('aws', 23), ('azure', 15), ('firebase', 18), ('mysql', 22),
        ('postgresql', 18), ('mongodb', 20), ('redis cache', 14), ('git', 26),
        ('github', 24), ('webpack', 15), ('tailwind', 19), ('bootstrap', 16),
        ('jest', 17), ('cypress', 12), ('testing', 20), ('graphql', 16)
        ON CONFLICT (query) DO UPDATE SET frequency = EXCLUDED.frequency;
        
        -- Insert comprehensive trie data
        INSERT INTO trie_data (prefix, suggestions, version) VALUES 
        ('t', '[{\"query\":\"typescript\",\"score\":25},{\"query\":\"testing\",\"score\":20},{\"query\":\"tailwind\",\"score\":19}]', 1),
        ('ty', '[{\"query\":\"typescript\",\"score\":25}]', 1),
        ('typ', '[{\"query\":\"typescript\",\"score\":25}]', 1),
        ('type', '[{\"query\":\"typescript\",\"score\":25}]', 1),
        ('typescript', '[{\"query\":\"typescript\",\"score\":25}]', 1),
        ('p', '[{\"query\":\"python\",\"score\":15},{\"query\":\"postgresql\",\"score\":18}]', 1),
        ('py', '[{\"query\":\"python\",\"score\":15}]', 1),
        ('pyt', '[{\"query\":\"python\",\"score\":15}]', 1),
        ('python', '[{\"query\":\"python\",\"score\":15}]', 1),
        ('j', '[{\"query\":\"javascript\",\"score\":10},{\"query\":\"java\",\"score\":8},{\"query\":\"jest\",\"score\":17}]', 1),
        ('ja', '[{\"query\":\"javascript\",\"score\":10},{\"query\":\"java\",\"score\":8}]', 1),
        ('jav', '[{\"query\":\"javascript\",\"score\":10},{\"query\":\"java\",\"score\":8}]', 1),
        ('java', '[{\"query\":\"javascript\",\"score\":10},{\"query\":\"java\",\"score\":8}]', 1),
        ('javascript', '[{\"query\":\"javascript\",\"score\":10}]', 1),
        ('r', '[{\"query\":\"react\",\"score\":12},{\"query\":\"redis cache\",\"score\":14}]', 1),
        ('re', '[{\"query\":\"react\",\"score\":12},{\"query\":\"redis cache\",\"score\":14}]', 1),
        ('rea', '[{\"query\":\"react\",\"score\":12}]', 1),
        ('react', '[{\"query\":\"react\",\"score\":12}]', 1),
        ('d', '[{\"query\":\"docker\",\"score\":24},{\"query\":\"django\",\"score\":22}]', 1),
        ('do', '[{\"query\":\"docker\",\"score\":24}]', 1),
        ('doc', '[{\"query\":\"docker\",\"score\":24}]', 1),
        ('docker', '[{\"query\":\"docker\",\"score\":24}]', 1),
        ('g', '[{\"query\":\"git\",\"score\":26},{\"query\":\"github\",\"score\":24},{\"query\":\"graphql\",\"score\":16}]', 1),
        ('gi', '[{\"query\":\"git\",\"score\":26},{\"query\":\"github\",\"score\":24}]', 1),
        ('git', '[{\"query\":\"git\",\"score\":26},{\"query\":\"github\",\"score\":24}]', 1),
        ('github', '[{\"query\":\"github\",\"score\":24}]', 1),
        ('gr', '[{\"query\":\"graphql\",\"score\":16}]', 1),
        ('graphql', '[{\"query\":\"graphql\",\"score\":16}]', 1)
        ON CONFLICT (prefix) DO UPDATE SET suggestions = EXCLUDED.suggestions, version = EXCLUDED.version;
    "
    echo -e "${GREEN}✅ Database initialized with sample data${NC}"
}

# Start application services
start_services() {
    echo -e "${YELLOW}Starting application services...${NC}"
    
    # Query Service
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
    
    # Data Collection Service
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
    
    # Analytics Aggregator
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
    
    # Trie Cache Service
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
    
    # API Gateway
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

# Start UI server natively
start_ui() {
    echo -e "${YELLOW}Starting UI Server (native)...${NC}"
    cd "$SCRIPT_DIR/ui"
    python3 server.py &
    echo $! > /tmp/autocomplete_ui_pid
    echo -e "${GREEN}✅ UI Server started on http://localhost:12847${NC}"
}

# Check health
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

# Main execution
echo -e "${BLUE}🚀 Starting complete system...${NC}"
cleanup
create_network
start_infrastructure
init_database
start_services
start_ui
check_health

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
echo -e "${BLUE}🐳 Docker Containers:${NC}"
docker ps --filter "name=autocomplete-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo
echo -e "${RED}To stop: ./stop.sh${NC}"