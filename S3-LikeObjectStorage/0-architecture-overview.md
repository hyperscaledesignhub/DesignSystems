# S3-like Object Storage - Minimal Architecture

## System Overview
Minimal viable S3-compatible object storage system built as microservices for Kubernetes deployment.

## Service Architecture
```
[Client] → [API Gateway] → [Services Layer] → [Data Layer]
```

## Port Allocation (Uncommon Ranges)
| Service | HTTP Port | Management Port | Purpose |
|---------|-----------|-----------------|---------|
| API Gateway | 7841 | 7842 | Request routing & load balancing |
| Identity Service | 7851 | 7852 | Authentication & authorization |
| Bucket Service | 7861 | 7862 | Bucket lifecycle management |
| Object Service | 7871 | 7872 | Object operations orchestration |
| Storage Service | 7881 | 7882 | Raw data persistence |
| Metadata Service | 7891 | 7892 | Object/bucket metadata |
| Web UI | 9347 | 9348 | Customer web interface |

## Data Flow
### Upload Object
1. Client → API Gateway (7841)
2. API Gateway → Identity Service (7851) [Auth]
3. API Gateway → Object Service (7871)
4. Object Service → Storage Service (7881) [Data]
5. Object Service → Metadata Service (7891) [Metadata]

### Download Object  
1. Client → API Gateway (7841)
2. API Gateway → Identity Service (7851) [Auth]
3. API Gateway → Object Service (7871)
4. Object Service → Metadata Service (7891) [Get UUID]
5. Object Service → Storage Service (7881) [Fetch Data]

## Technology Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Databases**: PostgreSQL (metadata), SQLite (simple storage)
- **Container**: Docker
- **Orchestration**: Kubernetes
- **Storage**: Persistent Volumes

## Deployment Strategy
- Each service: Independent Docker container
- Database: Managed PostgreSQL or StatefulSet
- Storage: Kubernetes Persistent Volumes
- Networking: ClusterIP services with Ingress
- Scaling: Horizontal Pod Autoscaler

## Key Design Decisions
1. **Simple Replication**: 3-copy synchronous replication (no erasure coding)
2. **Strong Consistency**: ACID compliance for metadata
3. **Stateless Services**: All business logic services are stateless
4. **HTTP APIs**: RESTful APIs between all services
5. **Local Storage**: Filesystem-based storage with SQLite indexing