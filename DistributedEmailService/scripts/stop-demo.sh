#!/bin/bash

# Distributed Email Service Demo - Cleanup Script
# This script stops all services and cleans up resources

set -e

echo "🛑 Stopping Distributed Email Service Demo"
echo "=========================================="

# Change to the demo directory
cd "$(dirname "$0")/.."

# Function to print colored output
print_status() {
    echo -e "\033[1;32m$1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m$1\033[0m"
}

# Ask for shutdown type
echo ""
echo "Choose shutdown option:"
echo "1) Stop containers only (preserve volumes and images)"
echo "2) Stop containers and remove volumes (but keep images)"
echo "3) Full cleanup (remove everything)"
echo ""
read -p "Select option (1/2/3) [1]: " -n 1 -r shutdown_option
echo
echo

# Set default to option 1 if nothing selected
if [[ -z "$shutdown_option" ]]; then
    shutdown_option="1"
fi

case $shutdown_option in
    1)
        print_status "🛑 Stopping containers only (preserving volumes and images)..."
        docker-compose stop
        print_status "✅ Containers stopped. Data preserved for quick restart."
        ;;
    2)
        print_status "🛑 Stopping containers and removing volumes..."
        docker-compose down --volumes --remove-orphans
        print_status "✅ Containers stopped and volumes removed. Images preserved."
        ;;
    3)
        print_status "🛑 Stopping containers and removing volumes..."
        docker-compose down --volumes --remove-orphans
        
        # Clean up Docker resources
        read -p "Would you like to clean up all Docker resources (images, networks)? (Y/n): " -n 1 -r cleanup_resources
        echo
        if [[ $cleanup_resources =~ ^[Yy]$ ]] || [[ -z "$cleanup_resources" ]]; then
            print_status "🧹 Cleaning up Docker resources..."
            
            # Remove demo images
            print_status "🗑️  Removing demo images..."
            docker images --filter=reference="demo-*" -q | xargs -r docker rmi -f 2>/dev/null || true
            
            # Remove unused volumes
            print_status "🗑️  Removing unused volumes..."
            docker volume prune -f
            
            # Remove unused networks
            print_status "🗑️  Removing unused networks..."
            docker network prune -f
            
            # Remove unused images
            print_status "🗑️  Removing unused images..."
            docker image prune -f
            
            print_status "✅ Full cleanup complete"
        else
            print_warning "⚠️  Docker resources preserved (containers stopped, volumes removed)"
        fi
        ;;
    *)
        print_warning "Invalid option. Stopping containers only..."
        docker-compose stop
        print_status "✅ Containers stopped. Data preserved."
        ;;
esac

echo ""
echo "✅ Demo cleanup complete!"
echo ""
echo "To restart the demo, run: ./scripts/start-demo.sh"