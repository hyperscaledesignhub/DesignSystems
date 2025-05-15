#!/bin/bash

# Script to clean up Docker and Kubernetes resources to free up disk space

echo "Starting cleanup process..."

# Clean up Docker resources
echo "Cleaning up Docker resources..."
docker system prune -af --volumes

# Find and remove all Docker volumes
echo "Finding and removing all Docker volumes..."
docker volume ls -q | xargs -r docker volume rm

# Clean up Kubernetes resources (if Kind is used)
echo "Cleaning up Kubernetes resources..."
kind delete cluster

# Check disk usage after cleanup
echo "Checking disk usage after cleanup..."
df -h

# Check Docker disk usage
echo "Checking Docker disk usage..."
docker system df

echo "Cleanup completed!" 