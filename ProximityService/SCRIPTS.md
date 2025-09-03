# 📜 Available Demo Scripts

## Main Demo Scripts

### Complete Demo (Recommended)
- **`./start-full-demo.sh`** - Start backend services + UI together
- **`./stop-full-demo.sh`** - Stop everything together

### Separate Control
- **`./start-demo.sh`** - Start backend services only (Docker containers)
- **`./stop-demo.sh`** - Stop backend services only
- **`./start-ui.sh`** - Start UI server only (Python HTTP server)
- **`./stop-ui.sh`** - Stop UI server only

### Testing & Validation
- **`./test-demo.sh`** - Test all functionality after startup

## What Each Script Does

### `start-full-demo.sh`
- Runs `start-demo.sh` followed by `start-ui.sh`
- Complete demo setup in one command
- Best for full demonstrations

### `start-demo.sh`
- Stops existing containers
- Builds all Docker services
- Starts backend infrastructure:
  - PostgreSQL (primary + 2 replicas)
  - Redis (master + 2 replicas + sentinels)
  - API Gateway, Location Service, Business Service
  - Cache Warmer
- Generates demo data (50 businesses)
- Health checks all services

### `start-ui.sh`
- Checks if backend is running (warns if not)
- Kills existing UI server if running
- Starts Python HTTP server on port 8081
- Serves the interactive demo UI
- Runs in background with PID tracking

### `stop-demo.sh`
- Shows current containers
- Stops all Docker containers
- Removes containers (keeps volumes)
- Preserves data for next startup

### `stop-ui.sh`
- Finds UI server process
- Gracefully stops Python HTTP server
- Force kills if needed
- Cleans up PID tracking

### `test-demo.sh`
- Waits for services to be ready
- Tests search functionality
- Tests business creation
- Tests API Gateway
- Tests health endpoints
- Tests rate limiting
- Provides test results summary

## Usage Examples

```bash
# Full demo for presentation
./start-full-demo.sh
# ... give demo ...
./stop-full-demo.sh

# Development workflow
./start-demo.sh      # Terminal 1: Backend
./start-ui.sh        # Terminal 2: UI (optional)
# ... develop/test ...
./stop-ui.sh         # Terminal 2
./stop-demo.sh       # Terminal 1

# Testing after changes
./start-full-demo.sh
./test-demo.sh       # Validate everything works
./stop-full-demo.sh

# Quick backend-only testing
./start-demo.sh
curl "http://localhost:7891/api/v1/search/nearby?latitude=37.7749&longitude=-122.4194&radius=1000"
./stop-demo.sh
```

## File Artifacts

### Generated Files
- `.ui.pid` - UI server process ID (auto-cleaned)
- `ui.log` - UI server access logs
- Docker volumes (databases persist between runs)

### Cleanup
```bash
# Remove all demo artifacts
./stop-full-demo.sh
docker-compose down -v --rmi all
rm -f .ui.pid ui.log
```

## Troubleshooting

### Port Conflicts
```bash
# Check what's using ports
lsof -i :8081   # UI
lsof -i :7891   # API Gateway
lsof -i :8921   # Location Service
lsof -i :9823   # Business Service

# Kill conflicting processes
kill -9 [PID]
```

### Service Issues
```bash
# Check container status
docker-compose ps

# View service logs
docker-compose logs -f [service-name]

# Clean restart
docker-compose down -v --rmi all
./start-full-demo.sh
```

### UI Server Issues
```bash
# Check UI logs
tail -f ui.log

# Manual cleanup
pkill -f "python3.*http.server.*8081"
rm -f .ui.pid
```