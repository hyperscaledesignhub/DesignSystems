# 3. Bucket Service

## Core Features (Minimal MVP)
- **Create Bucket**: Create new storage bucket
- **List Buckets**: List all buckets for a user
- **Delete Bucket**: Delete empty bucket
- **Bucket Validation**: Ensure globally unique bucket names

## APIs
```
POST /buckets                    # Create bucket
GET  /buckets                    # List user's buckets  
GET  /buckets/{bucket}          # Get bucket info
DELETE /buckets/{bucket}        # Delete bucket (if empty)
```

## Port Assignment
- **HTTP Port**: 7861
- **Management Port**: 7862

## Technology Stack
- **Language**: Python (FastAPI)
- **Database**: PostgreSQL (for ACID compliance)
- **Dependencies**: fastapi, asyncpg, sqlalchemy

## Data Schema
```sql
buckets (
  bucket_id UUID PRIMARY KEY,
  bucket_name VARCHAR UNIQUE,
  owner_id VARCHAR,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

## Storage Requirements
- PostgreSQL database
- ~1KB per bucket record
- Expected: <10GB for millions of buckets

## Deployment
- Kubernetes Deployment
- 2 replicas for availability
- Resource limits: 1Gi memory, 500m CPU