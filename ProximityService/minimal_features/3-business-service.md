# Business Service - Minimal Features

## Core Features
- CRUD operations for businesses
- Business data validation
- Batch updates (nightly job)
- Business information caching

## API Endpoints
- `GET /businesses/{id}` - Get business details
- `POST /businesses` - Create new business
- `PUT /businesses/{id}` - Update business
- `DELETE /businesses/{id}` - Delete business

## Port Configuration
- Internal: 9823 (HTTP)
- Admin: 9824

## Technologies
- Python (FastAPI)
- PostgreSQL for persistent storage
- Redis for caching

## Data Model
```
Business {
  id: UUID
  name: string
  latitude: float
  longitude: float
  address: string
  city: string
  state: string
  country: string
  category: string
  created_at: timestamp
  updated_at: timestamp
}
```

## Resource Requirements
- CPU: 800m
- Memory: 1Gi
- Replicas: 3 minimum