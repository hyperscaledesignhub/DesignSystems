# Search Autocomplete System - Docker Deployment

Complete containerized deployment with individual Docker containers for all services and infrastructure components.

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐
│   Web UI    │───▶│   API Gateway   │───▶│  Query Service   │
│  (Native)   │    │   (Container)   │    │   (Container)    │
│ Port 8080   │    │   Port 19845    │    │   Port 17893     │
└─────────────┘    └─────────────────┘    └──────────────────┘
                            │                       │
                            │                       ▼
                            │              ┌──────────────────┐
                            │              │ Trie Cache Svc   │
                            │              │   (Container)    │
                            │              │   Port 18294     │
                            │              └──────────────────┘
                            │                       │
                            ▼                       ▼
                   ┌──────────────────┐    ┌──────────────────┐
                   │Data Collection   │    │   PostgreSQL     │
                   │   (Container)    │    │   (Container)    │
                   │   Port 18761     │    │   Port 5432      │
                   └──────────────────┘    └──────────────────┘
                            │                       
                            ▼                       
                   ┌──────────────────┐             
                   │     Kafka        │             
                   │   (Container)    │             
                   │   Port 9092      │             
                   └──────────────────┘             
                            │                       
                            ▼                       
                   ┌──────────────────┐             
                   │Analytics Aggr.   │             
                   │   (Container)    │             
                   │   Port 16742     │             
                   └──────────────────┘             
                            │                       
                            ▼                       
                   ┌──────────────────┐             
                   │     Redis        │             
                   │   (Container)    │             
                   │   Port 6379      │             
                   └──────────────────┘             
```

## 🐳 Docker Containers

### Infrastructure Services
- **PostgreSQL**: Database storage for queries and trie data
- **Redis**: Caching and rate limiting
- **Kafka + Zookeeper**: Message streaming for analytics
- **Docker Network**: `autocomplete-net` for service communication

### Application Services  
- **API Gateway**: Go service handling routing and rate limiting
- **Query Service**: Python/FastAPI for autocomplete suggestions
- **Data Collection**: Python/FastAPI for query logging
- **Trie Cache Service**: Go service for optimized trie operations
- **Analytics Aggregator**: Python service for batch processing

### Native Service
- **UI Server**: Python HTTP server (not containerized for easy development)

## 🚀 Quick Start

### Start Complete System
```bash
cd demo
./docker-manager.sh start
```

### Check System Status
```bash
./docker-manager.sh status
```

### View Service Logs
```bash
# View specific service logs
./docker-manager.sh logs query
./docker-manager.sh logs api-gateway
./docker-manager.sh logs data-collection
```

### Stop Everything
```bash
./docker-manager.sh stop
```

## 📊 Service Details

| Service | Container Name | Port | Language | Purpose |
|---------|----------------|------|----------|---------|
| UI Server | (native) | 8080 | Python | Web interface |
| API Gateway | autocomplete-api-gateway | 19845 | Go | Request routing |
| Query Service | autocomplete-query | 17893 | Python | Autocomplete API |
| Data Collection | autocomplete-data-collection | 18761 | Python | Query logging |
| Trie Cache | autocomplete-trie-cache | 18294 | Go | Fast prefix search |
| Analytics | autocomplete-analytics | 16742 | Python | Batch processing |
| PostgreSQL | autocomplete-postgres | 5432 | - | Database |
| Redis | autocomplete-redis | 6379 | - | Cache |
| Kafka | autocomplete-kafka | 9092 | - | Message queue |
| Zookeeper | autocomplete-zookeeper | 2181 | - | Kafka coordinator |

## 🔄 Docker Commands Reference

### Basic Operations
```bash
# Start everything
./docker-manager.sh start

# Stop everything  
./docker-manager.sh stop

# Restart system
./docker-manager.sh restart

# Check status
./docker-manager.sh status
```

### Debugging
```bash
# View container logs
./docker-manager.sh logs <service_name>

# Examples:
./docker-manager.sh logs query          # Query Service logs
./docker-manager.sh logs api-gateway    # API Gateway logs
./docker-manager.sh logs analytics      # Analytics Aggregator logs

# Manual Docker commands
docker ps --filter "name=autocomplete-"           # List containers
docker logs -f autocomplete-query                 # Follow Query Service logs
docker exec -it autocomplete-postgres psql -U testuser -d autocomplete_test  # Database access
```

## 🌐 Access URLs

Once started, access the system via:

- **Main UI**: http://localhost:8080
- **API Gateway**: http://localhost:19845/health
- **Direct Service Access**:
  - Query Service: http://localhost:17893/health
  - Data Collection: http://localhost:18761/health
  - Trie Cache: http://localhost:18294/health
  - Analytics: http://localhost:16742/health

## 🔧 Configuration

### Environment Variables (automatically set)
```bash
# For Python services
DB_HOST=autocomplete-postgres
REDIS_HOST=autocomplete-redis
KAFKA_BROKERS=autocomplete-kafka:29092

# For Go services  
REDIS_HOST=autocomplete-redis
DB_HOST=autocomplete-postgres
QUERY_SERVICE_HOST=autocomplete-query
DATA_COLLECTION_HOST=autocomplete-data-collection
```

### Network Communication
- All containers communicate via Docker network `autocomplete-net`
- Host ports are mapped for external access
- Services use container names for internal communication

## 🐛 Troubleshooting

### Services Not Starting
```bash
# Check if ports are in use
lsof -i :8080 :19845 :17893 :18761 :18294 :16742 :5432 :6379 :9092

# Check container status
docker ps --filter "name=autocomplete-"

# View container logs for errors
./docker-manager.sh logs <service_name>
```

### Database Issues
```bash
# Connect to PostgreSQL container
docker exec -it autocomplete-postgres psql -U testuser -d autocomplete_test

# Check tables
\dt

# View query data
SELECT * FROM query_frequencies LIMIT 5;
SELECT * FROM trie_data LIMIT 5;
```

### Kafka Issues
```bash
# Check Kafka topics
docker exec -it autocomplete-kafka kafka-topics --bootstrap-server localhost:9092 --list

# View Kafka logs
./docker-manager.sh logs kafka
```

### Performance Issues
- **Cold Start**: First startup takes longer as images are downloaded and built
- **Resource Usage**: Monitor with `docker stats`
- **Network Latency**: Services communicate via Docker network (minimal overhead)

## 🎯 Benefits of Docker Deployment

✅ **Isolation**: Each service runs in its own container  
✅ **Consistency**: Same environment across different machines  
✅ **Easy Scaling**: Can easily scale individual services  
✅ **Development**: UI remains native for easy frontend development  
✅ **Debugging**: Individual container logs and access  
✅ **Infrastructure**: Complete infrastructure stack included  
✅ **Networking**: Automatic service discovery via container names  

## 🚨 Important Notes

- **UI Server**: Runs natively (not containerized) for easier development
- **Data Persistence**: Database data is not persisted between container restarts
- **Resource Requirements**: Requires Docker and sufficient RAM for all containers
- **Port Conflicts**: Ensure ports 5432, 6379, 9092, 8080, 17893, 18761, 18294, 16742, 19845 are available
- **Startup Time**: Initial startup may take 2-3 minutes for all services to initialize

This Docker setup provides a complete production-like environment for the search autocomplete system!