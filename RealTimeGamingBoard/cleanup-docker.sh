#!/bin/bash

# Gaming Leaderboard Demo - Cleanup Script
# This script removes all docker containers, images, volumes, and networks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_question() {
    echo -e "${YELLOW}[?]${NC} $1"
}

# Main script
echo "============================================"
echo "   Gaming Leaderboard Demo - Cleanup"
echo "============================================"
echo ""

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed."
    exit 1
fi

# Ask for confirmation
print_question "This will remove all Gaming Leaderboard demo resources."
print_warning "This includes: containers, images, volumes, and networks"
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleanup cancelled."
    exit 0
fi

echo ""

# Stop all running containers
print_status "Stopping all containers..."
docker-compose down 2>/dev/null || print_warning "No containers to stop"

# Remove all containers (including stopped ones)
print_status "Removing containers..."
containers=$(docker ps -a --filter "name=demo-" --format "{{.ID}}" 2>/dev/null)
if [ -n "$containers" ]; then
    docker rm -f $containers 2>/dev/null || true
    print_success "Containers removed"
else
    print_status "No containers to remove"
fi

# Remove all images
print_status "Removing images..."
images=$(docker images --filter "reference=demo-*" --format "{{.ID}}" 2>/dev/null)
if [ -n "$images" ]; then
    docker rmi -f $images 2>/dev/null || true
fi

# Remove images with specific service names
service_images=$(docker images | grep -E "user-service|tournament-service|websocket-service|api-gateway|demo-generator|simple-gateway|leaderboard|gaming" | awk '{print $3}' 2>/dev/null || true)
if [ -n "$service_images" ]; then
    echo "$service_images" | xargs -r docker rmi -f 2>/dev/null || true
fi
print_success "Images removed"

# Remove volumes
print_status "Removing volumes..."
volumes=$(docker volume ls --filter "name=demo_" --format "{{.Name}}" 2>/dev/null)
if [ -n "$volumes" ]; then
    docker volume rm $volumes 2>/dev/null || true
    print_success "Volumes removed"
else
    print_status "No volumes to remove"
fi

# Remove networks
print_status "Removing networks..."
networks=$(docker network ls --filter "name=demo_" --format "{{.Name}}" 2>/dev/null)
if [ -n "$networks" ]; then
    docker network rm $networks 2>/dev/null || true
    print_success "Networks removed"
else
    print_status "No networks to remove"
fi

# Clean up dangling images
print_status "Cleaning up dangling images..."
docker image prune -f > /dev/null 2>&1 || true

# Clean up build cache (optional)
print_question "Do you want to clear Docker build cache? This will free up space but slow next build (y/N): "
read -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Clearing build cache..."
    docker builder prune -f > /dev/null 2>&1 || true
    print_success "Build cache cleared"
fi

# Display cleanup summary
echo ""
echo "============================================"
echo "   Cleanup Summary"
echo "============================================"

# Check what's left
remaining_containers=$(docker ps -a --filter "name=demo-" --format "{{.Names}}" 2>/dev/null | wc -l)
remaining_images=$(docker images | grep -E "demo-|gaming|leaderboard" 2>/dev/null | wc -l || echo "0")
remaining_volumes=$(docker volume ls --filter "name=demo_" --format "{{.Name}}" 2>/dev/null | wc -l)
remaining_networks=$(docker network ls --filter "name=demo_" --format "{{.Name}}" 2>/dev/null | wc -l)

if [ "$remaining_containers" -eq 0 ] && [ "$remaining_images" -eq 0 ] && [ "$remaining_volumes" -eq 0 ] && [ "$remaining_networks" -eq 0 ]; then
    print_success "All Gaming Leaderboard demo resources have been removed!"
else
    print_warning "Some resources may still exist:"
    [ "$remaining_containers" -gt 0 ] && echo "  - Containers: $remaining_containers"
    [ "$remaining_images" -gt 0 ] && echo "  - Images: $remaining_images"
    [ "$remaining_volumes" -gt 0 ] && echo "  - Volumes: $remaining_volumes"  
    [ "$remaining_networks" -gt 0 ] && echo "  - Networks: $remaining_networks"
    echo ""
    print_status "Run 'docker system prune -a' for a complete Docker cleanup"
fi

# Display disk space saved
echo ""
print_status "Checking disk space..."
docker system df

echo ""
echo "============================================"
print_success "Cleanup completed!"
echo ""
echo "To start the demo again, run: ./startup.sh"
echo "============================================"