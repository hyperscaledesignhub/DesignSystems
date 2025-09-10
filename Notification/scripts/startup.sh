#!/bin/bash

# Notification System Demo - Startup Script
# This script starts all services as individual Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Notification System Demo${NC}"
echo "======================================="

# Create network if it doesn't exist
echo -e "${YELLOW}Creating Docker network...${NC}"
docker network create notification-network 2>/dev/null || echo "Network already exists"

# Start Redis
echo -e "${YELLOW}Starting Redis...${NC}"
docker run -d \
  --name redis-service \
  --network notification-network \
  -p 7847:6379 \
  redis:7-alpine \
  redis-server --port 6379

# Wait for Redis to be ready
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
sleep 5
until docker exec redis-service redis-cli ping | grep PONG; do
  sleep 1
done
echo -e "${GREEN}Redis is ready!${NC}"

# Build and start User Database
echo -e "${YELLOW}Building and starting User Database...${NC}"
docker build --no-cache -t user-database ../services/user-database/
docker run -d \
  --name user-database \
  --network notification-network \
  -p 7846:7846 \
  -e PORT=7846 \
  -v $(pwd)/../data/sqlite:/app/data \
  user-database

# Wait for User Database to be ready
echo -e "${YELLOW}Waiting for User Database to be ready...${NC}"
sleep 3

# Build and start Notification Server
echo -e "${YELLOW}Building and starting Notification Server...${NC}"
docker build --no-cache -t notification-server ../services/notification-server/
docker run -d \
  --name notification-server \
  --network notification-network \
  -p 7842:7842 \
  -e PORT=7842 \
  -e REDIS_HOST=redis-service \
  -e REDIS_PORT=6379 \
  -e USER_DB_URL=http://user-database:7846 \
  notification-server

# Wait for Notification Server to be ready
echo -e "${YELLOW}Waiting for Notification Server to be ready...${NC}"
sleep 5

# Build and start API Gateway
echo -e "${YELLOW}Building and starting API Gateway...${NC}"
docker build --no-cache -t api-gateway ../services/api-gateway/
docker run -d \
  --name api-gateway \
  --network notification-network \
  -p 7841:7841 \
  -e PORT=7841 \
  -e NOTIFICATION_SERVER_URL=http://notification-server:7842 \
  api-gateway

# Build and start Email Worker
echo -e "${YELLOW}Building and starting Email Worker...${NC}"
docker build --no-cache -t email-worker ../services/email-worker/
docker run -d \
  --name email-worker \
  --network notification-network \
  -p 7843:7843 \
  -e PORT=7843 \
  -e REDIS_HOST=redis-service \
  -e REDIS_PORT=6379 \
  -e SMTP_HOST=${SMTP_HOST:-smtp.gmail.com} \
  -e SMTP_PORT=${SMTP_PORT:-587} \
  -e SMTP_USERNAME=${SMTP_USERNAME:-} \
  -e SMTP_PASSWORD=${SMTP_PASSWORD:-} \
  email-worker

# Build and start SMS Worker
echo -e "${YELLOW}Building and starting SMS Worker...${NC}"
docker build --no-cache -t sms-worker ../services/sms-worker/
docker run -d \
  --name sms-worker \
  --network notification-network \
  -p 7844:7844 \
  -e PORT=7844 \
  -e REDIS_HOST=redis-service \
  -e REDIS_PORT=6379 \
  -e SMS_API_URL=${SMS_API_URL:-https://api.twilio.com} \
  -e SMS_API_KEY=${SMS_API_KEY:-} \
  -e SMS_API_SECRET=${SMS_API_SECRET:-} \
  sms-worker

# Build and start Push Worker
echo -e "${YELLOW}Building and starting Push Worker...${NC}"
docker build --no-cache -t push-worker ../services/push-worker/
docker run -d \
  --name push-worker \
  --network notification-network \
  -p 7845:7845 \
  -e PORT=7845 \
  -e REDIS_HOST=redis-service \
  -e REDIS_PORT=6379 \
  -e USER_DB_URL=http://user-database:7846 \
  -e FCM_SERVER_KEY=${FCM_SERVER_KEY:-} \
  -e FCM_API_URL=${FCM_API_URL:-https://fcm.googleapis.com/fcm/send} \
  push-worker

echo -e "${GREEN}✅ All services started successfully!${NC}"
echo ""
echo "Service Status:"
echo "---------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(redis-service|user-database|notification-server|api-gateway|email-worker|sms-worker|push-worker|NAMES)"

echo ""
echo -e "${GREEN}Service URLs:${NC}"
echo "  API Gateway:        http://localhost:7841"
echo "  Notification Server: http://localhost:7842"
echo "  User Database:      http://localhost:7846"
echo "  Email Worker:       http://localhost:7843/health"
echo "  SMS Worker:         http://localhost:7844/health"
echo "  Push Worker:        http://localhost:7845/health"
echo "  Redis:              localhost:7847"
echo ""
echo -e "${YELLOW}Starting UI service (non-Docker)...${NC}"

# Start UI service (as a separate process, not in Docker)
cd ../ui
if [ -f "package.json" ]; then
  npm install
  npm run dev &
  UI_PID=$!
  echo $UI_PID > ../scripts/ui.pid
  echo -e "${GREEN}✅ UI service started (PID: $UI_PID)${NC}"
  echo "  UI:                 http://localhost:3000"
else
  echo -e "${RED}UI not found. Please run 'npm init' in the ui directory first.${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Notification System Demo is ready!${NC}"
echo "Use ./stop.sh to stop all services"