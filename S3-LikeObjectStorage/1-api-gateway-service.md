# 1. API Gateway Service

## Core Features (Minimal MVP)
- **Request Routing**: Route HTTP requests to appropriate microservices
- **Load Balancing**: Simple round-robin load balancing
- **Rate Limiting**: Basic rate limiting per client IP
- **Health Checks**: Monitor downstream service health

## APIs
```
GET  /health                     # Gateway health check
GET  /buckets                    # Route to bucket service
POST /buckets                    # Route to bucket service
PUT  /buckets/{bucket}/objects/{key}  # Route to object service
GET  /buckets/{bucket}/objects/{key}  # Route to object service
```

## Port Assignment
- **HTTP Port**: 7841
- **Management Port**: 7842

## Technology Stack
- **Language**: Python (FastAPI)
- **Dependencies**: fastapi, uvicorn, httpx

## Storage Requirements
- In-memory routing table
- No persistent storage needed

## Deployment
- Kubernetes Service (LoadBalancer type)
- 2-3 replicas for HA
- Resource limits: 256Mi memory, 200m CPU