# Quick Setup Guide

## 🚀 One-Command Start (Docker)

```bash
# Clone and start everything
git clone <your-repo-url>
cd essential-wallet-system
./start.sh
```

## 📦 What's Included

### ✅ 5 Working Features
1. **User Login** - JWT authentication
2. **Create Wallet** - Multi-wallet per user  
3. **Deposit Money** - Add funds
4. **Withdraw Money** - Remove funds with validation
5. **Transaction History** - View all transactions

### 🏗️ Architecture
- **6 Microservices** (API Gateway, User, Wallet, Transaction, Event, Frontend)
- **PostgreSQL** databases (one per service)
- **Redis** for rate limiting
- **Kafka** for event logging
- **React** frontend

## 🎯 Test the System

### Option 1: Use the UI
1. Open http://localhost:3000/demo/working
2. Register → Login → Create Wallet → Deposit → Withdraw → View History

### Option 2: Use API
```bash
# Register
curl -X POST http://localhost:9080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "full_name": "Test User"}'

# Login (save the token)
curl -X POST http://localhost:9080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

## 🛠️ Manual Setup

### Backend (Docker Compose)
```bash
cd deployments
docker-compose up -d
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

## 📊 Architecture Diagram

```
Frontend (React:3000)
         ↓
API Gateway (9080) → Redis (Rate Limiting)
         ↓
    Microservices
    ├── User Service (9081) → PostgreSQL
    ├── Wallet Service (9082) → PostgreSQL
    ├── Transaction Service (9083) → PostgreSQL
    └── Event Service (9085) → Kafka
```

## 🔍 Health Checks

```bash
# Check all services
curl http://localhost:9080/api/v1/health/services

# View logs
docker-compose logs -f api-gateway
docker-compose logs -f transaction-service
```

## 💡 Key Files

- `services/*/main.py` - Service implementations
- `frontend/WorkingDemo.jsx` - Complete UI component
- `deployments/docker-compose.yml` - Full stack deployment
- `shared/models/base.py` - Data models
- `shared/utils/` - Common utilities

## 🚨 Common Issues

### Port Already in Use
```bash
# Stop existing containers
docker-compose down
docker stop $(docker ps -aq)
```

### Database Connection Failed
```bash
# Restart services
docker-compose restart
```

### Frontend Not Loading
```bash
# Check if backend is ready
curl http://localhost:9080/health
```

## 📝 Notes

- Simplified implementation for demonstration
- Events logged to Kafka (not full event sourcing)
- Rate limiting: 10 req/min (auth), 100 req/min (default)
- Test credentials: `deposit_test@example.com` / `test123`