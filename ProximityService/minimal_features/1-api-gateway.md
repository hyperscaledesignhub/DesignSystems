# API Gateway Service - Minimal Features

## Core Features
- Load balancing across services
- Request routing based on URL paths
- Rate limiting (1000 requests/minute per IP)
- Health checks for upstream services

## Endpoints
- `/api/v1/search/nearby` → Location Service
- `/api/v1/businesses/*` → Business Service

## Port Configuration
- External: 7891 (HTTP)
- Internal: 7892 (gRPC)

## Technologies
- Python (FastAPI)
- Nginx for reverse proxy
- Redis for rate limiting

## Resource Requirements
- CPU: 500m
- Memory: 512Mi
- Replicas: 3 minimum