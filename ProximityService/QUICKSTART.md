# Proximity Service - Quick Start Guide

## Prerequisites

- **Docker** and **Docker Compose** installed
- **8GB RAM** minimum (recommended 16GB)
- **5GB free disk space**
- **Ports available**: 5832, 6739, 7891, 8921, 9823

## 🚀 Quick Start (5 minutes)

### 1. Clone and Navigate
```bash
cd /path/to/proximity-service
```

### 2. Start All Services
```bash
# Start core infrastructure (database + cache)
docker-compose up -d postgres-primary redis-cache

# Wait 30 seconds for database initialization
sleep 30

# Start application services
docker-compose up -d business-service location-service

# Start cache warmer to populate Redis
docker-compose up -d cache-warmer

# Wait for cache warming (10 seconds)
sleep 10

# Start API gateway
docker-compose up -d api-gateway

# Wait for all services to be ready
sleep 15
```

### 3. Verify System Health
```bash
curl http://localhost:7891/health
```
**Expected response:**
```json
{"status":"healthy","services":{"location":"healthy","business":"healthy"}}
```

## 🔍 Core Functionality Tests

### Test 1: Find Nearby Businesses
```bash
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=5000"
```

**Expected response:**
```json
{
  "businesses": [
    {"business_id": "xxx", "distance": 0.0},
    {"business_id": "yyy", "distance": 62.53}
  ],
  "total": 5
}
```

### Test 2: Get Business Details
```bash
# Use a business_id from the search results
curl http://localhost:7891/api/v1/businesses/{business_id}
```

**Expected response:**
```json
{
  "name": "Golden Gate Pizza",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "address": "123 Market St",
  "city": "San Francisco",
  "state": "CA",
  "country": "USA",
  "category": "Restaurant",
  "id": "business_id",
  "created_at": "2025-07-18T23:10:23.585460",
  "updated_at": "2025-07-18T23:10:23.585460"
}
```

### Test 3: Add New Business
```bash
curl -X POST http://localhost:7891/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New Restaurant",
    "latitude": 37.7751,
    "longitude": -122.4193,
    "address": "789 Main St",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "category": "Restaurant"
  }'
```

### Test 4: Search Different Radius
```bash
# 500 meters
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7750&longitude=-122.4195&radius=500"

# 1 kilometer  
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7750&longitude=-122.4195&radius=1000"

# 5 kilometers
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7750&longitude=-122.4195&radius=5000"
```

### Test 5: Update Business
```bash
curl -X PUT http://localhost:7891/api/v1/businesses/{business_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Restaurant Name",
    "latitude": 37.7752,
    "longitude": -122.4196,
    "address": "999 Updated St",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "category": "Fine Dining"
  }'
```

### Test 6: Delete Business
```bash
curl -X DELETE http://localhost:7891/api/v1/businesses/{business_id}
```

## 📊 Performance Testing

### Load Test Proximity Search
```bash
# Test 10 concurrent requests
for i in {1..10}; do
  curl -s "http://localhost:7891/api/v1/search/nearby?latitude=37.77$((i%10))&longitude=-122.41$((i%10))&radius=5000" &
done
wait
echo "All requests completed"
```

### Test Rate Limiting
```bash
# Send rapid requests to test rate limiting (1000/min limit)
for i in {1..20}; do
  echo "Request $i:"
  curl -w "Response time: %{time_total}s\n" -s "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000" | head -c 50
  echo ""
done
```

## 🔧 Service Management

### Check All Services Status
```bash
docker-compose ps
```

### View Service Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs api-gateway
docker-compose logs location-service
docker-compose logs business-service
docker-compose logs cache-warmer
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api-gateway
```

### Stop All Services
```bash
docker-compose down
```

### Clean Up (Remove all data)
```bash
docker-compose down -v
docker system prune -f
```

## 🌐 Service Endpoints

| Service | Port | Health Check | Purpose |
|---------|------|-------------|---------|
| **API Gateway** | 7891 | `/health` | Main entry point |
| **Location Service** | 8921 | `/health` | Proximity search |
| **Business Service** | 9823 | `/health` | Business CRUD |
| **PostgreSQL** | 5832 | - | Database |
| **Redis** | 6739 | - | Cache |

## 📍 Sample Coordinates

Test with these real San Francisco locations:

```bash
# Union Square
latitude=37.7879, longitude=-122.4074

# Financial District  
latitude=37.7949, longitude=-122.4094

# Mission District
latitude=37.7599, longitude=-122.4148

# Castro District
latitude=37.7609, longitude=-122.4350
```

## 🐛 Troubleshooting

### Services Not Starting
```bash
# Check Docker resources
docker system df
docker system prune -f

# Restart Docker Desktop
# Then try: docker-compose up -d
```

### Database Connection Issues
```bash
# Check if PostgreSQL is ready
docker-compose logs postgres-primary | grep "ready to accept connections"

# Restart database
docker-compose restart postgres-primary
sleep 30
docker-compose restart business-service
```

### Cache Issues
```bash
# Check Redis
docker-compose exec redis-cache redis-cli ping

# Restart cache warmer
docker-compose restart cache-warmer
```

### Port Conflicts
```bash
# Check what's using ports
lsof -i :7891
lsof -i :8921
lsof -i :9823

# Stop conflicting services or change ports in docker-compose.yml
```

## ✅ Success Indicators

Your system is working correctly when:

1. **Health check returns all services healthy**
2. **Proximity search returns businesses with distances**
3. **Business CRUD operations work end-to-end**
4. **Response times are under 100ms**
5. **All 6 Docker containers are running**

## 🎯 Next Steps

Once core functionality is verified:

1. **Scale Up**: Increase replica counts in docker-compose.yml
2. **Deploy to Kubernetes**: Use manifests in `/deployments`
3. **Add Monitoring**: Set up Prometheus and Grafana
4. **Performance Tuning**: Optimize cache TTL and database queries
5. **Add Features**: Implement additional filters and sorting

## 📞 Support

If you encounter issues:
1. Check the logs: `docker-compose logs [service-name]`
2. Verify all containers are running: `docker-compose ps`
3. Test individual services directly using their specific ports
4. Ensure you have sufficient system resources (RAM/CPU)