# Proximity Service API Reference

## Base URL
```
http://localhost:7891/api/v1
```

## Authentication
- No authentication required for this MVP
- Rate limited to 1000 requests per minute per IP

---

## 🔍 Search Endpoints

### Find Nearby Businesses
Find businesses within a specified radius of coordinates.

```http
GET /search/nearby
```

**Parameters:**
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `latitude` | float | Yes | Latitude coordinate (-90 to 90) | `37.7749` |
| `longitude` | float | Yes | Longitude coordinate (-180 to 180) | `-122.4194` |
| `radius` | int | No | Search radius in meters (500-20000) | `5000` |

**Supported Radius Values:**
- `500` - 0.5km (precision 6)
- `1000` - 1km (precision 5)  
- `2000` - 2km (precision 5)
- `5000` - 5km (precision 4)
- `20000` - 20km (precision 4)

**Example Request:**
```bash
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=5000"
```

**Response:**
```json
{
  "businesses": [
    {
      "business_id": "123e4567-e89b-12d3-a456-426614174000",
      "distance": 0.0
    },
    {
      "business_id": "987fcdeb-51a2-43d1-9c4e-5f6a7b8c9d0e", 
      "distance": 125.04
    }
  ],
  "total": 2
}
```

**Response Fields:**
- `businesses`: Array of nearby businesses
- `business_id`: Unique identifier for the business
- `distance`: Distance from search point in meters
- `total`: Number of businesses found

**HTTP Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

## 🏢 Business Endpoints

### Get Business Details
Retrieve detailed information about a specific business.

```http
GET /businesses/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Business unique identifier |

**Example Request:**
```bash
curl http://localhost:7891/api/v1/businesses/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Golden Gate Pizza",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "address": "123 Market St",
  "city": "San Francisco",
  "state": "CA",
  "country": "USA",
  "category": "Restaurant",
  "created_at": "2025-07-18T23:10:23.585460",
  "updated_at": "2025-07-18T23:10:23.585460"
}
```

---

### Create New Business
Add a new business to the system.

```http
POST /businesses
```

**Request Body:**
```json
{
  "name": "My Restaurant",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "address": "123 Main St",
  "city": "San Francisco", 
  "state": "CA",
  "country": "USA",
  "category": "Restaurant"
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | 1-255 characters |
| `latitude` | float | Yes | -90.0 to 90.0 |
| `longitude` | float | Yes | -180.0 to 180.0 |
| `address` | string | No | Max 500 characters |
| `city` | string | No | Max 100 characters |
| `state` | string | No | Max 100 characters |
| `country` | string | No | Max 100 characters |
| `category` | string | No | Max 100 characters |

**Example Request:**
```bash
curl -X POST http://localhost:7891/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sunset Cafe",
    "latitude": 37.7699,
    "longitude": -122.4681,
    "address": "456 Irving St",
    "city": "San Francisco",
    "state": "CA", 
    "country": "USA",
    "category": "Cafe"
  }'
```

**Response:**
```json
{
  "id": "new-uuid-generated",
  "name": "Sunset Cafe",
  "latitude": 37.7699,
  "longitude": -122.4681,
  "address": "456 Irving St",
  "city": "San Francisco",
  "state": "CA",
  "country": "USA", 
  "category": "Cafe",
  "created_at": "2025-07-18T23:15:30.123456",
  "updated_at": "2025-07-18T23:15:30.123456"
}
```

---

### Update Business
Update an existing business.

```http
PUT /businesses/{id}
```

**Request Body:** Same as POST /businesses

**Example Request:**
```bash
curl -X PUT http://localhost:7891/api/v1/businesses/123e4567-e89b-12d3-a456-426614174000 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Restaurant Name",
    "latitude": 37.7750,
    "longitude": -122.4195,
    "address": "789 Updated St",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "category": "Fine Dining"
  }'
```

---

### Delete Business
Remove a business from the system.

```http
DELETE /businesses/{id}
```

**Example Request:**
```bash
curl -X DELETE http://localhost:7891/api/v1/businesses/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "message": "Business deleted successfully"
}
```

---

## 🏥 Health Check

### System Health
Check the health status of all services.

```http
GET /health
```

**Example Request:**
```bash
curl http://localhost:7891/health
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "location": "healthy",
    "business": "healthy"
  }
}
```

**Status Values:**
- `healthy` - All services operational
- `degraded` - Some services have issues
- `unhealthy` - Critical services down

---

## 📊 Response Codes

### Success Codes
- `200 OK` - Request successful
- `201 Created` - Resource created successfully

### Client Error Codes  
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded

### Server Error Codes
- `500 Internal Server Error` - Unexpected server error
- `503 Service Unavailable` - Service temporarily unavailable
- `504 Gateway Timeout` - Request timeout

---

## 🔄 Rate Limiting

**Limits:**
- **1000 requests per minute** per IP address
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`: Request limit per window
  - `X-RateLimit-Remaining`: Requests remaining in window
  - `X-RateLimit-Reset`: Time when window resets

**Rate Limit Exceeded Response:**
```json
{
  "detail": "Rate limit exceeded"
}
```

---

## 🧪 Example Workflows

### Complete Business Lifecycle
```bash
# 1. Create business
BUSINESS_ID=$(curl -s -X POST http://localhost:7891/api/v1/businesses \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Business","latitude":37.7749,"longitude":-122.4194,"address":"123 Test St","city":"SF","state":"CA","country":"USA","category":"Test"}' | jq -r .id)

# 2. Search for nearby businesses
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000"

# 3. Get business details  
curl http://localhost:7891/api/v1/businesses/$BUSINESS_ID

# 4. Update business
curl -X PUT http://localhost:7891/api/v1/businesses/$BUSINESS_ID \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Business","latitude":37.7750,"longitude":-122.4195,"address":"456 Updated St","city":"SF","state":"CA","country":"USA","category":"Updated"}'

# 5. Delete business
curl -X DELETE http://localhost:7891/api/v1/businesses/$BUSINESS_ID
```

### Geographic Search Patterns
```bash
# City center search
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=2000"

# Neighborhood search  
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7699&longitude=-122.4681&radius=500"

# Wide area search
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=20000"
```

---

## 🛠 Error Handling

### Standard Error Response
```json
{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-07-18T23:15:30.123Z"
}
```

### Common Errors

**Invalid Coordinates:**
```json
{
  "detail": "Latitude must be between -90 and 90"
}
```

**Business Not Found:**
```json
{
  "detail": "Business not found"
}
```

**Invalid Radius:**
```json
{
  "detail": "Radius must be between 500 and 20000 meters"
}
```

---

## 📏 Distance Calculation

- **Algorithm**: Haversine formula for great-circle distance
- **Accuracy**: ±1 meter for distances under 10km
- **Units**: All distances returned in meters
- **Sorting**: Results always sorted by distance (nearest first)

---

## 🎯 Performance Expectations

| Operation | Expected Response Time | Throughput |
|-----------|----------------------|------------|
| Proximity Search | < 100ms | 1000+ req/sec |
| Business Retrieval | < 50ms | 2000+ req/sec |
| Business Creation | < 200ms | 500+ req/sec |
| Business Update | < 200ms | 500+ req/sec |
| Business Deletion | < 100ms | 1000+ req/sec |