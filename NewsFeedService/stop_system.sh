#!/bin/bash

# News Feed System - Stop Script
# This script stops all microservices gracefully

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/pids"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🛑 News Feed System - Stop Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/$service_name.pid"
    local worker_pid_file="$PID_DIR/$service_name-worker.pid"
    
    # Stop main service
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🔧 Stopping $service_name (PID: $pid)...${NC}"
            kill -TERM "$pid" 2>/dev/null
            
            # Wait for graceful shutdown
            local timeout=10
            while [ $timeout -gt 0 ] && kill -0 "$pid" 2>/dev/null; do
                sleep 1
                ((timeout--))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${RED}⚠️  Force killing $service_name...${NC}"
                kill -KILL "$pid" 2>/dev/null
            fi
            
            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠️  No PID file for $service_name${NC}"
    fi
    
    # Stop worker if exists
    if [ -f "$worker_pid_file" ]; then
        local worker_pid=$(cat "$worker_pid_file")
        if kill -0 "$worker_pid" 2>/dev/null; then
            echo -e "${YELLOW}🔧 Stopping $service_name worker (PID: $worker_pid)...${NC}"
            kill -TERM "$worker_pid" 2>/dev/null
            
            # Wait for graceful shutdown
            local timeout=10
            while [ $timeout -gt 0 ] && kill -0 "$worker_pid" 2>/dev/null; do
                sleep 1
                ((timeout--))
            done
            
            # Force kill if still running
            if kill -0 "$worker_pid" 2>/dev/null; then
                echo -e "${RED}⚠️  Force killing $service_name worker...${NC}"
                kill -KILL "$worker_pid" 2>/dev/null
            fi
            
            echo -e "${GREEN}✅ $service_name worker stopped${NC}"
        fi
        rm -f "$worker_pid_file"
    fi
}

echo -e "${YELLOW}🛑 Stopping all microservices...${NC}"

# Stop services in reverse dependency order
services=(
    "ui-service"
    "api-gateway"
    "notification-service"
    "newsfeed-service"
    "fanout-service"
    "post-service"
    "graph-service"
    "user-service"
)

for service in "${services[@]}"; do
    stop_service "$service"
done

echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"

# Kill any remaining processes on our ports (including UI service)
ports=(3000 8370 8371 8372 8373 8374 8375 8376)
for port in "${ports[@]}"; do
    pids=$(lsof -ti tcp:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}🔧 Killing remaining processes on port $port...${NC}"
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 1
        # Force kill if still there
        remaining_pids=$(lsof -ti tcp:$port 2>/dev/null || true)
        if [ -n "$remaining_pids" ]; then
            echo "$remaining_pids" | xargs kill -KILL 2>/dev/null || true
        fi
    fi
done

# Kill any remaining Celery workers
celery_pids=$(pgrep -f "celery.*worker" 2>/dev/null || true)
if [ -n "$celery_pids" ]; then
    echo -e "${YELLOW}🔧 Stopping remaining Celery workers...${NC}"
    echo "$celery_pids" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    # Force kill remaining
    remaining_celery=$(pgrep -f "celery.*worker" 2>/dev/null || true)
    if [ -n "$remaining_celery" ]; then
        echo "$remaining_celery" | xargs kill -KILL 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ Celery workers stopped${NC}"
fi

# Clean up PID directory
if [ -d "$PID_DIR" ]; then
    rm -f "$PID_DIR"/*.pid 2>/dev/null || true
fi

echo -e "\n${BLUE}🔍 Final verification...${NC}"

# Check if any services are still running
still_running=false
service_ports=(
    "UI Service:3000"
    "API Gateway:8370"
    "User Service:8371"
    "Post Service:8372" 
    "Graph Service:8373"
    "Fanout Service:8374"
    "News Feed Service:8375"
    "Notification Service:8376"
)

for service_port in "${service_ports[@]}"; do
    IFS=':' read -r service port <<< "$service_port"
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "${RED}⚠️  $service (port $port): Still responding${NC}"
        still_running=true
    else
        echo -e "${GREEN}✅ $service (port $port): Stopped${NC}"
    fi
done

echo -e "\n${BLUE}========================================${NC}"
if [ "$still_running" = false ]; then
    echo -e "${GREEN}🎉 All News Feed services stopped successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📊 System Status:${NC}"
    echo -e "   🛑 All 7 microservices: Stopped"
    echo -e "   📂 Log files preserved in: logs/"
    echo -e "   🧹 PID files cleaned up"
    echo ""
    echo -e "${YELLOW}🔄 To restart the system:${NC}"
    echo -e "   ./start_system.sh"
    echo ""
    echo -e "${YELLOW}📋 Docker containers (if you want to stop them):${NC}"
    echo -e "   docker stop postgres-newsfeed redis-newsfeed rabbitmq-newsfeed"
else
    echo -e "${RED}⚠️  Some services are still running${NC}"
    echo -e "${RED}🔍 You may need to manually kill remaining processes${NC}"
    echo ""
    echo -e "${YELLOW}💡 To check what's still running on our ports:${NC}"
    echo -e "   lsof -i :8370-8376"
fi
echo -e "${BLUE}========================================${NC}"