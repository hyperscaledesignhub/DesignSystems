#!/bin/bash

# Build all Docker images for S3 microservices
set -e

echo "Building S3 Storage System Docker Images..."

SERVICES=("api-gateway" "identity" "bucket" "object" "storage" "metadata")
BASE_DIR="$(dirname "$0")/../services"

for service in "${SERVICES[@]}"; do
    echo "Building s3-$service-service:latest..."
    docker build -t "s3-$service-service:latest" "$BASE_DIR/$service/"
    echo "✅ Built s3-$service-service:latest"
done

echo "🎉 All Docker images built successfully!"
echo ""
echo "Built images:"
docker images | grep "s3-.*-service"