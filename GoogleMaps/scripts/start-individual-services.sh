#!/bin/bash

SERVICE=$1
PORT_MAP=""

if [[ -z "$SERVICE" ]]; then
    echo "Usage: $0 <service_name>"
    echo "Available services: location, navigation, places, traffic, ui"
    exit 1
fi

echo "🐳 Starting $SERVICE service..."

case $SERVICE in
    "location")
        docker build -f Dockerfile.location -t location-service .
        docker run -d --name location-service --network maps-network -p 8086:8086 location-service
        echo "✅ Location service started on port 8086"
        ;;
    "navigation") 
        docker build -f Dockerfile.navigation -t navigation-service .
        docker run -d --name navigation-service --network maps-network -p 8081:8081 navigation-service
        echo "✅ Navigation service started on port 8081"
        ;;
    "places")
        docker build -f Dockerfile.places -t places-service .
        docker run -d --name places-service --network maps-network -p 8080:8080 places-service
        echo "✅ Places service started on port 8080"
        ;;
    "traffic")
        docker build -f Dockerfile.traffic -t traffic-service .
        docker run -d --name traffic-service --network maps-network -p 8084:8084 traffic-service
        echo "✅ Traffic service started on port 8084"
        ;;
    "ui")
        echo "🖥️  Starting UI (non-Docker)..."
        cd ui && python maps_ui.py &
        echo "✅ UI started on port 3002"
        ;;
    *)
        echo "❌ Unknown service: $SERVICE"
        echo "Available services: location, navigation, places, traffic, ui"
        exit 1
        ;;
esac
