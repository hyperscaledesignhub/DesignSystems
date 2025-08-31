# 5. Storage Service

## Core Features (Minimal MVP)
- **Data Persistence**: Store raw object data on disk
- **Data Retrieval**: Fetch object data by UUID
- **Basic Replication**: 3-copy replication for durability
- **Health Monitoring**: Report storage node health

## APIs
```
POST /data                       # Store object data, return UUID
GET  /data/{uuid}               # Retrieve object data by UUID
DELETE /data/{uuid}             # Delete object data
GET  /health                    # Storage node health status
```

## Port Assignment
- **HTTP Port**: 7881
- **Management Port**: 7882

## Technology Stack
- **Language**: Python (FastAPI) 
- **Storage**: Local filesystem with SQLite index
- **Dependencies**: fastapi, aiofiles, sqlalchemy

## Data Organization
- Objects stored in local filesystem
- SQLite database for UUID -> file mapping
- Simple file naming: `/data/{uuid[:2]}/{uuid[2:4]}/{uuid}`

## Replication Strategy
- Primary-replica pattern
- Synchronous replication to 2 replicas
- Simple consistency model (strong consistency)

## Storage Schema
```sql
objects (
  uuid VARCHAR PRIMARY KEY,
  file_path VARCHAR,
  size_bytes INTEGER,
  checksum VARCHAR,
  created_at TIMESTAMP
)
```

## Storage Requirements
- Local filesystem (SSD preferred)
- SQLite database for metadata
- Expected: 10TB+ storage capacity per node

## Deployment
- Kubernetes StatefulSet
- Persistent Volume Claims
- 3 replicas minimum
- Resource limits: 4Gi memory, 2000m CPU