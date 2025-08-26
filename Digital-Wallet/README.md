# Essential Digital Wallet System

This directory contains the minimal, working code for a digital wallet system with 5 core features.

## ✅ Working Features

1. **User Login** - JWT authentication
2. **Create Wallet** - Multi-wallet support per user
3. **Deposit Money** - Add money to wallet
4. **Withdraw Money** - Remove money from wallet with balance validation
5. **Transaction History** - View all transactions for a wallet

## 🏗️ Architecture

### Microservices (6 Services)
- **API Gateway** (Port 9080) - Rate limiting, routing
- **User Service** (Port 9081) - Authentication, user management
- **Wallet Service** (Port 9082) - Wallet CRUD, balance updates
- **Transaction Service** (Port 9083) - Transaction processing, Saga pattern
- **Event Service** (Port 9085) - Event logging to Kafka
- **Frontend** (Port 3000) - React UI

### Infrastructure
- **PostgreSQL** - Primary database for each service
- **Redis** - Rate limiting at API Gateway
- **Kafka + Zookeeper** - Event streaming for audit trail

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend)
- Python 3.11+ (if running locally)
- Go 1.21+ (for event service)

### Start Everything with Docker Compose

```bash
# 1. Navigate to deployments directory
cd deployments

# 2. Start all services
docker-compose up -d

# 3. Wait for services to be ready (about 30 seconds)
docker-compose ps

# 4. Start frontend (in separate terminal)
cd frontend
npm install
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:3000/demo/working
- **API Gateway**: http://localhost:9080/health
- **Service Health**: http://localhost:9080/api/v1/health/services

## 📁 Directory Structure

```
essential-wallet-system/
├── services/
│   ├── api-gateway/        # API Gateway with rate limiting
│   ├── user-service/        # User authentication
│   ├── wallet-service/      # Wallet management
│   ├── transaction-service/ # Transaction processing
│   └── event-service/       # Event logging (Go)
├── frontend/
│   └── WorkingDemo.jsx      # React UI component
├── shared/
│   ├── models/              # Shared data models
│   └── utils/               # Database, auth utilities
├── deployments/
│   ├── docker-compose.yml   # Complete stack deployment
│   ├── Dockerfile.python    # Python services image
│   ├── Dockerfile.go        # Go service image
│   └── init-db.sql         # Database initialization
└── README.md

```

## 🔄 Data Flow

### Login Flow
```
Frontend → API Gateway → User Service → PostgreSQL → JWT Token
```

### Create Wallet Flow
```
Frontend → API Gateway → Wallet Service → User Validation → PostgreSQL
```

### Deposit/Withdraw Flow
```
Frontend → API Gateway → Transaction Service → Wallet Service → PostgreSQL + Kafka
```

## 💻 API Examples

### 1. Register User
```bash
curl -X POST http://localhost:9080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:9080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### 3. Create Wallet
```bash
curl -X POST http://localhost:9080/api/v1/wallets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -d '{
    "user_id": "<USER_UUID>",
    "currency": "USD"
  }'
```

### 4. Deposit Money
```bash
curl -X POST http://localhost:9080/api/v1/deposits \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -d '{
    "wallet_id": "<WALLET_UUID>",
    "amount": 100.00,
    "currency": "USD",
    "idempotency_key": "<UNIQUE_UUID>"
  }'
```

### 5. Get Transaction History
```bash
curl -X GET http://localhost:9080/api/v1/transfers/wallet/<WALLET_UUID> \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

## 🧪 Testing the System

### Using the UI
1. Open http://localhost:3000/demo/working
2. Register with email/password
3. Login with credentials
4. Create a wallet
5. Deposit money
6. Withdraw money
7. View transaction history

### Test Data
- Default test user: `deposit_test@example.com` / `test123`

## 🔧 Environment Variables

### API Gateway
```
USER_SERVICE_URL=http://user-service:9081
WALLET_SERVICE_URL=http://wallet-service:9082
TRANSACTION_SERVICE_URL=http://transaction-service:9083
EVENT_SERVICE_URL=http://event-service:9085
REDIS_HOST=redis
REDIS_PORT=6379
```

### Database Configuration
```
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=<service_name>_service
```

## 🎯 Key Design Patterns

1. **Microservices Architecture** - Service independence
2. **API Gateway Pattern** - Single entry point
3. **Saga Pattern** - Distributed transactions
4. **Database per Service** - Data isolation
5. **Event Logging** - Kafka for audit trail
6. **Rate Limiting** - Redis-based protection

## 📊 Transaction Processing

### Saga Pattern Implementation
- **Deposit**: Credit wallet → Publish event
- **Withdraw**: Validate balance → Debit wallet → Publish event
- **Rollback**: Compensating transactions on failure

### Event Types
- `wallet_credited` - Money added
- `wallet_debited` - Money removed
- `transaction_completed` - Transaction successful
- `transaction_failed` - Transaction failed

## 🚨 Monitoring

### Check Service Health
```bash
# All services status
curl http://localhost:9080/api/v1/health/services

# Individual service logs
docker-compose logs -f api-gateway
docker-compose logs -f transaction-service
```

### View Kafka Events
```bash
docker exec -it docker-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic wallet-events \
  --from-beginning
```

## 🛑 Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## 📝 Notes

- This is a simplified implementation focusing on core functionality
- Production deployment would require additional security, monitoring, and scaling considerations
- Events are logged to Kafka but not used for state reconstruction (not full event sourcing)
- Rate limiting is configured at API Gateway (10 requests/minute for auth, 100/minute default)

## 🤝 Contributing

This is the essential working code extracted from a larger digital wallet system implementation.