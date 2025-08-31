# 2. Identity Service

## Core Features (Minimal MVP)
- **Authentication**: API key-based authentication
- **Authorization**: Basic bucket/object permissions (READ/WRITE)
- **User Management**: Simple user creation/deletion
- **Token Validation**: Validate API keys for requests

## APIs
```
POST /auth/validate              # Validate API key and permissions
POST /users                      # Create new user
GET  /users/{user_id}           # Get user info
DELETE /users/{user_id}         # Delete user
```

## Port Assignment
- **HTTP Port**: 7851
- **Management Port**: 7852

## Technology Stack
- **Language**: Python (FastAPI)
- **Database**: SQLite (for simplicity)
- **Dependencies**: fastapi, sqlalchemy, bcrypt

## Data Schema
```sql
users (
  user_id VARCHAR PRIMARY KEY,
  api_key VARCHAR UNIQUE,
  permissions JSON,
  created_at TIMESTAMP
)
```

## Storage Requirements
- SQLite database file (< 100MB for MVP)
- User data and API keys

## Deployment
- Kubernetes Deployment
- 2 replicas for availability
- Resource limits: 512Mi memory, 300m CPU