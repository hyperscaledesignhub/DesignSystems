#!/bin/bash

echo "Stopping and removing all service containers..."

# List of all container names
CONTAINERS=(
  "demo-jaeger-1"
  "demo-postgres-payment-1"
  "demo-postgres-ledger-1"
  "demo-postgres-wallet-1"
  "demo-postgres-fraud-1"
  "demo-postgres-reconciliation-1"
  "demo-postgres-notification-1"
  "demo-redis-payment-1"
  "demo-redis-wallet-1"
  "demo-redis-fraud-1"
  "demo-rabbitmq-1"
  "demo-payment-service-1"
  "demo-payment-executor-1"
  "demo-ledger-service-1"
  "demo-psp-gateway-1"
  "demo-api-gateway-1"
  "demo-wallet-service-1"
  "demo-reconciliation-service-1"
  "demo-fraud-detection-service-1"
  "demo-notification-service-1"
)

# Stop and remove each container
for container in "${CONTAINERS[@]}"; do
  if docker ps -a | grep -q "$container"; then
    echo "Stopping $container..."
    docker stop "$container" 2>/dev/null
    docker rm "$container" 2>/dev/null
  fi
done

echo ""
echo "All service containers stopped and removed."
echo "Note: Docker volumes are preserved for data persistence."
echo "To remove volumes as well, run: docker volume prune"