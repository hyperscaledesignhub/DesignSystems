# Web Crawler Microservices Architecture

This is a **microservices-based refactoring** of the web crawler, demonstrating how a monolithic application can be decomposed into independent, scalable services.

## 🏗️ Architecture Overview

### Microservices Components:

1. **URL Frontier Service** (Port 5001)
   - Manages URL queue with politeness constraints
   - Implements priority-based scheduling
   - Tracks visited URLs

2. **HTML Downloader Service** (Port 5002)
   - Handles HTTP requests with retries
   - Implements caching for efficiency
   - Manages rate limiting

3. **Content Parser Service** (Port 5003)
   - Parses HTML content
   - Extracts text, metadata, and links
   - Cleans and normalizes content

4. **Content Deduplication Service** (Port 5004)
   - Detects duplicate content using hashing
   - Implements similarity detection
   - Maintains content fingerprints

5. **API Gateway** (Port 5000)
   - Orchestrates communication between services
   - Provides unified API interface
   - Manages crawl workflows

### Infrastructure Components:

- **Redis**: Shared state management and caching
- **Prometheus**: Metrics collection (optional)
- **Grafana**: Metrics visualization (optional)

## 🚀 Quick Start

### Prerequisites:
- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 5000-5004 and 6379 available

### 1. Build and Start Services:

```bash
cd microservices-demo

# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

### 2. Verify Services:

```bash
# Check gateway health
curl http://localhost:5000/health

# Check all services health
curl http://localhost:5000/services/health
```

## 📡 API Usage

### Start a Crawl:

```bash
curl -X POST http://localhost:5000/crawl/start \
  -H "Content-Type: application/json" \
  -d '{
    "seed_urls": [
      "https://httpbin.org/html",
      "https://httpbin.org/links/3"
    ]
  }'
```

### Check Crawl Status:

```bash
curl http://localhost:5000/crawl/status
```

### Process Single URL:

```bash
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/html"}'
```

### Get Statistics:

```bash
curl http://localhost:5000/stats
```

## 🔧 Individual Service APIs

### URL Frontier Service:

```bash
# Enqueue URL
curl -X POST http://localhost:5001/enqueue \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "priority": 10}'

# Dequeue URLs
curl http://localhost:5001/dequeue?count=5

# Get stats
curl http://localhost:5001/stats
```

### HTML Downloader Service:

```bash
# Download content
curl -X POST http://localhost:5002/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/html"}'
```

### Content Parser Service:

```bash
# Parse HTML
curl -X POST http://localhost:5003/parse \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "content": "<html>...</html>",
    "extract_metadata": true
  }'
```

### Deduplication Service:

```bash
# Check for duplicates
curl -X POST http://localhost:5004/check \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "content": "Page content here..."
  }'
```

## 📊 Monitoring

### Access Monitoring Tools:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Redis Commander**: Can be added for Redis monitoring

### View Logs:

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f gateway
docker-compose logs -f frontier
```

## 🔄 Scaling Services

### Scale Individual Services:

```bash
# Scale downloader service to 3 instances
docker-compose up -d --scale downloader=3

# Scale parser service to 2 instances
docker-compose up -d --scale parser=2
```

## 🧪 Testing

### Health Check All Services:

```bash
# Create a test script
cat > test_services.sh << 'EOF'
#!/bin/bash
echo "Testing all services..."
for port in 5000 5001 5002 5003 5004; do
  echo -n "Service on port $port: "
  curl -s http://localhost:$port/health | jq -r '.status' || echo "FAILED"
done
EOF

chmod +x test_services.sh
./test_services.sh
```

### Load Testing:

```bash
# Simple load test
for i in {1..10}; do
  curl -X POST http://localhost:5000/process \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"https://httpbin.org/html?page=$i\"}" &
done
wait
```

## 🛠️ Development

### Local Development Without Docker:

```bash
# Install dependencies
pip install -r shared/requirements.txt
pip install -r services/parser/requirements.txt

# Start Redis
redis-server

# Start individual service
cd services/gateway
python app.py
```

### Adding New Services:

1. Create service directory: `services/newservice/`
2. Add `app.py` with Flask application
3. Add service-specific `requirements.txt`
4. Update `docker-compose.yml`
5. Update gateway configuration

## 📈 Architecture Benefits

### Compared to Monolithic Version:

| Aspect | Monolithic | Microservices |
|--------|-----------|---------------|
| **Scalability** | Scale entire app | Scale individual services |
| **Deployment** | Deploy everything | Deploy independently |
| **Technology** | Single stack | Polyglot possible |
| **Fault Isolation** | Single point of failure | Service isolation |
| **Development** | Single codebase | Independent teams |
| **Resource Usage** | Shared resources | Optimized per service |

## 🚨 Troubleshooting

### Services Not Starting:

```bash
# Check logs
docker-compose logs [service_name]

# Restart specific service
docker-compose restart [service_name]

# Rebuild service
docker-compose build --no-cache [service_name]
```

### Redis Connection Issues:

```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Clear Redis data
docker-compose exec redis redis-cli FLUSHALL
```

### Port Conflicts:

```bash
# Check port usage
lsof -i :5000-5004

# Use different ports in .env file
echo "GATEWAY_PORT=8000" >> .env
```

## 🔍 Comparison: Monolith vs Microservices

### Performance Metrics:

| Metric | Monolith | Microservices |
|--------|----------|---------------|
| **Startup Time** | ~2s | ~10s (all services) |
| **Memory Usage** | ~200MB | ~600MB (total) |
| **Network Latency** | 0ms (in-process) | 1-5ms (inter-service) |
| **Throughput** | High | Medium (network overhead) |
| **Complexity** | Low | High |

### When to Use Each:

**Use Monolith When:**
- Small to medium scale
- Single team
- Rapid prototyping
- Limited resources

**Use Microservices When:**
- Large scale requirements
- Multiple teams
- Independent scaling needs
- Technology diversity needed
- High availability requirements

## 📝 Notes

- This is a demonstration of microservices architecture
- For production, add service mesh (Istio/Linkerd)
- Implement proper authentication/authorization
- Add circuit breakers and retries
- Use message queues for async communication
- Implement distributed tracing (Jaeger/Zipkin)

## 🛑 Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

---

**Architecture Transformation Complete!** 🎉

The crawler has been successfully refactored from a monolithic application into a microservices architecture, demonstrating modern cloud-native patterns and scalability improvements.