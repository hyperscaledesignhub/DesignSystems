# Proximity Service Demo 🏢📍

A complete microservices-based proximity service (like Yelp) demonstrating high availability architecture with database replication, Redis caching, and failover capabilities.

## Architecture

The system consists of 6 microservices:

1. **API Gateway** (Port 7891) - Load balancing and request routing
2. **Location Service** (Port 8921) - Core proximity search using geohash
3. **Business Service** (Port 9823) - Business CRUD operations
4. **Database Service** (Port 5832) - PostgreSQL with spatial indexing
5. **Cache Service** (Port 6739) - Redis for geohash and business caching
6. **Monitoring Service** (Port 9290) - Prometheus metrics collection

## Core Features

- Find businesses within radius (0.5km, 1km, 2km, 5km)
- Geohash-based spatial indexing (precision 4-6)
- Business CRUD operations with automatic cache updates
- Rate limiting (1000 requests/minute per IP)
- Health checks and monitoring

## Quick Start 🚀

### Complete Demo (Backend + UI)
```bash
# Start everything
./start-full-demo.sh

# Stop everything  
./stop-full-demo.sh
```

### Separate Control
```bash
# Backend services only
./start-demo.sh
./stop-demo.sh

# UI server only (run after backend is started)
./start-ui.sh
./stop-ui.sh
```

## Demo URLs 🌐

- **Demo UI**: http://localhost:8081
- **API Gateway**: http://localhost:7891/api/v1/*
- **Location Service**: http://localhost:8921
- **Business Service**: http://localhost:9823

### Using Kubernetes (Production)

```bash
# Create namespace
kubectl apply -f deployments/namespace.yaml

# Deploy database and cache
kubectl apply -f deployments/postgres.yaml
kubectl apply -f deployments/redis.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres-primary -n proximity-service --timeout=300s

# Deploy services
kubectl apply -f deployments/business-service.yaml
kubectl apply -f deployments/location-service.yaml
kubectl apply -f deployments/api-gateway.yaml

# Deploy cache warmer and monitoring
kubectl apply -f deployments/cache-warmer.yaml
kubectl apply -f deployments/monitoring.yaml

# Get external IP
kubectl get service api-gateway -n proximity-service
```

## API Endpoints

### Search Nearby Businesses
```
GET /api/v1/search/nearby?latitude={lat}&longitude={lng}&radius={meters}
```

### Business Management
```
GET /api/v1/businesses/{id}     # Get business details
POST /api/v1/businesses         # Create business
PUT /api/v1/businesses/{id}     # Update business  
DELETE /api/v1/businesses/{id}  # Delete business
```

## Port Configuration

All services use non-standard ports to avoid conflicts:

- API Gateway: 7891 (HTTP), 7892 (gRPC)
- Location Service: 8921 (HTTP), 8922 (Metrics)
- Business Service: 9823 (HTTP), 9824 (Admin)
- Database: 5832 (PostgreSQL)
- Cache: 6739 (Redis)
- Monitoring: 9290 (Prometheus), 3200 (Grafana)

## Technology Stack

- **Languages**: Python 3.11
- **Frameworks**: FastAPI, uvicorn
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Orchestration**: Kubernetes, Docker Compose
- **Monitoring**: Prometheus

## Scaling

- Location Service: 5 replicas (read-heavy)
- API Gateway: 3 replicas  
- Business Service: 3 replicas
- Database: Primary-replica setup
- Cache: 3-node Redis cluster

## Features Skipped (see minimal_features/skipped-features.md)

- Advanced search filters
- User authentication
- Machine learning ranking
- Real-time updates
- Advanced monitoring
- Multi-region deployment

## Development

Each service is containerized with its own Dockerfile and requirements.txt. The system is designed for easy horizontal scaling and cloud deployment.