# Cache Service - Minimal Features

## Core Features
- Redis cluster for high availability
- Two separate caches:
  - Geohash cache: Business IDs by geohash
  - Business info cache: Full business objects
- Automatic expiration (24 hours)
- Cache warming on startup

## Cache Structure
### Geohash Cache
- Key: `geohash:{precision}:{hash}`
- Value: List of business IDs
- TTL: 24 hours

### Business Info Cache
- Key: `business:{id}`
- Value: JSON business object
- TTL: 24 hours

## Port Configuration
- Redis Cluster: 6739, 6740, 6741
- Sentinel: 26739, 26740, 26741

## Technologies
- Redis 7.0
- Redis Sentinel for HA
- Python Redis client

## Resource Requirements
- CPU: 1000m per node
- Memory: 2Gi per node
- Nodes: 3 minimum