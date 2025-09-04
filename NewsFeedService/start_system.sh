#!/bin/bash

# News Feed System - Startup Script
# This script starts all 7 microservices and their dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"

# Create directories
mkdir -p "$LOG_DIR" "$PID_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 News Feed System - Startup Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ Waiting for $service_name to start on port $port...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        sleep 1
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to start after $max_attempts seconds${NC}"
    return 1
}

# Function to start a service
start_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    local env_vars=$4
    local extra_command=$5
    
    echo -e "${YELLOW}🔧 Starting $service_name...${NC}"
    
    cd "$SCRIPT_DIR/services/$service_dir"
    
    if [ -n "$extra_command" ]; then
        # For services with extra commands (like Celery workers)
        eval "$env_vars nohup python app/main.py > \"$LOG_DIR/$service_name.log\" 2>&1 & echo \$! > \"$PID_DIR/$service_name.pid\""
        
        # Start extra command
        eval "$env_vars nohup $extra_command > \"$LOG_DIR/$service_name-worker.log\" 2>&1 & echo \$! > \"$PID_DIR/$service_name-worker.pid\""
    else
        eval "$env_vars nohup python app/main.py > \"$LOG_DIR/$service_name.log\" 2>&1 & echo \$! > \"$PID_DIR/$service_name.pid\""
    fi
    
    cd "$SCRIPT_DIR"
}

echo -e "${YELLOW}📋 Step 1: Checking Dependencies...${NC}"

# Check Docker services
echo -e "${YELLOW}🐳 Checking Docker containers...${NC}"
if ! docker ps | grep -q postgres-newsfeed; then
    echo -e "${RED}❌ PostgreSQL container not running. Please start it first:${NC}"
    echo -e "${RED}   docker run -d --name postgres-newsfeed -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15${NC}"
    exit 1
fi

if ! docker ps | grep -q redis-newsfeed; then
    echo -e "${RED}❌ Redis container not running. Please start it first:${NC}"
    echo -e "${RED}   docker run -d --name redis-newsfeed -p 6379:6379 redis:7-alpine${NC}"
    exit 1
fi

if ! docker ps | grep -q rabbitmq-newsfeed; then
    echo -e "${RED}❌ RabbitMQ container not running. Please start it first:${NC}"
    echo -e "${RED}   docker run -d --name rabbitmq-newsfeed -p 5672:5672 -p 15672:15672 rabbitmq:3-management-alpine${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All Docker dependencies are running${NC}"

# Check and create databases
echo -e "${YELLOW}🗄️  Setting up databases...${NC}"
docker exec postgres-newsfeed psql -U user -d postgres -c "CREATE DATABASE userdb;" 2>/dev/null || echo "userdb already exists"
docker exec postgres-newsfeed psql -U user -d postgres -c "CREATE DATABASE postdb;" 2>/dev/null || echo "postdb already exists"  
docker exec postgres-newsfeed psql -U user -d postgres -c "CREATE DATABASE graphdb;" 2>/dev/null || echo "graphdb already exists"
docker exec postgres-newsfeed psql -U user -d postgres -c "CREATE DATABASE notificationdb;" 2>/dev/null || echo "notificationdb already exists"
echo -e "${GREEN}✅ Databases ready${NC}"

echo -e "${YELLOW}📋 Step 2: Starting Microservices...${NC}"

# Start services in dependency order
echo -e "\n${BLUE}🔹 Starting Core Services...${NC}"

# User Service (8371) - Core authentication service
start_service "user-service" "user-service" "8371" \
    "DATABASE_URL=\"postgresql://user:password@localhost:5432/userdb\" REDIS_URL=\"redis://localhost:6379\" SECRET_KEY=\"test-secret-key\" GRAPH_SERVICE_URL=\"http://localhost:8373\""

check_service "User Service" "8371"

# Graph Service (8373) - Social relationships
start_service "graph-service" "graph-service" "8373" \
    "DATABASE_URL=\"postgresql://user:password@localhost:5432/graphdb\" REDIS_URL=\"redis://localhost:6379\" USER_SERVICE_URL=\"http://localhost:8371\""

check_service "Graph Service" "8373"

echo -e "\n${BLUE}🔹 Starting Content Services...${NC}"

# Post Service (8372) - Content management
start_service "post-service" "post-service" "8372" \
    "DATABASE_URL=\"postgresql://user:password@localhost:5432/postdb\" REDIS_URL=\"redis://localhost:6379\" USER_SERVICE_URL=\"http://localhost:8371\" FANOUT_SERVICE_URL=\"http://localhost:8374\" SECRET_KEY=\"test-secret-key\""

check_service "Post Service" "8372"

# Fanout Service (8374) - Async distribution
start_service "fanout-service" "fanout-service" "8374" \
    "REDIS_URL=\"redis://localhost:6379\" RABBITMQ_URL=\"pyamqp://guest@localhost//\" GRAPH_SERVICE_URL=\"http://localhost:8373\"" \
    "celery -A app.main.celery_app worker --loglevel=info"

check_service "Fanout Service" "8374"

echo -e "\n${BLUE}🔹 Starting User-Facing Services...${NC}"

# News Feed Service (8375) - Feed aggregation
start_service "newsfeed-service" "newsfeed-service" "8375" \
    "REDIS_URL=\"redis://localhost:6379\" POST_SERVICE_URL=\"http://localhost:8372\" USER_SERVICE_URL=\"http://localhost:8371\""

check_service "News Feed Service" "8375"

# Notification Service (8376) - Notifications
start_service "notification-service" "notification-service" "8376" \
    "DATABASE_URL=\"postgresql://user:password@localhost:5432/notificationdb\" REDIS_URL=\"redis://localhost:6379\" USER_SERVICE_URL=\"http://localhost:8371\""

check_service "Notification Service" "8376"

echo -e "\n${BLUE}🔹 Starting API Gateway...${NC}"

# API Gateway (8370) - Central routing
start_service "api-gateway" "api-gateway" "8370" \
    "REDIS_URL=\"redis://localhost:6379\" USER_SERVICE_URL=\"http://localhost:8371\" POST_SERVICE_URL=\"http://localhost:8372\" GRAPH_SERVICE_URL=\"http://localhost:8373\" FANOUT_SERVICE_URL=\"http://localhost:8374\" NEWSFEED_SERVICE_URL=\"http://localhost:8375\" NOTIFICATION_SERVICE_URL=\"http://localhost:8376\""

check_service "API Gateway" "8370"

echo -e "\n${BLUE}🔹 Starting UI Service...${NC}"

# UI Service (3000) - React Frontend
echo -e "${YELLOW}🔧 Starting UI Service...${NC}"
cd "$SCRIPT_DIR/ui-service"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing UI dependencies...${NC}"
    npm install
fi

# Start UI service
PORT=3000 nohup npm start > "$LOG_DIR/ui-service.log" 2>&1 & echo $! > "$PID_DIR/ui-service.pid"

echo -e "${YELLOW}⏳ Waiting for UI Service to start on port 3000...${NC}"
sleep 10
echo -e "${GREEN}✅ UI Service started!${NC}"

cd "$SCRIPT_DIR"

echo -e "\n${BLUE}📋 Step 3: System Health Check...${NC}"

# Final health check
echo -e "${YELLOW}🏥 Performing comprehensive health check...${NC}"
sleep 2

services=(
    "API Gateway:8370"
    "User Service:8371" 
    "Post Service:8372"
    "Graph Service:8373"
    "Fanout Service:8374"
    "News Feed Service:8375"
    "Notification Service:8376"
)

all_healthy=true
for service_port in "${services[@]}"; do
    IFS=':' read -r service port <<< "$service_port"
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service (port $port): Healthy${NC}"
    else
        echo -e "${RED}❌ $service (port $port): Unhealthy${NC}"
        all_healthy=false
    fi
done

echo -e "\n${BLUE}========================================${NC}"
if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}🎉 News Feed System Started Successfully!${NC}"
    echo -e "${GREEN}✨ All 7 microservices are running${NC}"
    echo ""
    echo -e "${YELLOW}📡 Service Endpoints:${NC}"
    echo -e "   🌐 API Gateway:       http://localhost:8370"
    echo -e "   👤 User Service:      http://localhost:8371"
    echo -e "   📝 Post Service:      http://localhost:8372"
    echo -e "   🤝 Graph Service:     http://localhost:8373"
    echo -e "   📡 Fanout Service:    http://localhost:8374"
    echo -e "   📰 News Feed Service: http://localhost:8375"
    echo -e "   🔔 Notification Svc:  http://localhost:8376"
    echo -e "   🎨 UI Service:        http://localhost:3000"
    echo ""
    echo -e "${YELLOW}🧪 Test the system:${NC}"
    echo -e "   python test_ultimate_system.py"
    echo -e "   python test_api_gateway.py"
    echo ""
    echo -e "${YELLOW}📊 Monitor logs:${NC}"
    echo -e "   tail -f logs/*.log"
    echo ""
    echo -e "${YELLOW}🛑 Stop system:${NC}"
    echo -e "   ./stop_system.sh"
else
    echo -e "${RED}❌ Some services failed to start properly${NC}"
    echo -e "${RED}🔍 Check logs in: $LOG_DIR${NC}"
    exit 1
fi
echo -e "${BLUE}========================================${NC}"