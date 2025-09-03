# Location Service (LBS) - Minimal Features

## Core Features
- Find businesses within radius (0.5km, 1km, 2km, 5km)
- Geohash-based spatial indexing (precision 4-6)
- Calculate distance between coordinates
- Return top 50 nearest businesses

## API Endpoints
- `GET /nearby` - Find nearby businesses
  - Parameters: latitude, longitude, radius
  - Response: List of business IDs with distances

## Port Configuration
- Internal: 8921 (HTTP)
- Metrics: 8922

## Technologies
- Python (FastAPI)
- Redis for geohash cache
- NumPy for distance calculations

## Data Storage
- Geohash index cache (Redis)
- Business location data (Redis)

## Resource Requirements
- CPU: 1000m
- Memory: 1Gi
- Replicas: 5 minimum