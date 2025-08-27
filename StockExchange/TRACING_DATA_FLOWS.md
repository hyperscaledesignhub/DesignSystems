# Microservices Data Flow Visualization with Tracing

## Overview
This document shows the exact data flow through our microservices architecture as captured by distributed tracing with Jaeger.

## How to View Traces

1. **Open Jaeger UI**: http://localhost:16686
2. **Select Service**: Choose "client-gateway" from dropdown
3. **Find Traces**: Click "Find Traces" button
4. **View Details**: Click on any trace to see the complete flow

## Data Flow Patterns

### 1. User Registration Flow
```
[Frontend] 
    ↓ HTTP POST /auth/register
[Client Gateway] 
    ↓ HTTP POST /register
[User Service]
    ↓ SQL INSERT
[PostgreSQL Database]
```

**Trace Visualization in Jaeger:**
- Total Duration: ~50-100ms
- Spans:
  - `client-gateway: POST /auth/register` (parent)
  - `user-service: register_user`
  - `postgresql: INSERT INTO users`

---

### 2. User Login Flow
```
[Frontend]
    ↓ HTTP POST /auth/login
[Client Gateway]
    ↓ HTTP POST /login
[User Service]
    ↓ SQL SELECT (verify user)
[PostgreSQL Database]
    ↓ JWT Generation
[User Service]
    ↓ Response with token
[Client Gateway]
```

**Trace Visualization in Jaeger:**
- Total Duration: ~30-60ms
- Spans:
  - `client-gateway: POST /auth/login`
  - `user-service: authenticate_user`
  - `postgresql: SELECT FROM users`
  - `jwt: generate_token`

---

### 3. Wallet Creation & Funding Flow
```
[Frontend]
    ↓ HTTP POST /wallet/add-funds
[Client Gateway]
    ↓ HTTP GET /me (verify user)
[User Service]
    ↓ Response with user_id
[Client Gateway]
    ↓ HTTP GET /balance/{user_id} (check wallet)
[Wallet Service]
    ↓ SQL SELECT
[PostgreSQL] (returns 404 if no wallet)
    ↓
[Client Gateway]
    ↓ HTTP POST /update-balance/{user_id}
[Wallet Service]
    ↓ SQL INSERT (create wallet if not exists)
    ↓ SQL INSERT (transaction record)
[PostgreSQL Database]
```

**Trace Visualization in Jaeger:**
- Total Duration: ~80-150ms
- Spans:
  - `client-gateway: POST /wallet/add-funds`
    - `user-service: GET /me`
    - `wallet-service: GET /balance/13`
      - `postgresql: SELECT FROM wallets`
    - `wallet-service: POST /update-balance/13`
      - `postgresql: INSERT INTO wallets` (if new)
      - `postgresql: UPDATE wallets`
      - `postgresql: INSERT INTO transactions`

---

### 4. Order Placement Flow (Most Complex)
```
[Frontend]
    ↓ HTTP POST /v1/order
[Client Gateway]
    ↓ HTTP POST /order
[Order Manager]
    ↓ HTTP POST /validate (risk check)
[Risk Manager]
    ↓ Redis GET (check limits)
[Redis Cache]
    ↓ Response (approved/rejected)
[Order Manager]
    ↓ HTTP POST /block-funds
[Wallet Service]
    ↓ SQL UPDATE (block funds)
[PostgreSQL Database]
    ↓ Response
[Order Manager]
    ↓ SQL INSERT (create order)
[PostgreSQL Database]
    ↓ Redis PUBLISH (order event)
[Redis PubSub]
    ↓ Event consumed
[Matching Engine]
    ↓ Order Book Update
[In-Memory Order Book]
    ↓ Redis PUBLISH (market data)
[Market Data Service]
```

**Trace Visualization in Jaeger:**
- Total Duration: ~100-200ms
- Spans:
  - `client-gateway: POST /v1/order`
    - `order-manager: POST /order`
      - `risk-manager: validate_order`
        - `redis: GET risk_limits`
      - `wallet-service: block_funds`
        - `postgresql: UPDATE wallets`
        - `postgresql: INSERT transactions`
      - `postgresql: INSERT INTO orders`
      - `redis: PUBLISH order_created`
      - `matching-engine: process_order`
        - `orderbook: add_order`
        - `redis: PUBLISH market_data`

---

### 5. Order Query Flow
```
[Frontend]
    ↓ HTTP GET /v1/orders
[Client Gateway]
    ↓ HTTP GET /orders/user/{user_id}
[Order Manager]
    ↓ SQL SELECT
[PostgreSQL Database]
    ↓ Response with orders
[Client Gateway]
```

**Trace Visualization in Jaeger:**
- Total Duration: ~20-40ms
- Spans:
  - `client-gateway: GET /v1/orders`
    - `order-manager: get_user_orders`
      - `postgresql: SELECT FROM orders WHERE user_id = ?`

---

### 6. Portfolio Reporting Flow
```
[Frontend]
    ↓ HTTP GET /reports/positions
[Client Gateway]
    ↓ HTTP GET /positions/{user_id}
[Reporting Service]
    ↓ SQL Query (complex JOIN)
[PostgreSQL Database]
    ↓ Aggregation
[Reporting Service]
    ↓ Response with positions
[Client Gateway]
```

**Trace Visualization in Jaeger:**
- Total Duration: ~40-80ms
- Spans:
  - `client-gateway: GET /reports/positions`
    - `reporting-service: get_positions`
      - `postgresql: SELECT (complex aggregation query)`
      - `reporting-service: calculate_pnl`

---

### 7. Order Cancellation Flow
```
[Frontend]
    ↓ HTTP DELETE /v1/order/{order_id}
[Client Gateway]
    ↓ HTTP DELETE /order/{order_id}
[Order Manager]
    ↓ SQL SELECT (verify order)
[PostgreSQL Database]
    ↓ HTTP POST /unblock-funds
[Wallet Service]
    ↓ SQL UPDATE (release funds)
[PostgreSQL Database]
    ↓ SQL UPDATE (cancel order)
[Order Manager]
    ↓ Redis PUBLISH (cancellation event)
[Matching Engine]
    ↓ Order Book Update
[In-Memory Order Book]
```

**Trace Visualization in Jaeger:**
- Total Duration: ~60-100ms
- Spans:
  - `client-gateway: DELETE /v1/order/{id}`
    - `order-manager: cancel_order`
      - `postgresql: SELECT FROM orders`
      - `wallet-service: unblock_funds`
        - `postgresql: UPDATE wallets`
      - `postgresql: UPDATE orders SET status = CANCELLED`
      - `redis: PUBLISH order_cancelled`
      - `matching-engine: remove_order`

---

## Trace Analysis Features

### Performance Metrics
In Jaeger, you can see:
- **Latency per Service**: How long each service takes
- **Database Query Time**: Actual SQL execution time
- **Network Overhead**: Time spent in service-to-service calls
- **Bottlenecks**: Which service/operation is slowest

### Dependency Graph
Jaeger provides a dependency graph showing:
```
                    Client Gateway
                    /      |      \
                   /       |       \
            User Service  Order    Wallet
                |        Manager   Service
                |          |         |
            PostgreSQL     |     PostgreSQL
                      Risk Manager
                           |
                        Redis
```

### Error Tracking
Failed requests show:
- Which service failed
- Error message in span tags
- Full stack trace of failures
- Retry attempts

## Viewing Specific Traces

### To see Order Placement flow:
1. Go to Jaeger UI: http://localhost:16686
2. Service: `client-gateway`
3. Operation: `POST /v1/order`
4. Click "Find Traces"
5. Click on any trace to see full flow

### To see the Service Dependencies:
1. Go to Jaeger UI
2. Click "Dependencies" tab
3. Select time range
4. View the service dependency graph

### To analyze performance:
1. Go to Jaeger UI
2. Click "Compare" tab
3. Select two traces
4. Compare latencies

## Key Insights from Tracing

### 1. Database is Often the Bottleneck
- Most time spent in PostgreSQL queries
- Wallet updates are serialized (potential bottleneck)

### 2. Service Communication Pattern
- Client Gateway is the single entry point
- Services don't call each other directly (except Order Manager)
- Redis is used for async communication

### 3. Transaction Boundaries
- Each HTTP request is a transaction
- Database transactions are clearly visible
- Distributed transactions span multiple services

### 4. Performance Optimization Opportunities
- Cache user data in Redis
- Batch database operations
- Async processing for non-critical paths

## Sample Trace IDs

After running the demo script, you'll have traces for:
- Registration: Look for `POST /auth/register`
- Login: Look for `POST /auth/login`
- Add Funds: Look for `POST /wallet/add-funds`
- Place Order: Look for `POST /v1/order`
- Cancel Order: Look for `DELETE /v1/order`

## Monitoring Dashboard

To create a monitoring dashboard:
1. Use Jaeger metrics
2. Track P50, P95, P99 latencies
3. Monitor error rates per service
4. Set up alerts for slow traces (>500ms)