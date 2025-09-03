# Core Functionality Test Guide

## 🎯 Complete Test Suite for Proximity Service

This guide will walk you through testing every core feature of the proximity service in a logical sequence.

---

## 📋 Prerequisites Check

Before starting, ensure you have:
- [ ] Docker and Docker Compose installed
- [ ] Ports 5832, 6739, 7891, 8921, 9823 available
- [ ] At least 8GB RAM available
- [ ] curl command available

---

## 🚀 Step 1: Start the System

### 1.1 Start All Services
```bash
# Navigate to project directory
cd proximity-service

# Start all services in correct order
docker-compose up -d postgres-primary redis-cache
sleep 30  # Wait for database initialization

docker-compose up -d business-service location-service
sleep 10  # Wait for services to start

docker-compose up -d cache-warmer
sleep 10  # Wait for cache warming

docker-compose up -d api-gateway
sleep 15  # Wait for gateway to be ready
```

### 1.2 Verify All Services Running
```bash
docker-compose ps
```
**Expected Output:**
```
NAME                                     STATUS
10-proximityservice-api-gateway-1        Up
10-proximityservice-business-service-1   Up
10-proximityservice-cache-warmer-1       Up
10-proximityservice-location-service-1   Up
10-proximityservice-postgres-primary-1   Up
10-proximityservice-redis-cache-1        Up
```

---

## 🏥 Step 2: Health Check Tests

### 2.1 System Health Check
```bash
curl http://localhost:7891/health
```
**Expected Response:**
```json
{"status":"healthy","services":{"location":"healthy","business":"healthy"}}
```

### 2.2 Individual Service Health
```bash
# Location service
curl http://localhost:8921/health

# Business service  
curl http://localhost:9823/health
```

**✅ Success Criteria:** All health checks return `{"status":"healthy"}`

---

## 🏢 Step 3: Business Management Tests

### 3.1 Create First Business
```bash
curl -X POST http://localhost:7891/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Downtown Pizza Palace",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "address": "123 Market St",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "category": "Restaurant"
  }'
```

**Expected Response:**
```json
{
  "name": "Downtown Pizza Palace",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "address": "123 Market St",
  "city": "San Francisco",
  "state": "CA",
  "country": "USA",
  "category": "Restaurant",
  "id": "business-id-1",
  "created_at": "2025-07-18T...",
  "updated_at": "2025-07-18T..."
}
```

**📝 Save the business ID for next tests!**

### 3.2 Create Second Business (Different Location)
```bash
curl -X POST http://localhost:7891/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Union Square Cafe",
    "latitude": 37.7879,
    "longitude": -122.4074,
    "address": "456 Union St",
    "city": "San Francisco", 
    "state": "CA",
    "country": "USA",
    "category": "Cafe"
  }'
```

### 3.3 Create Third Business (Close to First)
```bash
curl -X POST http://localhost:7891/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Market Street Deli",
    "latitude": 37.7750,
    "longitude": -122.4195,
    "address": "789 Market St",
    "city": "San Francisco",
    "state": "CA", 
    "country": "USA",
    "category": "Deli"
  }'
```

### 3.4 Retrieve Business Details
```bash
# Replace {business-id-1} with actual ID from step 3.1
curl http://localhost:7891/api/v1/businesses/{business-id-1}
```

**✅ Success Criteria:** 
- All 3 businesses created successfully
- Each returns unique ID and timestamps
- Business retrieval returns complete details

---

## 🔍 Step 4: Proximity Search Tests

### 4.1 Search Downtown Area (5km radius)
```bash
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=5000"
```

**Expected Response:**
```json
{
  "businesses": [
    {"business_id": "business-id-1", "distance": 0.0},
    {"business_id": "business-id-3", "distance": 14.17},
    {"business_id": "business-id-2", "distance": 1789.34}
  ],
  "total": 3
}
```

### 4.2 Search with Smaller Radius (500m)
```bash
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=500"
```

**Expected Response:**
```json
{
  "businesses": [
    {"business_id": "business-id-1", "distance": 0.0},
    {"business_id": "business-id-3", "distance": 14.17}
  ],
  "total": 2
}
```

### 4.3 Search Different Location
```bash
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7879&longitude=-122.4074&radius=2000"
```

### 4.4 Search with Different Radius Options
```bash
# 1km radius
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000"

# 2km radius  
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=2000"

# 20km radius (maximum)
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=20000"
```

**✅ Success Criteria:**
- Larger radius returns more businesses
- Distances are calculated correctly
- Results sorted by distance (nearest first)
- Distance values are realistic (meters)

---

## ✏️ Step 5: Business Update Tests

### 5.1 Update Business Information
```bash
# Replace {business-id-1} with actual ID
curl -X PUT http://localhost:7891/api/v1/businesses/{business-id-1} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "UPDATED Downtown Pizza Palace",
    "latitude": 37.7751,
    "longitude": -122.4193,
    "address": "UPDATED 123 Market St",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "category": "Italian Restaurant"
  }'
```

### 5.2 Verify Update
```bash
curl http://localhost:7891/api/v1/businesses/{business-id-1}
```

**✅ Success Criteria:**
- Name shows "UPDATED Downtown Pizza Palace"
- Location coordinates updated
- Updated timestamp changed
- Category changed to "Italian Restaurant"

---

## ⚡ Step 6: Performance Tests

### 6.1 Response Time Test
```bash
# Test 5 consecutive requests and measure time
for i in {1..5}; do
  echo "Request $i:"
  time curl -s "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=5000" > /dev/null
done
```

### 6.2 Concurrent Request Test  
```bash
# Test 10 simultaneous requests
for i in {1..10}; do
  curl -s "http://localhost:7891/api/v1/search/nearby?latitude=37.77$((i%10))&longitude=-122.41$((i%10))&radius=1000" &
done
wait
echo "All concurrent requests completed"
```

### 6.3 Rate Limiting Test
```bash
# Send rapid requests to test rate limiting
for i in {1..15}; do
  echo "Request $i:"
  curl -w "Response time: %{time_total}s, HTTP code: %{http_code}\n" \
    -s "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000" > /dev/null
  sleep 0.1
done
```

**✅ Success Criteria:**
- Response times under 200ms
- All concurrent requests succeed
- Rate limiting allows normal traffic
- No 429 errors for reasonable request rates

---

## 🗑️ Step 7: Business Deletion Tests

### 7.1 Delete a Business
```bash
# Replace {business-id-2} with actual ID
curl -X DELETE http://localhost:7891/api/v1/businesses/{business-id-2}
```

**Expected Response:**
```json
{"message": "Business deleted successfully"}
```

### 7.2 Verify Deletion
```bash
# This should return 404
curl http://localhost:7891/api/v1/businesses/{business-id-2}
```

### 7.3 Search Should Exclude Deleted Business
```bash
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7879&longitude=-122.4074&radius=5000"
```

**✅ Success Criteria:**
- Deletion returns success message
- Deleted business returns 404
- Search results no longer include deleted business

---

## 🌍 Step 8: Geographic Boundary Tests

### 8.1 Test Different Geographic Locations
```bash
# New York City
curl "http://localhost:7891/api/v1/search/nearby?latitude=40.7128&longitude=-74.0060&radius=5000"

# London (should return empty)
curl "http://localhost:7891/api/v1/search/nearby?latitude=51.5074&longitude=-0.1278&radius=5000"

# Invalid coordinates (should fail)
curl "http://localhost:7891/api/v1/search/nearby?latitude=91.0000&longitude=-122.4194&radius=5000"
```

### 8.2 Test Boundary Coordinates
```bash
# Edge of the world
curl "http://localhost:7891/api/v1/search/nearby?latitude=89.9999&longitude=179.9999&radius=5000"

# Equator/Prime Meridian
curl "http://localhost:7891/api/v1/search/nearby?latitude=0.0000&longitude=0.0000&radius=5000"
```

**✅ Success Criteria:**
- Remote locations return empty results
- Invalid coordinates return error
- Boundary coordinates work correctly

---

## 🧪 Step 9: Edge Case Tests

### 9.1 Invalid Parameter Tests
```bash
# Invalid radius (too small)
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=100"

# Invalid radius (too large)  
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=50000"

# Missing required parameters
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749"

# Invalid business creation (missing required fields)
curl -X POST http://localhost:7891/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d '{"name": "Test"}'
```

### 9.2 Large Dataset Test
```bash
# Create multiple businesses quickly
for i in {1..10}; do
  curl -s -X POST http://localhost:7891/api/v1/businesses \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"Test Business $i\",
      \"latitude\": 37.77$((i%10)),
      \"longitude\": -122.41$((i%10)),
      \"address\": \"$i Test St\",
      \"city\": \"San Francisco\",
      \"state\": \"CA\",
      \"country\": \"USA\",
      \"category\": \"Test\"
    }" > /dev/null &
done
wait

# Search should now return more results
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=20000"
```

**✅ Success Criteria:**
- Invalid parameters return appropriate errors
- System handles edge cases gracefully
- Performance remains good with more data

---

## 📊 Step 10: Final Validation

### 10.1 Complete System Status
```bash
# Check all services
curl http://localhost:7891/health

# Check service logs for errors
docker-compose logs --tail=20 api-gateway
docker-compose logs --tail=20 location-service  
docker-compose logs --tail=20 business-service
```

### 10.2 Data Consistency Check
```bash
# Count businesses in search vs database
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=20000" | jq '.total'

# Should match the number of businesses created
```

### 10.3 Performance Summary
```bash
# Final performance test
echo "Testing final system performance..."
time curl -s "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=5000" > /dev/null
```

---

## ✅ Success Checklist

Mark each item as completed:

### Basic Functionality
- [ ] All 6 services start successfully
- [ ] Health checks return healthy status
- [ ] Can create new businesses
- [ ] Can retrieve business details
- [ ] Can update business information
- [ ] Can delete businesses

### Core Proximity Features  
- [ ] Proximity search finds nearby businesses
- [ ] Distance calculations are accurate
- [ ] Different radius options work (500m, 1km, 2km, 5km, 20km)
- [ ] Results sorted by distance
- [ ] Search excludes deleted businesses

### Performance Requirements
- [ ] Response times under 200ms
- [ ] Handles concurrent requests
- [ ] Rate limiting works correctly
- [ ] System stable under load

### Data Integrity
- [ ] Created businesses appear in search results
- [ ] Updated businesses reflect changes
- [ ] Deleted businesses removed from results
- [ ] Geographic boundaries respected

### Error Handling
- [ ] Invalid parameters return proper errors
- [ ] Missing data handled gracefully
- [ ] System recovers from failures

---

## 🔧 Troubleshooting

### Common Issues

**Services Won't Start:**
```bash
# Check available resources
docker system df
docker system prune -f
```

**Search Returns No Results:**
```bash
# Check cache warming
docker-compose logs cache-warmer
docker-compose restart cache-warmer
```

**Slow Response Times:**
```bash
# Check service resources
docker stats
# Restart services if needed
docker-compose restart
```

**Database Connection Errors:**
```bash
# Wait longer for database initialization
sleep 60
docker-compose restart business-service
```

---

## 🎯 Expected Results Summary

After completing all tests, you should have:

- **~13+ businesses** in the system (3 manual + 10 bulk created)
- **Sub-200ms response times** for proximity searches
- **Accurate distance calculations** in meters
- **Working CRUD operations** for all business data
- **Proper error handling** for invalid inputs
- **Geographic search coverage** across different coordinate ranges

The system is **production-ready** when all tests pass! 🚀