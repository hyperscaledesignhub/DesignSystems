# Database Service - Minimal Features

## Core Features
- PostgreSQL primary-replica setup
- Automatic failover
- Read replicas for scaling
- Daily backups

## Database Schema
```sql
-- Business table
CREATE TABLE businesses (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Geospatial index table
CREATE TABLE geohash_index (
    geohash VARCHAR(12) NOT NULL,
    business_id UUID NOT NULL,
    PRIMARY KEY (geohash, business_id),
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

CREATE INDEX idx_geohash ON geohash_index(geohash);
```

## Port Configuration
- Primary: 5832
- Replicas: 5833, 5834

## Technologies
- PostgreSQL 15
- PgBouncer for connection pooling
- Patroni for HA

## Resource Requirements
- CPU: 2000m
- Memory: 4Gi
- Storage: 100Gi SSD