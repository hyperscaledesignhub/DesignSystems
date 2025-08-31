# 6. Metadata Service

## Core Features (Minimal MVP)
- **Object Metadata**: Store object metadata (name, size, timestamps)
- **Bucket Metadata**: Store bucket-object relationships
- **Query Support**: Find objects by bucket/key, list objects with prefix
- **Atomic Operations**: Ensure metadata consistency

## APIs
```
POST /metadata/objects           # Create object metadata
GET  /metadata/objects/{uuid}    # Get object metadata
DELETE /metadata/objects/{uuid}  # Delete object metadata
GET  /metadata/buckets/{bucket}/objects  # List objects in bucket
```

## Port Assignment
- **HTTP Port**: 7891
- **Management Port**: 7892

## Technology Stack
- **Language**: Python (FastAPI)
- **Database**: PostgreSQL (ACID compliance required)
- **Dependencies**: fastapi, asyncpg, sqlalchemy

## Data Schema
```sql
object_metadata (
  object_id UUID PRIMARY KEY,
  bucket_name VARCHAR,
  object_name VARCHAR,
  content_type VARCHAR,
  size_bytes INTEGER,
  etag VARCHAR,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  UNIQUE(bucket_name, object_name)
)

CREATE INDEX idx_bucket_name ON object_metadata(bucket_name);
CREATE INDEX idx_bucket_object ON object_metadata(bucket_name, object_name);
```

## Query Patterns
- Find object by bucket + key: O(1) lookup
- List objects by bucket: Index scan
- Prefix filtering: LIKE queries with optimization

## Storage Requirements
- PostgreSQL database
- ~2KB per object metadata record
- Expected: 50GB+ for millions of objects

## Deployment
- Kubernetes Deployment
- 2 replicas with read/write split
- PostgreSQL cluster for HA
- Resource limits: 2Gi memory, 1000m CPU