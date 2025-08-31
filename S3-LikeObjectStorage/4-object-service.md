# 4. Object Service

## Core Features (Minimal MVP)
- **Upload Object**: Store object data with metadata
- **Download Object**: Retrieve object by bucket/key
- **Delete Object**: Remove object from bucket
- **List Objects**: List objects in bucket with prefix support

## APIs
```
PUT  /buckets/{bucket}/objects/{key}     # Upload object
GET  /buckets/{bucket}/objects/{key}     # Download object
DELETE /buckets/{bucket}/objects/{key}   # Delete object
GET  /buckets/{bucket}/objects           # List objects (with prefix filter)
```

## Port Assignment
- **HTTP Port**: 7871
- **Management Port**: 7872

## Technology Stack
- **Language**: Python (FastAPI)
- **Dependencies**: fastapi, httpx, aiofiles
- **Communication**: HTTP calls to storage and metadata services

## Core Logic
- Coordinate between storage and metadata services
- Handle object upload/download workflows
- Basic object validation (size limits, naming)

## Request Flow
1. Validate request with identity service
2. Generate UUID for new objects
3. Store data via storage service
4. Store metadata via metadata service
5. Return success/error response

## Storage Requirements
- No persistent storage (stateless service)
- Temporary file buffering during transfers

## Deployment
- Kubernetes Deployment
- 3 replicas for load distribution
- Resource limits: 2Gi memory, 1000m CPU