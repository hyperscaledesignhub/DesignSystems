# Search Autocomplete System - Deployment Options

Complete search autocomplete system with multiple deployment options for different use cases.

## 📋 Overview

This demo provides **two deployment methods** for the complete search autocomplete system:

1. **Native Deployment** - All services run natively on localhost
2. **Docker Deployment** - All services (except UI) run in individual Docker containers

## 🏃 Quick Start Guide

### Option 1: Native Deployment (Recommended for Development)

```bash
# Prerequisites: Start infrastructure services
brew services start postgresql
brew services start redis  
brew services start kafka

# Start all services
./start_demo.sh

# Access UI: http://localhost:8080
```

### Option 2: Docker Deployment (Recommended for Production)

```bash
# No prerequisites needed - Docker handles everything
./docker-manager.sh start

# Access UI: http://localhost:8080
```

## 📊 Comparison

| Aspect | Native Deployment | Docker Deployment |
|--------|-------------------|-------------------|
| **Setup** | Requires manual infrastructure setup | Fully automated |
| **Performance** | Fastest (native execution) | Slightly slower (containerization overhead) |
| **Development** | Best for development/debugging | Good for testing production-like setup |
| **Isolation** | Services share host environment | Complete service isolation |
| **Resource Usage** | Lower memory/CPU usage | Higher resource usage |
| **Portability** | Machine-dependent | Runs anywhere with Docker |
| **Startup Time** | ~30 seconds | ~2-3 minutes (first time) |
| **Debugging** | Direct access to processes | Container logs and exec access |

## 🎯 When to Use Each

### Use Native Deployment When:
- 🔧 **Developing/debugging** individual services
- ⚡ **Performance testing** (no containerization overhead)  
- 💻 **Local development** with frequent code changes
- 📊 **Resource constrained** environments
- 🚀 **Quick demos** and testing

### Use Docker Deployment When:
- 🏭 **Production-like testing** environment needed
- 🐳 **Consistent deployment** across different machines
- 👥 **Team development** with standardized environment  
- 🔒 **Service isolation** requirements
- 📦 **Easy distribution** of the complete system
- ☁️ **Cloud deployment** preparation

## 🛠️ Detailed Instructions

### Native Deployment

#### Prerequisites
```bash
# Install infrastructure services
brew install postgresql redis kafka

# Start infrastructure
brew services start postgresql
brew services start redis
brew services start kafka
```

#### Commands  
```bash
# Start everything
./start_demo.sh

# Stop everything
./stop_demo.sh

# Check individual services
curl http://localhost:17893/health  # Query Service
curl http://localhost:18761/health  # Data Collection
curl http://localhost:16742/health  # Analytics Aggregator
```

### Docker Deployment  

#### Prerequisites
- Docker installed and running
- No other prerequisites needed

#### Commands
```bash  
# Start everything (infrastructure + services)
./docker-manager.sh start

# Check system status
./docker-manager.sh status

# View service logs
./docker-manager.sh logs query
./docker-manager.sh logs api-gateway

# Stop everything
./docker-manager.sh stop

# Restart system
./docker-manager.sh restart
```

## 📈 Service Architecture (Both Deployments)

Both deployments provide the same services and functionality:

```
🌐 Web UI (8080) 
    ↓
🚪 API Gateway (19845)
    ↓
┌─── 🔍 Query Service (17893)
│       ↓
│    📊 Trie Cache Service (18294)
│       ↓  
│    🗄️ PostgreSQL (5432)
│
└─── 📝 Data Collection (18761)
        ↓
     📨 Kafka (9092)  
        ↓
     📊 Analytics Aggregator (16742)
        ↓
     🗄️ PostgreSQL (5432)
```

## 🎛️ Configuration Differences

### Native Deployment
- Services connect to `localhost` infrastructure
- Direct process execution
- Shared host network and filesystem
- Environment variables for localhost connections

### Docker Deployment  
- Services connect to container hostnames (e.g., `autocomplete-postgres`)
- Containerized execution with isolated environments
- Docker network (`autocomplete-net`) for service communication
- Automatic service discovery via container names

## 🚨 Troubleshooting

### Native Deployment Issues
```bash
# Check if infrastructure is running
brew services list | grep -E "(postgresql|redis|kafka)"

# Check port usage
lsof -i :5432 :6379 :9092

# View service logs directly (they run in terminal)
```

### Docker Deployment Issues  
```bash
# Check container status
docker ps --filter "name=autocomplete-"

# View logs
./docker-manager.sh logs <service_name>

# Debug individual containers
docker exec -it autocomplete-postgres psql -U testuser -d autocomplete_test
```

## 💡 Best Practices

### For Development
1. Use **Native Deployment** for day-to-day development
2. Test with **Docker Deployment** before production
3. Use UI server natively in both cases for frontend development

### For Production
1. Use **Docker Deployment** for consistent environments
2. Add persistent volumes for database data  
3. Consider container orchestration (Kubernetes, Docker Swarm)
4. Implement proper logging and monitoring

### For Demos
1. **Native**: Faster startup, better for live coding demos
2. **Docker**: Better for showcasing production readiness

## 📝 Files Structure

```
demo/
├── start_demo.sh           # Native deployment script
├── stop_demo.sh            # Stop native services
├── docker-manager.sh       # Docker deployment manager
├── README.md               # Native deployment guide  
├── README-Docker.md        # Docker deployment guide
├── DEPLOYMENT-OPTIONS.md   # This file
├── ui/
│   ├── index.html         # Web interface
│   └── server.py          # UI server (always native)
└── services/              # All microservices
    ├── query-service/
    ├── data-collection-service/
    ├── trie-cache-service/
    ├── api-gateway/
    └── analytics-aggregator/
```

Both deployment options provide the same complete search autocomplete system with identical functionality and features!