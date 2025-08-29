#!/bin/bash

# Distributed Email Service Demo - Startup Script
# This script starts all microservices with distributed tracing
# Usage: ./start-demo.sh [--skip-cleanup]

set -e

echo "🚀 Starting Distributed Email Service Demo"
echo "========================================="

# Change to the demo directory
cd "$(dirname "$0")/.."

# Parse command line arguments
SKIP_CLEANUP=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-cleanup]"
            exit 1
            ;;
    esac
done

# Function to print colored output
print_status() {
    echo -e "\033[1;32m$1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m$1\033[0m"
}

print_error() {
    echo -e "\033[1;31m$1\033[0m"
}

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    print_error "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Clean up any existing containers and resources
if [ "$SKIP_CLEANUP" = false ]; then
    print_status "🧹 Cleaning up existing Docker resources..."
    docker-compose down --volumes --remove-orphans 2>/dev/null || true
    docker system prune -f --volumes 2>/dev/null || true

    # Remove any dangling images
    print_status "🗑️  Removing dangling images..."
    docker image prune -f 2>/dev/null || true
else
    print_warning "⚠️  Skipping Docker cleanup (--skip-cleanup option used)"
fi

# Build all services
if [ "$SKIP_CLEANUP" = false ]; then
    print_status "🔨 Building all services..."
    docker-compose build --no-cache
else
    print_status "🔨 Building services (using cache)..."
    docker-compose build
fi

# Start infrastructure services first
print_status "🏗️  Starting infrastructure services..."
docker-compose up -d postgres redis elasticsearch minio jaeger

# Wait for infrastructure services to be ready
print_status "⏳ Waiting for infrastructure services to be ready..."
sleep 10

# Check infrastructure health
print_status "🔍 Checking infrastructure health..."

# Wait for PostgreSQL
until docker-compose exec -T postgres pg_isready -U emailuser -d emaildb > /dev/null 2>&1; do
    print_warning "Waiting for PostgreSQL..."
    sleep 2
done
print_status "✅ PostgreSQL is ready"

# Wait for Redis
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    print_warning "Waiting for Redis..."
    sleep 2
done
print_status "✅ Redis is ready"

# Wait for Elasticsearch
until curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; do
    print_warning "Waiting for Elasticsearch..."
    sleep 2
done
print_status "✅ Elasticsearch is ready"

# Wait for MinIO
until curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    print_warning "Waiting for MinIO..."
    sleep 2
done
print_status "✅ MinIO is ready"

print_status "✅ Jaeger is ready"

# Start application services
print_status "🚀 Starting application services..."
docker-compose up -d

# Wait for all services to be ready
print_status "⏳ Waiting for all services to be ready..."
sleep 15

# Check service health
print_status "🔍 Checking service health..."

services=("auth-service:8001" "email-service:8002" "spam-service:8003" "notification-service:8004" "attachment-service:8005" "search-service:8006" "api-gateway:8000")

for service in "${services[@]}"; do
    service_name=${service%:*}
    service_port=${service#*:}
    
    for i in {1..30}; do
        if curl -s http://localhost:${service_port}/health > /dev/null 2>&1; then
            print_status "✅ ${service_name} is healthy"
            break
        elif [ $i -eq 30 ]; then
            print_error "❌ ${service_name} failed to start"
            docker-compose logs ${service_name}
        else
            print_warning "⏳ Waiting for ${service_name}..."
            sleep 2
        fi
    done
done

# Create demo user and data
print_status "👤 Creating demo user and sample data..."
sleep 5

# Register demo user
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "password",
    "full_name": "Demo User",
    "role": "user"
  }' > /dev/null 2>&1 && print_status "✅ Demo user created" || print_warning "⚠️  Demo user may already exist"

# Create sample emails
print_status "📧 Creating sample emails..."
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "password"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ ! -z "$TOKEN" ]; then
    # Sample email 1
    curl -s -X POST http://localhost:8000/emails \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "to_recipients": ["demo@example.com"],
        "subject": "Welcome to the Distributed Email Service Demo",
        "body": "This is a demonstration of a distributed email system with microservices architecture and distributed tracing. All services are instrumented with OpenTelemetry and traces can be viewed in Jaeger UI.",
        "priority": "high",
        "labels": ["demo", "welcome"]
      }' > /dev/null 2>&1 && print_status "✅ Welcome email created"

    # Sample email 2
    curl -s -X POST http://localhost:8000/emails \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "to_recipients": ["demo@example.com"],
        "subject": "Distributed Architecture Overview",
        "body": "This system demonstrates various microservice patterns:\n\n1. API Gateway - Request routing\n2. Service Discovery - Health checks\n3. Distributed Tracing - OpenTelemetry + Jaeger\n4. Event-driven Architecture - Notifications\n5. Data Storage - PostgreSQL, Redis, Elasticsearch, MinIO\n\nExplore the different features to see how the services interact!",
        "priority": "normal",
        "labels": ["architecture", "info"]
      }' > /dev/null 2>&1 && print_status "✅ Architecture email created"

    # Sample spam email
    curl -s -X POST http://localhost:8000/emails \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "to_recipients": ["demo@example.com"],
        "subject": "URGENT!!! You have won $1000000!!!",
        "body": "Congratulations! You are the winner of our lottery! Click here to claim your prize now! Limited time offer! Act fast! 100% guaranteed! Free money! No risk!",
        "priority": "urgent",
        "labels": ["suspicious"]
      }' > /dev/null 2>&1 && print_status "✅ Sample spam email created (will be detected by spam service)"
else
    print_warning "⚠️  Could not create sample emails (authentication failed)"
fi

# Display final status
echo ""
echo "🎉 Demo is ready!"
echo "=================="
echo ""
echo "🌐 Access Points:"
echo "• Main UI: http://localhost:3000"
echo "• API Gateway: http://localhost:8000"
echo "• Jaeger Tracing: http://localhost:16686"
echo "• MinIO Console: http://localhost:9001 (minioaccess/miniosecret)"
echo "• Elasticsearch: http://localhost:9200"
echo ""
echo "👤 Demo Credentials:"
echo "• Email: demo@example.com"
echo "• Password: password"
echo ""
echo "🔧 Individual Services:"
echo "• Auth Service: http://localhost:8001/docs"
echo "• Email Service: http://localhost:8002/docs"
echo "• Spam Service: http://localhost:8003/docs"
echo "• Notification Service: http://localhost:8004/docs"
echo "• Attachment Service: http://localhost:8005/docs"
echo "• Search Service: http://localhost:8006/docs"
echo ""
echo "📊 To view distributed traces:"
echo "1. Open Jaeger UI: http://localhost:16686"
echo "2. Use the demo application to generate traces"
echo "3. Search for traces by service name"
echo ""
echo "🛑 To stop the demo: ./scripts/stop-demo.sh"
echo ""

# Monitor logs (optional)
read -p "Would you like to monitor service logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "📋 Monitoring service logs (Ctrl+C to exit)..."
    docker-compose logs -f --tail=50
fi