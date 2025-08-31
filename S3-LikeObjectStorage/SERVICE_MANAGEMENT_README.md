# 🛠️ SERVICE MANAGEMENT SCRIPTS

## Overview
Complete set of scripts to manage your S3-like Object Storage System with Docker services and external UI server.

## 📋 Available Scripts

### 🚀 **start_all_services.sh** - Start Everything
```bash
./start_all_services.sh
```
**What it does:**
- ✅ Cleans up any existing services
- 🐳 Creates Docker network (`s3-network`)  
- 🏗️ Builds all Docker images
- 🗄️ Starts PostgreSQL database
- ⚡ Starts all 6 microservices with proper dependencies
- 🌐 Starts Demo UI server (Python) outside Docker
- 🏥 Performs health checks on all services
- 📊 Shows final system status

**Services Started:**
1. PostgreSQL Database (port 5432)
2. Identity Service (port 7851) 
3. Bucket Service (port 7861)
4. Storage Service (port 7881)
5. Metadata Service (port 7891)
6. Object Service (port 7871)
7. API Gateway (port 7841)
8. Demo UI Server (port 8080) - **Runs outside Docker**

### 🛑 **stop_all_services.sh** - Stop Everything  
```bash
./stop_all_services.sh
```
**What it does:**
- 🌐 Stops Demo UI server (Python process)
- 🐳 Stops all Docker containers in dependency order
- 🗑️ Removes stopped containers
- 🧹 Interactive cleanup options:
  - Keep all data (default)
  - Remove network only
  - Remove network + volumes (destroys data)
  - Skip cleanup

### 📊 **check_system_status.sh** - System Health Check
```bash
./check_system_status.sh
```
**What it shows:**
- 🐳 Docker container status (running/stopped)
- 🏥 Service health checks (HTTP endpoints)
- 🌐 Demo UI server status
- 💾 Storage statistics and consistency
- 🔗 Docker resources (network, volumes)
- 📋 Overall system status summary

### 🔄 **restart_all_services.sh** - Full Restart
```bash
./restart_all_services.sh
```
**What it does:**
- Runs stop script → wait 5 seconds → runs start script
- Complete system restart cycle

## 🎯 **Quick Commands**

### Daily Usage
```bash
# Start the system
./start_all_services.sh

# Check if everything is working  
./check_system_status.sh

# Stop when done
./stop_all_services.sh
```

### Troubleshooting
```bash
# Quick storage overview
./quick_storage_check.sh

# Detailed storage analysis  
./inspect_storage.sh

# Restart if having issues
./restart_all_services.sh
```

### Rollback Testing
```bash
# Test transactional rollback
./demo_rollback_1_stop_metadata.sh
./demo_rollback_2_test_requests.sh  
./demo_rollback_3_show_logs.sh
./demo_rollback_4_restart_metadata.sh

# Or run complete demo
./demo_rollback_complete.sh
```

## 📊 **System Architecture**

### Service Dependencies
```
Demo UI Server (Python, port 8080)
    ↓ HTTP calls
API Gateway (port 7841) 
    ↓ Routes to
┌─────────────────────────────────────┐
│  Identity (7851)  │  Bucket (7861)  │
│  Object (7871)    │  Storage (7881) │  
│  Metadata (7891)  │                 │
└─────────────────────────────────────┘
    ↓ All connect to
PostgreSQL Database (port 5432)
```

### Data Persistence
- **PostgreSQL**: Bucket + Object metadata 
- **SQLite**: Identity users + Storage index
- **File System**: Raw object data (UUID partitioned)
- **Docker Volumes**: `postgres_data`, `identity_data`, `storage_data`

## 🔍 **System Status Indicators**

### ✅ **Fully Operational**
- All 7 containers running
- All 6 services healthy  
- Demo UI accessible
- Storage consistent

### ⚠️ **Partially Operational** 
- Some containers running
- Some services healthy
- May have storage inconsistencies

### ❌ **Not Operational**
- Most/all services down
- Cannot access Demo UI
- Cannot check storage

## 🛡️ **Safety Features**

### Data Protection
- Interactive confirmation for destructive operations
- Multiple cleanup options (preserve/destroy data)
- Automatic container cleanup before restart
- Health checks prevent false-positive "ready" status

### Error Handling  
- Service startup timeout detection (30 attempts × 2s = 60s max)
- Dependency ordering (database first, API gateway last)
- Graceful failure reporting
- Log file management

## 📝 **Log Files**

### Generated Files
- `ui_server.log` - Demo UI server output
- `ui_server.pid` - UI server process ID
- `startup.log` - Timestamped startup/shutdown events

### Docker Logs
```bash
docker logs <service-name>
docker logs postgres-db
docker logs api-gateway
# etc.
```

## 🎉 **Access Points After Startup**

- **🌐 Demo UI**: http://localhost:8080/demo-ui.html
- **🚪 API Gateway**: http://localhost:7841
- **👤 Identity Service**: http://localhost:7851/health
- **🪣 Bucket Service**: http://localhost:7861/health  
- **📄 Object Service**: http://localhost:7871/health
- **💾 Storage Service**: http://localhost:7881/health
- **📊 Metadata Service**: http://localhost:7891/health
- **🗄️ PostgreSQL**: localhost:5432

## 🚀 **Getting Started**

1. **First Time Setup:**
   ```bash
   ./start_all_services.sh
   ```

2. **Open Demo UI:**
   ```
   http://localhost:8080/demo-ui.html
   ```

3. **Test All Features:**
   - Create buckets
   - Upload/download objects
   - Check health status
   - View storage statistics

4. **When Done:**
   ```bash
   ./stop_all_services.sh
   ```

Your S3-like Object Storage System is now ready for use! 🎯