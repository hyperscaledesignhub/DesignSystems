# Stock Exchange Microservices Data Flow

## Current Architecture Overview

Based on our tracing demo, here's the exact data flow through the system:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                               │
│                              Port: 3000                                     │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │ HTTP REST API
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT GATEWAY                                    │
│                              Port: 8347                                     │
│  • Authentication & Authorization                                           │
│  • Request Routing & Load Balancing                                         │
│  • Rate Limiting & CORS                                                     │
│  • API Aggregation                                                          │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │ Service-to-Service Communication
        ┌─────────────────┼─────────────────┬─────────────────┐
        ▼                 ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│USER SERVICE │  │ORDER MANAGER│  │WALLET SERVICE│  │REPORTING SVC│
│Port: 8975   │  │Port: 8426   │  │Port: 8651   │  │Port: 9127   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
        │                 │                 │                 │
        ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           POSTGRESQL DATABASE                               │
│                              Port: 5432                                     │
│  Tables: users, wallets, orders, transactions, executions                   │
└─────────────────────────────────────────────────────────────────────────────┘

        ┌─────────────────┬─────────────────┬─────────────────┐
        ▼                 ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│RISK MANAGER │  │MATCHING ENG │  │MARKET DATA  │  │NOTIFICATION │
│Port: 8539   │  │Port: 8792   │  │Port: 8864   │  │Port: 9243   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
        │                 │                 │                 │
        ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               REDIS CACHE                                   │
│                              Port: 6379                                     │
│  • Real-time messaging (Pub/Sub)                                           │
│  • Cache user sessions & market data                                        │
│  • Order book state                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

        ┌─────────────────────────────────────────────────────────┐
        ▼                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              JAEGER TRACING                                 │
│                              Port: 16686                                    │
│  • Distributed tracing across all services                                 │
│  • Performance monitoring                                                   │
│  • Request flow visualization                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Flow Examples

### 1. User Registration Flow
```
Frontend → Client Gateway → User Service → PostgreSQL
   ↓              ↓              ↓            ↓
  (UI)     (POST /register)  (CREATE user) (INSERT)
```

**Tracing Shows:**
- Total time: ~80ms
- Spans: HTTP request → user validation → password hashing → DB insert

### 2. Login Flow
```
Frontend → Client Gateway → User Service → PostgreSQL
   ↓              ↓              ↓            ↓
(Login UI)  (POST /auth/login) (verify pwd) (SELECT)
                   ↓
               JWT Token ←─────── User Service
                   ↓
               Frontend ←─────── Client Gateway
```

**Tracing Shows:**
- Total time: ~60ms  
- Spans: HTTP request → DB query → password verification → JWT generation

### 3. Add Funds Flow (Most Complex)
```
Frontend → Client Gateway → User Service (verify token)
   ↓              ↓              ↓
(Add Funds)  (POST /wallet/add-funds) (GET /me)
                   ↓              ↓
                   ↓        PostgreSQL (user lookup)
                   ↓              
             Wallet Service ← Client Gateway
                   ↓        (GET /balance/user_id)
             PostgreSQL
                   ↓ (404 - no wallet)
             Client Gateway
                   ↓
             Wallet Service ← (POST /update-balance)
                   ↓
             PostgreSQL (CREATE wallet + transaction)
                   ↓
             Success Response → Client Gateway → Frontend
```

**Tracing Shows:**
- Total time: ~150ms
- Spans: Token verification → Wallet check → Wallet creation → Balance update
- Database transactions visible as separate spans

### 4. Order Placement Flow
```
Frontend → Client Gateway → Order Manager
   ↓              ↓              ↓
(Place Order) (POST /v1/order) (POST /order)
                   ↓              ↓
                   ↓        Risk Manager ← (validate order)
                   ↓              ↓
                   ↓         Redis (check limits)
                   ↓              ↓
                   ↓        Response → Order Manager
                   ↓
             Wallet Service ← (POST /block-funds)
                   ↓
             PostgreSQL (UPDATE wallet)
                   ↓
             Order Manager ← Success
                   ↓
             PostgreSQL (INSERT order)
                   ↓
             Redis ← (PUBLISH order_created)
                   ↓
             Matching Engine ← (consume event)
                   ↓
             In-Memory Order Book
```

**Tracing Shows:**
- Total time: ~200ms
- Complex span tree with parallel operations
- Multiple database transactions
- Redis pub/sub events

## Service Dependencies (What Jaeger Shows)

```
Client Gateway (entry point)
    ├── User Service (authentication)
    ├── Wallet Service (balance management)
    ├── Order Manager (order processing)
    │   ├── Risk Manager (validation)
    │   ├── Wallet Service (funds blocking)
    │   └── Matching Engine (order matching)
    └── Reporting Service (analytics)

All services connect to:
├── PostgreSQL (persistent data)
├── Redis (caching & messaging)
└── Jaeger (tracing)
```

## Performance Insights from Tracing

### Bottlenecks Identified:
1. **Database Queries** - 60-70% of request time
2. **Service-to-Service Calls** - 20-25% of request time  
3. **Application Logic** - 10-15% of request time

### Optimization Opportunities:
1. **Database Connection Pooling** - Reduce connection overhead
2. **Redis Caching** - Cache user data, wallet balances
3. **Async Processing** - Order matching in background
4. **Batch Operations** - Group database writes

## How to View This in Jaeger UI

1. **Go to**: http://localhost:16686
2. **Service**: Select "client-gateway" 
3. **Find Traces**: Click to see recent requests
4. **Click any trace** to see:
   - Timeline view of all service calls
   - Database query times
   - Error locations
   - Service dependency graph

### Key Metrics to Watch:
- **P95 Latency**: Should be < 500ms
- **Error Rate**: Should be < 1%
- **Database Query Time**: Should be < 50ms avg
- **Service Communication**: Should be < 100ms

## Real-Time Monitoring

The tracing system automatically captures:
- Every HTTP request through the gateway
- All database queries with execution time
- Redis operations (get/set/publish)
- Inter-service communication
- Error stack traces
- Business metrics (order counts, trade volumes)

This gives you complete visibility into your distributed system performance!