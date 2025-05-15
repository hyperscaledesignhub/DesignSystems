#!/bin/bash

# Delete existing cluster if it exists
kind delete cluster

# Create new cluster
kind create cluster --config kind-config.yaml

# Load the image into kind
kind load docker-image rate-limiter:latest

# Create namespace
kubectl create namespace rate-limiter

# Deploy Redis
kubectl apply -f  redis.yaml

# Wait for Redis to be ready
kubectl wait --namespace rate-limiter \
  --for=condition=ready pod \
  --selector=app=redis \
  --timeout=90s

# Deploy rate limiter
kubectl apply -f deployment-local.yaml

# Wait for rate limiter to be ready
kubectl wait --namespace rate-limiter \
  --for=condition=ready pod \
  --selector=app=rate-limiter \
  --timeout=90s

# Show pod distribution
kubectl get pods -n rate-limiter -o wide

# Get the service URL
echo "Rate limiter is available at: http://localhost/api/limited" 