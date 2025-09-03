# Proximity Service Demo Guide

## 🚀 Quick Start

### 1. Start All Services
```bash
cd /Users/vijayabhaskarv/python-projects/venv/sysdesign/10-ProximityService
docker-compose up -d
```

### 2. Load Demo Data
```bash
cd demo
python3 generate_data.py
```

### 3. Open Web UI
Open `demo/index.html` in your browser or:
```bash
open demo/index.html  # macOS
xdg-open demo/index.html  # Linux
```

## 🎯 Demo Features

### 1. **Geospatial Search**
- **Interactive Map**: Click anywhere to set search location
- **Radius Options**: 500m, 1km, 2km, 5km
- **Real-time Results**: Shows businesses with distances
- **Visual Feedback**: Map markers and search radius circle

### 2. **Business Management** 
- **Create Business**: Add new businesses at any location
- **Generate Demo Data**: Auto-create 10 random businesses
- **CRUD Operations**: Full create, read, update, delete support

### 3. **High Availability Testing**
- **Database Failover**:
  - Kill Primary DB → Reads continue via replicas
  - Restore Primary → Writes resume automatically
  
- **Redis Failover**:
  - Kill Redis Master → Sentinel promotes replica
  - Restore Master → Automatic rebalancing

### 4. **Performance Features**
- **Rate Limiting**: 1000 requests/minute per IP
- **Response Time**: Monitor average latency
- **Cache Hit Rate**: Redis caching for <10ms responses
- **Load Testing**: Bulk request testing

## 📊 Architecture Components

### Services Running:
1. **API Gateway** (Port 7891) - Load balancing, rate limiting
2. **Business Service** (Port 9823) - CRUD operations
3. **Location Service** (Port 8921) - Geospatial search
4. **PostgreSQL Cluster**:
   - Primary (Port 5832)
   - Replica 1 (Port 5833)
   - Replica 2 (Port 5834)
5. **Redis Cluster**:
   - Master (Port 6739)
   - Replica 1 (Port 6740)
   - Replica 2 (Port 6741)
   - Sentinels (Ports 26379-26381)

## 🎮 Demo Scenarios

### Scenario 1: Normal Operation
1. Open web UI
2. Click "Generate Demo Data"
3. Search for businesses within 1km
4. Observe response times (<100ms)

### Scenario 2: Database Failover
1. Click "Kill Primary DB"
2. Try searching (✓ works - reads from replicas)
3. Try creating business (✗ fails - no writable DB)
4. Click "Restore Primary"
5. All operations resume

### Scenario 3: Cache Performance
1. Search for businesses
2. Note response time (first search ~100ms)
3. Repeat same search
4. Note improved time (<20ms from cache)

### Scenario 4: Rate Limiting
1. Click "Test Rate Limit"
2. Observe ~17 requests succeed
3. Remaining blocked (429 status)

### Scenario 5: Load Test
```bash
./demo_failover.sh
```
Runs automated tests for all failover scenarios

## 🔍 Health Monitoring

Check system health:
```bash
curl http://localhost:7891/health | jq
```

Response shows:
- Database primary/replica status
- Redis master/slave status
- Overall system health

## 📈 Performance Metrics

Expected performance:
- **Search Latency**: <100ms (uncached), <20ms (cached)
- **Write Latency**: <50ms
- **Cache Hit Rate**: >90% after warm-up
- **Failover Time**: <5 seconds
- **Rate Limit**: 1000 req/min

## 🛠️ Troubleshooting

### Services not starting:
```bash
docker-compose down -v
docker-compose up -d
```

### Cache not working:
```bash
docker-compose restart redis-master redis-replica1 redis-replica2
```

### Database issues:
```bash
docker-compose logs postgres-primary
docker-compose logs postgres-replica1
```

## 📝 Key Takeaways

1. **Geohash Indexing**: Efficient proximity search using precision levels 4-6
2. **Read/Write Splitting**: Automatic routing to primary/replicas
3. **Cache Strategy**: 24-hour TTL with hourly warming
4. **Failover**: Automatic with <5 second recovery
5. **Rate Limiting**: Token bucket algorithm at API Gateway
6. **Monitoring**: Real-time health checks for all components

## 🎬 Demo Video Script

1. **Introduction** (30s)
   - Show architecture diagram
   - Explain microservices design

2. **Basic Features** (2 min)
   - Create businesses
   - Search nearby locations
   - Show map visualization

3. **High Availability** (2 min)
   - Kill primary database
   - Show continued read operations
   - Restore and test writes

4. **Performance** (1 min)
   - Show cache hit improvements
   - Demonstrate rate limiting
   - Display response times

5. **Conclusion** (30s)
   - Summarize key features
   - Show health monitoring
   - Q&A preparation