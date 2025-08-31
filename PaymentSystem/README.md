# Payment System Demo

A comprehensive distributed payment system demonstration with real microservices, proper data flow, UI dashboard, and distributed tracing.

## 🎯 Demo Features

### Microservices Architecture
- **Payment Service**: Core payment processing with real database
- **Wallet Service**: Digital wallet management with transaction history
- **Fraud Detection Service**: ML-based fraud scoring and risk assessment
- **Reconciliation Service**: Automated payment reconciliation and settlement
- **Notification Service**: Multi-channel notifications (email, SMS, webhooks, WebSocket)
- **Ledger Service**: Double-entry bookkeeping system
- **PSP Gateway**: Payment service provider integration
- **API Gateway**: Unified API endpoint

### Infrastructure & Observability
- **PostgreSQL**: Separate databases for each service
- **Redis**: Caching and session management
- **RabbitMQ**: Message queue for async processing  
- **Jaeger**: Distributed tracing across all services
- **Docker Compose**: Full containerized deployment

### User Interface
- **React Dashboard**: Real-time metrics and management interface
- **WebSocket**: Live transaction feed
- **Material-UI**: Professional UI components
- **Charts**: Real-time data visualization

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 8GB RAM available
- Ports 3000, 8733-8743, 5439-5444, 6385-6387, 15672, 16686 available

### Launch Demo
```bash
# Start the complete system
cd demo
chmod +x scripts/start-demo.sh
./scripts/start-demo.sh
```

This will:
1. Clean up any existing containers
2. Start all infrastructure services (databases, message queue, tracing)
3. Launch all microservices with proper dependencies
4. Start the React UI dashboard
5. Run comprehensive end-to-end tests
6. Display all access points

### Access Points
- **Dashboard UI**: http://localhost:3000
- **API Gateway**: http://localhost:8733
- **Jaeger Tracing**: http://localhost:16686
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

## 🎪 Customer Demo Scenarios

### 1. Real-Time Payment Processing
```bash
# Create a wallet
curl -X POST http://localhost:8740/api/v1/wallets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "currency": "USD",
    "initial_balance": 1000.00,
    "wallet_type": "personal"
  }'

# Process a payment
curl -X POST http://localhost:8733/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user", 
    "amount": 99.99,
    "currency": "USD",
    "payment_method": "card",
    "description": "Demo purchase"
  }'
```

### 2. Fraud Detection Demo
```bash
# Trigger fraud detection with high-risk transaction
curl -X POST http://localhost:8733/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "new_user",
    "amount": 15000.00,
    "currency": "USD",
    "payment_method": "card",
    "ip_address": "192.168.1.100",
    "billing_country": "US", 
    "shipping_country": "RU",
    "description": "High-risk purchase"
  }'

# Check fraud alerts
curl http://localhost:8742/api/v1/fraud/alerts
```

### 3. Wallet Operations
```bash
# Transfer between wallets
curl -X POST http://localhost:8740/api/v1/wallets/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "from_wallet_id": "WLT001",
    "to_wallet_id": "WLT002",
    "amount": 100.00,
    "description": "P2P transfer demo"
  }'

# Check wallet balance and history
curl http://localhost:8740/api/v1/wallets/WLT001/transactions
```

### 4. Reconciliation Process
```bash
# Start reconciliation
curl -X POST http://localhost:8741/api/v1/reconciliations \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-02T00:00:00Z", 
    "reconciliation_type": "daily"
  }'

# View reconciliation results
curl http://localhost:8741/api/v1/reconciliations/stats/summary
```

## 📊 Monitoring & Observability

### Distributed Tracing
- All services instrumented with OpenTelemetry
- View end-to-end request traces in Jaeger UI
- Service dependency mapping
- Performance bottleneck identification

### Real-time Metrics
- Payment success/failure rates
- Fraud detection accuracy
- Wallet transaction volumes
- System performance metrics
- Service health monitoring

### Dashboard Features
- Live transaction feed
- Fraud risk distribution charts
- Payment volume analytics
- System health indicators
- Real-time notifications

## 🏗️ Architecture

### Data Flow
1. **Payment Request** → API Gateway → Payment Service
2. **Fraud Check** → Fraud Detection Service (ML scoring)
3. **Wallet Debit** → Wallet Service (atomicpersistency)
4. **Ledger Entry** → Ledger Service (double-entry)
5. **PSP Processing** → PSP Gateway → External PSP
6. **Notifications** → Notification Service → Multiple channels
7. **Reconciliation** → Reconciliation Service → Discrepancy detection

### Service Communication
- **Synchronous**: HTTP/REST with circuit breakers
- **Asynchronous**: RabbitMQ message queues
- **Real-time**: WebSocket connections
- **Tracing**: OpenTelemetry context propagation

### Data Persistence
- **Payment DB**: PostgreSQL (payment_db)
- **Wallet DB**: PostgreSQL (wallet_db) 
- **Fraud DB**: PostgreSQL (fraud_db)
- **Reconciliation DB**: PostgreSQL (reconciliation_db)
- **Notification DB**: PostgreSQL (notification_db)
- **Ledger DB**: PostgreSQL (ledger_db)
- **Cache**: Redis (multiple instances)

## 🧪 Testing

### Manual Testing
```bash
# Run comprehensive test suite
./scripts/test-payment-flow.sh
```

### Test Scenarios Covered
- ✅ Wallet creation and management
- ✅ Payment processing (success/failure)
- ✅ Fraud detection and alerts
- ✅ P2P transfers
- ✅ Reconciliation processing
- ✅ Notification delivery
- ✅ System health checks
- ✅ Concurrent payment processing
- ✅ Distributed tracing verification

## 🔧 Configuration

### Environment Variables
- Database connections for each service
- Service URLs and ports
- Jaeger tracing configuration
- Message queue settings
- Feature flags

### Scaling
- Horizontal scaling support for all services
- Load balancing ready
- Database connection pooling
- Message queue clustering
- Cache distributed setup

## 🎁 Customer Value Propositions

### 1. **Enterprise-Ready Architecture**
- Microservices with proper separation of concerns
- Database per service pattern
- Event-driven architecture
- Circuit breaker patterns

### 2. **Real-Time Fraud Protection**
- ML-based risk scoring
- Velocity checks and pattern analysis
- Real-time alerts and blocking
- Blacklist management

### 3. **Comprehensive Reconciliation**
- Automated discrepancy detection
- Multi-PSP reconciliation support
- Settlement batch processing
- Audit trail and reporting

### 4. **Operational Excellence** 
- Full distributed tracing
- Real-time monitoring and alerting  
- Multi-channel notifications
- Professional admin dashboard

### 5. **Developer Experience**
- Well-documented APIs
- Comprehensive test coverage
- Docker-based deployment
- Tracing for troubleshooting

## 🛟 Troubleshooting

### Service Health Checks
```bash
# Check all service health
curl http://localhost:8733/health  # API Gateway
curl http://localhost:8734/health  # Payment Service
curl http://localhost:8740/health  # Wallet Service
curl http://localhost:8742/health  # Fraud Detection
curl http://localhost:8741/health  # Reconciliation
curl http://localhost:8743/health  # Notification Service
```

### View Service Logs
```bash
docker-compose logs -f payment-service
docker-compose logs -f wallet-service
docker-compose logs -f fraud-detection-service
```

### Reset Demo Data
```bash
docker-compose down -v  # Removes all data
./scripts/start-demo.sh  # Fresh start
```

## 📞 Demo Support

This demo showcases:
- **Real microservices** (no stubs or mocks)
- **Actual database operations** with ACID compliance
- **Distributed tracing** across all components
- **Production-ready patterns** and practices
- **Comprehensive test coverage**
- **Professional UI/UX** for business users

Perfect for demonstrating modern payment system architecture to customers, stakeholders, and technical teams.

---

🎯 **Ready to ship to customers for demonstration!**