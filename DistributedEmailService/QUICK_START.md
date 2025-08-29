# 🚀 Distributed Email System - Quick Start Guide

## 📁 Project Structure
All code is present in the `demo/` directory with complete microservices architecture.

## ⚡ Quick Start Commands

### Start All Services
```bash
# Option 1: Quick start (recommended)
./start.sh

# Option 2: Full demo with monitoring
./scripts/start-demo.sh
```

### Stop Services (Multiple Options)

```bash
# Option 1: Quick stop (containers only - fastest restart)
./stop.sh

# Option 2: Clean stop (containers + volumes, keep images)
./stop-clean.sh

# Option 3: Full cleanup with interactive options
./scripts/stop-demo.sh
```

#### Stop Options Explained:
- **`./stop.sh`** - Just stops containers, preserves everything (quickest restart)
- **`./stop-clean.sh`** - Stops containers + removes volumes, keeps images (clean restart)
- **`./scripts/stop-demo.sh`** - Interactive menu with 3 options:
  1. Stop containers only (same as ./stop.sh)
  2. Stop containers + remove volumes (same as ./stop-clean.sh) 
  3. Full cleanup (removes everything including images)

## 🌐 Access Points (After Starting)

### Main Applications
- **🏠 Main UI**: http://localhost:3000
- **🌐 API Gateway**: http://localhost:8000
- **📊 Jaeger Tracing**: http://localhost:16686

### Storage & Infrastructure
- **🗄️ MinIO Console**: http://localhost:9001 (admin/password123)
- **🔍 Elasticsearch**: http://localhost:9200

### Individual Service APIs
- **🔐 Auth Service**: http://localhost:8001/docs
- **📧 Email Service**: http://localhost:8002/docs  
- **🚨 Spam Service**: http://localhost:8003/docs
- **🔔 Notification Service**: http://localhost:8004/docs
- **📎 Attachment Service**: http://localhost:8005/docs
- **🔎 Search Service**: http://localhost:8006/docs

## 👤 Demo Credentials
- **Email**: `demo@example.com`
- **Password**: `password`

## 🎯 Demo Features

### ✅ Core Features Working
1. **Email Management** - Send, receive, search emails
2. **User Authentication** - JWT-based auth with registration/login
3. **Spam Detection** - ML-based spam filtering
4. **Real-time Notifications** - WebSocket notifications when emails sent
5. **Full-text Search** - Elasticsearch-powered email search
6. **File Attachments** - MinIO-based file storage
7. **Distributed Tracing** - OpenTelemetry + Jaeger integration
8. **Service Health** - Health checks for all microservices

### 🏗️ Architecture Highlights
- **7 Microservices** - Independent, scalable services
- **API Gateway** - Centralized routing and authentication
- **Event-Driven** - Async notifications and background tasks
- **Multiple Databases** - PostgreSQL, Redis, Elasticsearch, MinIO
- **Containerized** - Full Docker Compose deployment

## 📋 System Requirements
- Docker & Docker Compose
- 8GB+ RAM recommended
- Ports 3000, 8000-8006, 9000-9001, 5432, 6379, 9200, 16686

## 🛠️ Development Commands

### View Logs
```bash
docker-compose logs -f [service-name]
```

### Rebuild Specific Service  
```bash
docker-compose build [service-name]
docker-compose restart [service-name]
```

### Database Access
```bash
# PostgreSQL
docker-compose exec postgres psql -U emailuser -d emaildb

# Redis
docker-compose exec redis redis-cli
```

## 🎬 Demo Script for Presentations

1. **Start the system**: `./start.sh`
2. **Open UI**: http://localhost:3000
3. **Login**: demo@example.com / password
4. **Show Features**:
   - Send emails (auto-indexed for search)
   - Search functionality 
   - Real-time notifications
   - Service health dashboard
5. **Show Tracing**: http://localhost:16686
6. **API Documentation**: Individual service /docs endpoints

## 🔧 Troubleshooting

### Common Issues
- **Port conflicts**: Stop other services using ports 3000, 8000-8006
- **Memory issues**: Increase Docker memory allocation to 8GB+
- **Services not starting**: Check logs with `docker-compose logs [service]`

### Reset Everything
```bash
./stop.sh
docker system prune -a --volumes -f
./start.sh
```

## 📞 Support
All components are self-contained in the demo directory. Check logs and health endpoints for debugging.