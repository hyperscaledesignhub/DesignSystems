#!/bin/bash

# News Feed System - Dependencies Setup Script
# This script sets up Docker containers for PostgreSQL, Redis, and RabbitMQ

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🐳 News Feed System - Dependencies Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

# Function to setup a container
setup_container() {
    local name=$1
    local image=$2
    local ports=$3
    local env_vars=$4
    local extra_args=$5
    
    echo -e "${YELLOW}🔧 Setting up $name...${NC}"
    
    # Stop and remove existing container if it exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${name}$"; then
        echo -e "${YELLOW}   Removing existing $name container...${NC}"
        docker stop "$name" >/dev/null 2>&1 || true
        docker rm "$name" >/dev/null 2>&1 || true
    fi
    
    # Start new container
    eval "docker run -d --name $name $ports $env_vars $extra_args $image"
    
    # Check if container started successfully
    if docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        echo -e "${GREEN}✅ $name started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start $name${NC}"
        exit 1
    fi
}

# Check Docker
check_docker

echo -e "\n${YELLOW}📦 Setting up database and messaging infrastructure...${NC}"

# PostgreSQL - Main database
setup_container "postgres-newsfeed" "postgres:15" \
    "-p 5432:5432" \
    "-e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=postgres"

# Redis - Caching and session storage
setup_container "redis-newsfeed" "redis:7-alpine" \
    "-p 6379:6379" \
    ""

# RabbitMQ - Message queue for async processing
setup_container "rabbitmq-newsfeed" "rabbitmq:3-management-alpine" \
    "-p 5672:5672 -p 15672:15672" \
    "-e RABBITMQ_DEFAULT_USER=guest -e RABBITMQ_DEFAULT_PASS=guest"

echo -e "\n${BLUE}⏳ Waiting for services to be ready...${NC}"

# Wait for PostgreSQL
echo -e "${YELLOW}🔍 Waiting for PostgreSQL...${NC}"
timeout=30
while [ $timeout -gt 0 ]; do
    if docker exec postgres-newsfeed pg_isready -U user >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo -e "${RED}❌ PostgreSQL failed to start within 30 seconds${NC}"
    exit 1
fi

# Wait for Redis
echo -e "${YELLOW}🔍 Waiting for Redis...${NC}"
timeout=30
while [ $timeout -gt 0 ]; do
    if docker exec redis-newsfeed redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is ready${NC}"
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo -e "${RED}❌ Redis failed to start within 30 seconds${NC}"
    exit 1
fi

# Wait for RabbitMQ
echo -e "${YELLOW}🔍 Waiting for RabbitMQ...${NC}"
timeout=60
while [ $timeout -gt 0 ]; do
    if docker exec rabbitmq-newsfeed rabbitmq-diagnostics -q ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ RabbitMQ is ready${NC}"
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo -e "${RED}❌ RabbitMQ failed to start within 60 seconds${NC}"
    exit 1
fi

echo -e "\n${BLUE}🗄️  Setting up databases...${NC}"

# Create databases
databases=("userdb" "postdb" "graphdb" "notificationdb")
for db in "${databases[@]}"; do
    echo -e "${YELLOW}📊 Creating database: $db${NC}"
    if docker exec postgres-newsfeed psql -U user -d postgres -c "CREATE DATABASE $db;" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Database $db created${NC}"
    else
        echo -e "${YELLOW}⚠️  Database $db already exists${NC}"
    fi
done

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}🎉 Dependencies Setup Complete!${NC}"
echo -e "${GREEN}✨ All infrastructure services are ready${NC}"
echo ""
echo -e "${YELLOW}📊 Infrastructure Status:${NC}"
echo -e "   🐘 PostgreSQL:  localhost:5432 (user/password)"
echo -e "   🔴 Redis:       localhost:6379"
echo -e "   🐰 RabbitMQ:    localhost:5672"
echo -e "   📊 RabbitMQ UI: http://localhost:15672 (guest/guest)"
echo ""
echo -e "${YELLOW}🗄️  Databases Created:${NC}"
echo -e "   • userdb (User Service)"
echo -e "   • postdb (Post Service)"  
echo -e "   • graphdb (Graph Service)"
echo -e "   • notificationdb (Notification Service)"
echo ""
echo -e "${YELLOW}▶️  Next Steps:${NC}"
echo -e "   1. Install Python dependencies: pip install -r requirements.txt"
echo -e "   2. Start the system: ./start_system.sh"
echo -e "   3. Test the system: python test_ultimate_system.py"
echo ""
echo -e "${YELLOW}🛑 To stop dependencies later:${NC}"
echo -e "   docker stop postgres-newsfeed redis-newsfeed rabbitmq-newsfeed"
echo -e "   docker rm postgres-newsfeed redis-newsfeed rabbitmq-newsfeed"
echo -e "${BLUE}========================================${NC}"