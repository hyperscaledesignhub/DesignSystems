#!/bin/bash

echo "🐳 Building Google Maps Clone - Docker Images for All Services"
echo "=============================================================="

# Create Docker network if it doesn't exist
docker network create maps-network 2>/dev/null || echo "Network 'maps-network' already exists"

# Build base image
echo "📦 Building base Google Maps Clone image..."
docker build -t google-maps-clone:latest .

# Build specialized images for each service
echo "🚀 Building API Gateway image..."
docker build -t maps-api-gateway:latest \
  --build-arg SERVICE_FILE=simple_api.py \
  --build-arg SERVICE_PORT=8080 .

echo "🗺️ Building Navigation Service image..."
docker build -t maps-navigation:latest \
  --build-arg SERVICE_FILE=navigation_service.py \
  --build-arg SERVICE_PORT=8081 .

echo "🤖 Building AI/ML Service image..."
docker build -t maps-ai-ml:latest \
  --build-arg SERVICE_FILE=ai_ml_service.py \
  --build-arg SERVICE_PORT=8082 .

echo "🏢 Building Places & Business Service image..."
docker build -t maps-places:latest \
  --build-arg SERVICE_FILE=places_business_service.py \
  --build-arg SERVICE_PORT=8083 .

echo "🚦 Building Traffic & Real-Time Service image..."
docker build -t maps-traffic:latest \
  --build-arg SERVICE_FILE=traffic_realtime_service.py \
  --build-arg SERVICE_PORT=8084 .

echo "🗺️ Building Maps & Visualization Service image..."
docker build -t maps-visualization:latest \
  --build-arg SERVICE_FILE=maps_visualization_service.py \
  --build-arg SERVICE_PORT=8085 .

echo "🌐 Building Web UI Service image..."
docker build -f Dockerfile.ui -t maps-web-ui:latest .

echo "✅ All Docker images built successfully!"
echo ""
echo "📋 Available images:"
echo "   - google-maps-clone:latest (base)"
echo "   - maps-api-gateway:latest"
echo "   - maps-navigation:latest"
echo "   - maps-ai-ml:latest"
echo "   - maps-places:latest"
echo "   - maps-traffic:latest"
echo "   - maps-visualization:latest"
echo "   - maps-web-ui:latest"
echo ""
echo "🚀 Use 'run-docker-services.sh' to start all services"