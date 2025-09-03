# ProximityService - Independent Docker Setup

This setup runs all ProximityService components as independent Docker containers instead of using docker-compose. This approach provides more control and avoids docker-compose build caching issues.

## 🚀 Quick Start

```bash
# Start all services
./start-docker-services.sh

# Check service status
./status-docker-services.sh

# Stop all services
./stop-docker-services.sh
```

## 🏗️ Architecture

The system runs the following independent Docker containers:

### Core Infrastructure
- **postgres-primary** (Port 5832) - Primary PostgreSQL database
- **postgres-replica1** (Port 5833) - PostgreSQL read replica 1
- **postgres-replica2** (Port 5834) - PostgreSQL read replica 2
- **redis-master** (Port 6739) - Redis master cache
- **redis-replica1** (Port 6740) - Redis read replica 1
- **redis-replica2** (Port 6741) - Redis read replica 2
- **redis-sentinel1-3** (Ports 26379-26381) - Redis Sentinel monitoring

### Application Services
- **location-service** (Port 8921) - Geospatial search service
- **business-service** (Port 9823) - Business data management service
- **api-gateway** (Port 7891) - API Gateway and routing
- **cache-warmer** - Background cache warming service

### User Interface
- **Demo UI** (Port 8081) - Interactive web interface (independent Python HTTP server)

## 🔧 Management Commands

### Start Services
```bash
./start-docker-services.sh
```
- Creates custom Docker network (`proximity-network`)
- Creates Docker volumes for data persistence
- Starts all containers in dependency order
- Performs health checks
- Starts UI independently

### Check Status
```bash
./status-docker-services.sh
```
- Shows container status (running/stopped/not found)
- Tests service endpoints
- Shows network and volume status
- Provides management command reference

### Stop Services
```bash
./stop-docker-services.sh
```
- Stops all containers in reverse dependency order
- Removes containers
- Stops UI server
- Removes Docker network
- Preserves data volumes

## 🌐 Service Endpoints

### API Endpoints
- **API Gateway**: http://localhost:7891
- **Business Service**: http://localhost:9823
- **Location Service**: http://localhost:8921
- **Demo UI**: http://localhost:8081

### Health Check Endpoints
```bash
curl http://localhost:8921/health  # Location Service
curl http://localhost:9823/health  # Business Service
curl http://localhost:7891/health  # API Gateway
```

### API Gateway Routes
- `GET /api/v1/search/nearby` - Search for nearby businesses
- `POST /api/v1/businesses` - Create new business
- `GET /api/v1/businesses/{id}` - Get business details
- `PUT /api/v1/businesses/{id}` - Update business
- `DELETE /api/v1/businesses/{id}` - Delete business

## 🐳 Docker Network

All services run on a custom Docker bridge network called `proximity-network`. This allows:
- Service-to-service communication using container names
- Network isolation from other Docker applications
- Consistent networking across container restarts

## 💾 Data Persistence

Data is persisted using Docker volumes:
- `postgres_primary_data` - Primary database data
- `postgres_replica1_data` - Replica 1 database data
- `postgres_replica2_data` - Replica 2 database data
- `redis_master_data` - Redis master data
- `redis_replica1_data` - Redis replica 1 data
- `redis_replica2_data` - Redis replica 2 data

## 🔍 Debugging

### View Container Logs
```bash
docker logs <container-name>
docker logs -f <container-name>  # Follow logs
```

### Execute Commands in Container
```bash
docker exec -it <container-name> /bin/sh
```

### Common Debugging Commands
```bash
# Check Redis
docker exec -it redis-master redis-cli -p 6739 ping

# Check PostgreSQL
docker exec -it postgres-primary pg_isready -p 5832

# Check business service debug endpoint
curl http://localhost:9823/debug-test

# Check network connectivity
docker run --rm --network proximity-network alpine/curl:latest curl http://redis-master:6739
```

## 🚨 Troubleshooting

### Services Won't Start
1. Check if ports are already in use: `netstat -tulpn | grep <port>`
2. Check Docker daemon is running: `docker ps`
3. Check available disk space: `df -h`
4. Review service logs: `docker logs <service-name>`

### UI Not Accessible
1. Check if UI process is running: `ps aux | grep python`
2. Check if port 8081 is free: `lsof -i :8081`
3. Check UI logs: `cat ui.log`

### Database Connection Issues
1. Ensure PostgreSQL is fully started: `docker logs postgres-primary`
2. Check if database is accepting connections: `docker exec postgres-primary pg_isready -p 5832`
3. Verify network connectivity between services

### Cache Issues
1. Check Redis connectivity: `docker exec redis-master redis-cli -p 6739 ping`
2. Verify cache contents: `docker exec redis-master redis-cli -p 6739 keys "*"`
3. Clear cache if needed: `docker exec redis-master redis-cli -p 6739 flushall`

## ✨ Advantages of Independent Docker Setup

1. **No Build Cache Issues** - Each service builds independently
2. **Better Control** - Direct container management without docker-compose abstractions
3. **Easier Debugging** - Clear service boundaries and logging
4. **Flexible Updates** - Update individual services without affecting others
5. **Real Docker Experience** - Learn actual Docker commands and networking

## 🔄 Migration from Docker Compose

If you were previously using docker-compose:

```bash
# Stop docker-compose services
docker-compose down

# Remove docker-compose volumes (optional)
docker-compose down -v

# Start independent services
./start-docker-services.sh
```

## 📝 Notes

- The UI runs independently using Python's built-in HTTP server
- Services use the same ports as the docker-compose setup for compatibility
- All environment variables and configurations are preserved
- Data volumes are persistent across container restarts
- The setup includes proper service startup ordering and health checks