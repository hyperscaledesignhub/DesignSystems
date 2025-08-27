# Distributed Tracing Guide for Stock Exchange Microservices

## Overview
This system uses OpenTelemetry with Jaeger for distributed tracing across all microservices. This allows you to:
- Track requests as they flow through multiple services
- Identify performance bottlenecks
- Debug complex distributed transactions
- Monitor service dependencies

## Architecture

```
                    ┌─────────────┐
                    │   Jaeger    │
                    │   Collector │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼───────┐ ┌───▼──────┐ ┌────▼─────┐
     │Client Gateway│ │  Order   │ │  Wallet  │
     │   (traced)   │ │ Manager  │ │ Service  │
     └──────────────┘ └──────────┘ └──────────┘
```

## Accessing Jaeger UI

1. **Open Jaeger UI**: Navigate to http://localhost:16686
2. **Select Service**: Choose from dropdown (e.g., "client-gateway")
3. **Find Traces**: Click "Find Traces" to see recent requests
4. **View Trace Details**: Click on any trace to see the full request flow

## Key Features Implemented

### 1. Automatic Instrumentation
- FastAPI endpoints are automatically traced
- Database calls (PostgreSQL) are traced
- Redis operations are traced
- HTTP calls between services are traced

### 2. Context Propagation
- Trace context is automatically propagated between services
- Headers are injected/extracted for distributed tracing
- Parent-child span relationships are maintained

### 3. Custom Attributes
Each span includes custom attributes:
- Order details (symbol, side, quantity, price)
- User information
- Service names
- HTTP methods and paths
- Error details

## Trace Examples

### Order Placement Flow
```
client-gateway: POST /v1/order
├── user-service: verify_token
├── wallet-service: check_balance
├── risk-manager: validate_order
├── order-manager: create_order
│   ├── database: INSERT order
│   └── redis: publish_event
└── matching-engine: match_order
```

### User Login Flow
```
client-gateway: POST /auth/login
└── user-service: authenticate
    ├── database: SELECT user
    └── jwt: generate_token
```

## Testing Tracing

### 1. Generate Sample Traces

```bash
# Login
curl -X POST http://localhost:8347/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo_user", "password": "demo123"}'

# Place Order
TOKEN="your_jwt_token"
curl -X POST http://localhost:8347/v1/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "quantity": 10,
    "price": 150.00
  }'

# Get Portfolio
curl -X GET http://localhost:8347/reports/positions \
  -H "Authorization: Bearer $TOKEN"
```

### 2. View in Jaeger

1. Go to http://localhost:16686
2. Select service: "client-gateway"
3. Click "Find Traces"
4. Click on any trace to see details

## Trace Interpretation

### Span Details
- **Operation Name**: The specific function or endpoint
- **Duration**: Time taken by this operation
- **Tags**: Metadata about the operation
- **Logs**: Events that occurred during the span

### Performance Analysis
- Look for slow operations (long duration spans)
- Identify sequential vs parallel operations
- Check for repeated database calls
- Monitor external service latencies

## Adding Tracing to New Services

### 1. Import Tracing Module
```python
from shared.tracing import setup_tracing, instrument_fastapi

# Setup tracing
tracer = setup_tracing("service-name")

# Instrument FastAPI
app = FastAPI()
instrument_fastapi(app)
```

### 2. Add Custom Spans
```python
from opentelemetry import trace

tracer = trace.get_tracer("service-name")

with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here
    span.set_status(Status(StatusCode.OK))
```

### 3. Environment Variables
```yaml
environment:
  - JAEGER_HOST=jaeger
  - JAEGER_PORT=6831
```

## Monitoring Best Practices

### 1. Key Metrics to Monitor
- **Request Rate**: Number of traces per second
- **Error Rate**: Traces with errors
- **Latency**: P50, P95, P99 percentiles
- **Service Dependencies**: Which services call which

### 2. Alert Conditions
- Latency exceeds threshold (e.g., P95 > 500ms)
- Error rate exceeds threshold (e.g., > 1%)
- Service unavailable (no traces received)

### 3. Performance Optimization
- Use Jaeger to identify slow queries
- Find N+1 query problems
- Optimize service-to-service calls
- Cache frequently accessed data

## Troubleshooting

### No Traces Appearing
1. Check Jaeger is running: `docker ps | grep jaeger`
2. Check service logs for tracing errors
3. Verify environment variables are set
4. Ensure services are rebuilt after adding tracing

### Incomplete Traces
1. Check all services have tracing enabled
2. Verify trace context propagation
3. Check for firewall/network issues
4. Ensure Jaeger agent port (6831) is accessible

### Performance Impact
- Tracing adds ~1-2% overhead
- Use sampling in production (e.g., 1% of requests)
- Configure batch span processor for efficiency

## Production Considerations

### 1. Sampling Strategy
```python
# Configure sampling rate (0.01 = 1% of requests)
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

sampler = TraceIdRatioBased(0.01)
```

### 2. Data Retention
- Configure Jaeger storage backend (Elasticsearch/Cassandra)
- Set retention policies (e.g., 7 days)
- Archive important traces

### 3. Security
- Don't trace sensitive data (passwords, tokens)
- Use TLS for Jaeger collector
- Implement access controls for Jaeger UI

## Next Steps

1. **Enable tracing for all services**: Run the add_tracing.py script
2. **Configure alerting**: Set up alerts based on trace data
3. **Implement custom dashboards**: Use Grafana with Jaeger
4. **Add business metrics**: Track order success rates, etc.

## Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Distributed Tracing Best Practices](https://www.jaegertracing.io/docs/1.21/getting-started/)