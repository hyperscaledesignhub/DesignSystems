# How to Watch Data Flow Across Services with OpenTelemetry

## Overview
This guide shows you exactly how to watch data flow from Service1 → Service2 → Service3 using OpenTelemetry and Jaeger.

## Live Data Flow Monitoring

### Method 1: Jaeger UI (Recommended)

#### Step 1: Access Jaeger Dashboard
```bash
# Open in browser
http://localhost:16686
```

#### Step 2: Select Service and Time Range
1. **Service Dropdown**: Select "client-gateway" (entry point)
2. **Lookback**: Set to "Last 1 hour" 
3. **Limit**: Set to "20 traces"
4. **Click**: "Find Traces"

#### Step 3: View Service Flow
Click any trace to see the complete flow:

```
┌─────────────────────────────────────────────────┐
│ Trace Timeline (left to right = chronological) │
├─────────────────────────────────────────────────┤
│ client-gateway: POST /v1/order     [██████████] │ 150ms
│   ├─ user-service: verify_token    [██]         │ 25ms  
│   ├─ order-manager: create_order   [████████]   │ 90ms
│   │   ├─ risk-manager: validate    [██]         │ 15ms
│   │   ├─ wallet-service: block     [███]        │ 30ms
│   │   │   └─ postgresql: UPDATE    [█]          │ 12ms
│   │   └─ postgresql: INSERT        [██]         │ 18ms
│   └─ redis: publish_event          [█]          │ 8ms
└─────────────────────────────────────────────────┘
```

### Method 2: Real-Time Service Logs

#### Monitor Multiple Services Simultaneously
```bash
# Terminal 1: Watch client-gateway logs
docker logs -f docker-client-gateway-1

# Terminal 2: Watch order-manager logs  
docker logs -f docker-order-manager-1

# Terminal 3: Watch wallet-service logs
docker logs -f docker-wallet-service-1
```

#### Example Log Flow for Order Placement:
```bash
# Terminal 1 (client-gateway):
INFO: 172.18.0.1:54321 - "POST /v1/order HTTP/1.1" 200 OK

# Terminal 2 (order-manager):
INFO: 172.18.0.10:45678 - "POST /order HTTP/1.1" 200 OK
INFO: Validating order for user 11, symbol AAPL
INFO: Sending to risk-manager for validation

# Terminal 3 (wallet-service):  
INFO: 172.18.0.10:34567 - "POST /block-funds HTTP/1.1" 200 OK
INFO: Blocking $776.25 for user 11
```

### Method 3: Database Query Monitoring

#### Watch Database Activity
```bash
# Connect to PostgreSQL and monitor queries
docker exec -it docker-postgres-1 psql -U postgres -d stockexchange

# Enable query logging
SELECT pg_stat_statements_reset();

# In another terminal, make API calls
curl -X POST http://localhost:8347/v1/order ...

# View query stats
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

## Detailed Flow Examples

### 1. Order Placement Flow

#### API Call:
```bash
curl -X POST http://localhost:8347/v1/order \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"symbol":"AAPL","side":"BUY","quantity":10,"price":150}'
```

#### Service Flow in Jaeger:
```
1. client-gateway receives POST /v1/order
   ├─ Span: "place_order" 
   ├─ Tags: symbol=AAPL, side=BUY, quantity=10
   └─ Duration: 150ms
   
2. client-gateway → user-service  
   ├─ Span: "verify_token"
   ├─ HTTP: GET /me
   └─ Duration: 25ms
   
3. client-gateway → order-manager
   ├─ Span: "create_order" 
   ├─ HTTP: POST /order
   └─ Duration: 90ms
   
4. order-manager → risk-manager
   ├─ Span: "validate_order"
   ├─ HTTP: POST /validate  
   └─ Duration: 15ms
   
5. order-manager → wallet-service
   ├─ Span: "block_funds"
   ├─ HTTP: POST /block-funds
   └─ Duration: 30ms
   
6. wallet-service → postgresql  
   ├─ Span: "UPDATE wallets"
   ├─ SQL: UPDATE wallets SET blocked_balance = ...
   └─ Duration: 12ms
```

### 2. Portfolio Query Flow

#### API Call:
```bash
curl -X GET http://localhost:8347/reports/positions \
  -H "Authorization: Bearer $TOKEN"
```

#### Service Flow:
```
1. client-gateway: GET /reports/positions
   └─ reporting-service: get_positions
       └─ postgresql: SELECT with JOINs (complex query)
           └─ redis: cache_result
```

### 3. Add Funds Flow

#### API Call:
```bash
curl -X POST http://localhost:8347/wallet/add-funds \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"amount": 1000}'
```

#### Service Flow:
```
1. client-gateway: POST /wallet/add-funds
   ├─ user-service: GET /me (verify user)
   ├─ wallet-service: GET /balance (check existing)
   │   └─ postgresql: SELECT FROM wallets
   └─ wallet-service: POST /update-balance
       ├─ postgresql: INSERT wallet (if new)
       └─ postgresql: INSERT transaction
```

## Advanced Monitoring Techniques

### 1. Trace Correlation

#### Find Related Traces:
```bash
# In Jaeger UI, use the "Find Traces" with:
- Tags: user_id=11
- Tags: order_id=abc-123  
- Tags: error=true (for errors only)
```

### 2. Performance Analysis

#### Identify Bottlenecks:
1. **Sort traces by duration** (longest first)
2. **Look for patterns** in slow traces
3. **Check database spans** (usually longest)
4. **Identify retry patterns**

### 3. Error Tracking

#### Find Failed Requests:
```bash
# Filter traces with errors
Tags: error=true

# Look for:
- HTTP 4xx/5xx status codes
- Database connection failures  
- Timeout errors
- Service unavailable errors
```

## Real-Time Dashboard

### Create Custom Views in Jaeger:

#### 1. Service Map View
- Shows service dependencies
- Updates in real-time
- Color-coded by health

#### 2. Operation View  
- Lists all endpoints
- Shows P50/P95/P99 latencies
- Error rates per endpoint

#### 3. Trace Search
- Search by user_id, order_id
- Filter by time ranges
- Find specific error patterns

## Automated Monitoring

### Set Up Alerts:

#### 1. Latency Alerts
```bash
# Alert when P95 > 500ms
jaeger_trace_duration{quantile="0.95"} > 500
```

#### 2. Error Rate Alerts  
```bash
# Alert when error rate > 1%
jaeger_trace_error_rate > 0.01
```

#### 3. Service Availability
```bash
# Alert when service missing traces
absent(jaeger_traces{service="order-manager"})
```

## Troubleshooting Data Flow

### Common Issues:

#### 1. Missing Traces
- Check service logs for OpenTelemetry errors
- Verify Jaeger endpoint configuration
- Check network connectivity

#### 2. Incomplete Traces
- Missing context propagation headers
- Services not instrumented  
- Sampling rate too low

#### 3. Performance Issues
- Database queries too slow
- Too many service calls
- Missing caching

## Best Practices

### 1. Structured Logging
```python
# Add correlation IDs to logs
logging.info("Processing order", extra={
    "trace_id": trace.get_current_span().get_span_context().trace_id,
    "user_id": user_id,
    "order_id": order_id
})
```

### 2. Business Metrics
```python
# Track business events in spans
span.set_attribute("order.value", order_total)
span.set_attribute("user.tier", "premium")
span.add_event("payment_processed", {"amount": payment_amount})
```

### 3. Error Context
```python
# Add error details to spans
try:
    process_order()
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)))
```

## Quick Reference Commands

```bash
# Generate test traces
./trace_demo.sh

# View Jaeger UI
open http://localhost:16686

# Check service health
curl http://localhost:8347/health

# Monitor logs in real-time
docker-compose logs -f client-gateway order-manager wallet-service

# Query database activity
docker exec docker-postgres-1 psql -U postgres -d stockexchange -c "
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables 
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;"
```

This gives you complete visibility into how data flows through your microservices architecture!