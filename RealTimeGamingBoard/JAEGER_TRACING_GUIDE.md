# Jaeger Distributed Tracing Setup Guide

This document provides step-by-step instructions for enabling Jaeger distributed tracing in your microservices architecture.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Docker Compose Configuration](#docker-compose-configuration)
4. [Adding Tracing to a New Service](#adding-tracing-to-a-new-service)
5. [Service Configuration Examples](#service-configuration-examples)
6. [Testing and Verification](#testing-and-verification)
7. [Troubleshooting](#troubleshooting)

## Overview

Our distributed tracing setup uses:
- **Jaeger All-in-One**: For trace collection, storage, and UI
- **OpenTelemetry**: For instrumentation and trace generation
- **Automatic instrumentation**: For FastAPI, HTTPX, Redis, AsyncPG
- **Manual instrumentation**: For custom spans and trace propagation

## Prerequisites

Ensure you have the following running:
- Docker and Docker Compose
- Jaeger service (already configured in docker-compose.yml)
- Network connectivity between services

## Docker Compose Configuration

The Jaeger service is already configured in `docker-compose.yml`:

```yaml
jaeger:
  image: jaegertracing/all-in-one:latest
  container_name: demo-jaeger-1
  ports:
    - "16686:16686"  # Jaeger UI
    - "14268:14268"  # HTTP collector
    - "6831:6831/udp"  # Agent UDP
    - "6832:6832/udp"  # Agent UDP
    - "14250:14250"  # gRPC
  environment:
    - COLLECTOR_OTLP_ENABLED=true
    - LOG_LEVEL=debug
```

**Jaeger UI Access**: http://localhost:16686

## Adding Tracing to a New Service

Follow these steps to add Jaeger tracing to any new Python/FastAPI service:

### Step 1: Add OpenTelemetry Dependencies

Add these dependencies to your service's `requirements.txt`:

```txt
# OpenTelemetry Core
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-exporter-jaeger-thrift==1.21.0

# Auto-Instrumentation Packages
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-requests==0.42b0
opentelemetry-instrumentation-httpx==0.42b0
opentelemetry-instrumentation-redis==0.42b0
opentelemetry-instrumentation-asyncpg==0.42b0

# Required base packages (add if not already present)
requests==2.31.0  # Required for requests instrumentation
```

### Step 2: Create Tracing Configuration File

Create a `tracing.py` file in your service directory:

```python
"""
Distributed tracing configuration using OpenTelemetry and Jaeger
"""
import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

def setup_tracing(service_name: str, jaeger_host: Optional[str] = None) -> trace.Tracer:
    """
    Setup distributed tracing for a microservice
    
    Args:
        service_name: Name of the service for identification in traces
        jaeger_host: Jaeger collector host (defaults to environment variable or localhost)
    
    Returns:
        Configured tracer instance
    """
    # Get Jaeger host from environment or use default
    jaeger_host = jaeger_host or os.getenv("JAEGER_HOST", "jaeger")
    jaeger_collector_port = int(os.getenv("JAEGER_COLLECTOR_PORT", "14268"))
    
    # Create resource with service name
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "demo")
    })
    
    # Configure Jaeger exporter using HTTP collector (more reliable than UDP agent)
    collector_endpoint = f"http://{jaeger_host}:{jaeger_collector_port}/api/traces"
    jaeger_exporter = JaegerExporter(
        collector_endpoint=collector_endpoint
    )
    
    # Create and configure tracer provider
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        jaeger_exporter,
        export_timeout_millis=30000,  # 30 second timeout
        max_export_batch_size=512,
        schedule_delay_millis=5000    # Export every 5 seconds
    )
    provider.add_span_processor(processor)
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Set up context propagation
    set_global_textmap(TraceContextTextMapPropagator())
    
    # Auto-instrument common libraries
    RequestsInstrumentor().instrument()
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
        print(f"📨 HTTPX instrumentation enabled for {service_name}")
    except ImportError:
        print(f"⚠️ HTTPX instrumentation not available for {service_name}")
    
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        print(f"📊 Redis instrumentation enabled for {service_name}")
    except ImportError:
        print(f"⚠️ Redis instrumentation not available for {service_name}")
    except Exception as e:
        print(f"⚠️ Redis instrumentation failed for {service_name}: {e}")
    
    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
        AsyncPGInstrumentor().instrument()
        print(f"🗄️ AsyncPG instrumentation enabled for {service_name}")
    except ImportError:
        print(f"⚠️ AsyncPG instrumentation not available for {service_name}")
    except Exception as e:
        print(f"⚠️ AsyncPG instrumentation failed for {service_name}: {e}")
    
    # Add debug logging
    print(f"🔍 Tracing initialized for service: {service_name}")
    print(f"📡 Sending traces to: {collector_endpoint}")
    
    # Return tracer for manual instrumentation
    return trace.get_tracer(service_name)

def instrument_fastapi(app):
    """
    Instrument a FastAPI application for automatic tracing
    
    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(app)
    return app

def create_span_attributes(**kwargs) -> dict:
    """
    Create standardized span attributes
    
    Args:
        **kwargs: Key-value pairs for span attributes
    
    Returns:
        Dictionary of span attributes
    """
    return {
        f"app.{k}": str(v) for k, v in kwargs.items() if v is not None
    }

def get_trace_headers() -> dict:
    """
    Get headers for trace context propagation
    
    Returns:
        Dictionary of headers with trace context
    """
    from opentelemetry import propagate
    
    headers = {}
    propagate.inject(headers)
    return headers
```

### Step 3: Update Your Service's Main File

Modify your service's `main.py` file:

```python
# Add these imports at the top
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing BEFORE creating FastAPI app
tracer = setup_tracing("your-service-name")

# Create your FastAPI app
app = FastAPI(title="Your Service Name")

# Instrument FastAPI app for tracing
instrument_fastapi(app)

# Rest of your application code...
```

### Step 4: Add Trace Propagation to HTTP Calls

For any HTTP calls to other services, add trace headers:

```python
# Example: Making HTTP calls with trace propagation
async def call_other_service():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://other-service/endpoint",
            json={"data": "value"},
            headers=get_trace_headers()  # This propagates the trace context
        )
        return response.json()
```

### Step 5: Manual Span Creation (Optional)

For custom business logic tracing:

```python
# Example: Creating custom spans
@app.post("/api/v1/process")
async def process_data(data: dict):
    with tracer.start_as_current_span("process_data", attributes=create_span_attributes(
        operation="data_processing",
        data_size=len(data)
    )) as span:
        # Your processing logic here
        result = await process_business_logic(data)
        
        # Add more attributes to the span
        span.set_attribute("app.result_count", len(result))
        
        return result
```

### Step 6: Rebuild and Deploy

```bash
# Rebuild the service
docker-compose build your-service-name

# Start the service
docker-compose up -d your-service-name

# Check logs for tracing initialization
docker logs demo-your-service-name-1 --tail 20
```

## Service Configuration Examples

### Minimal Service Setup

For a basic FastAPI service:

```python
from fastapi import FastAPI
from tracing import setup_tracing, instrument_fastapi

# Initialize tracing
tracer = setup_tracing("minimal-service")

# Create and instrument app
app = FastAPI()
instrument_fastapi(app)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "minimal-service"}
```

### Service with HTTP Client Calls

```python
from fastapi import FastAPI
import httpx
from tracing import setup_tracing, instrument_fastapi, get_trace_headers

tracer = setup_tracing("http-client-service")
app = FastAPI()
instrument_fastapi(app)

@app.post("/api/v1/proxy")
async def proxy_request(data: dict):
    async with httpx.AsyncClient() as client:
        # Trace context automatically propagated
        response = await client.post(
            "http://target-service/endpoint",
            json=data,
            headers=get_trace_headers()
        )
        return response.json()
```

### Service with Database Operations

```python
from fastapi import FastAPI
import asyncpg
from tracing import setup_tracing, instrument_fastapi, create_span_attributes

tracer = setup_tracing("database-service")
app = FastAPI()
instrument_fastapi(app)

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    with tracer.start_as_current_span("get_user", attributes=create_span_attributes(
        user_id=user_id,
        operation="database_read"
    )):
        # Database operations are automatically traced by AsyncPG instrumentation
        conn = await asyncpg.connect("postgresql://...")
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        await conn.close()
        return dict(user) if user else None
```

## Testing and Verification

### Step 1: Check Service Logs

Look for tracing initialization messages:

```bash
docker logs demo-your-service-name-1 | grep -E "(📨|📊|🗄️|🔍|📡)"
```

Expected output:
```
📨 HTTPX instrumentation enabled for your-service-name
📊 Redis instrumentation enabled for your-service-name
🗄️ AsyncPG instrumentation enabled for your-service-name
🔍 Tracing initialized for service: your-service-name
📡 Sending traces to: http://jaeger:14268/api/traces
```

### Step 2: Generate Test Traffic

```bash
# Make some API calls to generate traces
curl -X GET "http://localhost:YOUR_PORT/health"
curl -X POST "http://localhost:YOUR_PORT/api/v1/endpoint" -H "Content-Type: application/json" -d '{"test": "data"}'
```

### Step 3: Verify in Jaeger UI

1. Open Jaeger UI: http://localhost:16686
2. Check if your service appears in the Service dropdown
3. Search for traces from your service
4. Verify trace spans and relationships

### Step 4: Check Service List via API

```bash
# Get list of all traced services
curl -s "http://localhost:16686/api/services" | jq '.data'

# Check trace count for your service
curl -s "http://localhost:16686/api/traces?service=your-service-name&limit=10" | jq '.data | length'
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Service Not Appearing in Jaeger

**Symptoms**: Service doesn't appear in Jaeger UI dropdown

**Solutions**:
- Check tracing initialization logs
- Verify Jaeger collector endpoint is reachable
- Generate traffic to the service (traces are only sent when spans are created)
- Wait 5-10 seconds after making requests (spans are batched)

#### 2. Import Errors

**Symptoms**: `ModuleNotFoundError` for tracing dependencies

**Solutions**:
- Verify all OpenTelemetry packages are in requirements.txt
- Add missing base packages (e.g., `requests` for requests instrumentation)
- Rebuild Docker container after adding dependencies

#### 3. Redis/AsyncPG Instrumentation Failures

**Symptoms**: Warnings about Redis or AsyncPG instrumentation not available

**Solutions**:
- These are non-fatal warnings if your service doesn't use Redis/PostgreSQL
- If you do use these services, ensure the packages are installed:
  - Redis: `redis>=3.0.0`
  - PostgreSQL: `asyncpg>=0.21.0`

#### 4. No Cross-Service Traces

**Symptoms**: Each service shows separate traces instead of connected spans

**Solutions**:
- Ensure `get_trace_headers()` is used in HTTP client calls
- Verify trace context propagation is working
- Check that both services are properly instrumented

#### 5. High Memory Usage

**Symptoms**: Services consuming too much memory

**Solutions**:
- Adjust batch processor settings in `setup_tracing()`:
  ```python
  processor = BatchSpanProcessor(
      jaeger_exporter,
      max_export_batch_size=128,  # Reduce from 512
      schedule_delay_millis=1000  # Reduce from 5000
  )
  ```

### Debug Commands

```bash
# Check if Jaeger is running
docker ps | grep jaeger

# Test Jaeger collector endpoint
curl -f http://localhost:14268/api/traces

# View service tracing logs
docker logs demo-your-service-name-1 2>&1 | grep -i "tracing\|otel\|jaeger"

# Check network connectivity between services
docker exec demo-your-service-name-1 ping jaeger

# Verify service can reach Jaeger collector
docker exec demo-your-service-name-1 curl -f http://jaeger:14268/api/traces
```

## Environment Variables

You can customize tracing behavior using these environment variables:

```yaml
# In docker-compose.yml
environment:
  - JAEGER_HOST=jaeger                    # Jaeger collector host
  - JAEGER_COLLECTOR_PORT=14268           # Jaeger collector port
  - ENVIRONMENT=production                # Deployment environment
  - OTEL_EXPORTER_JAEGER_TIMEOUT=30000   # Export timeout (ms)
```

## Best Practices

1. **Service Naming**: Use consistent, descriptive service names
2. **Span Attributes**: Add meaningful attributes to custom spans
3. **Error Handling**: Don't let tracing errors break your service
4. **Performance**: Use batch processing and reasonable export intervals
5. **Security**: Don't include sensitive data in trace attributes
6. **Monitoring**: Monitor trace export success and failures

## Quick Reference Commands

```bash
# Add tracing to existing service
echo "opentelemetry-api==1.21.0" >> requirements.txt
echo "opentelemetry-sdk==1.21.0" >> requirements.txt
echo "opentelemetry-exporter-jaeger-thrift==1.21.0" >> requirements.txt
echo "opentelemetry-instrumentation-fastapi==0.42b0" >> requirements.txt
echo "opentelemetry-instrumentation-httpx==0.42b0" >> requirements.txt
echo "requests==2.31.0" >> requirements.txt

# Copy tracing configuration
cp existing-service/tracing.py new-service/tracing.py

# Rebuild and start
docker-compose build new-service
docker-compose up -d new-service

# Verify tracing
docker logs demo-new-service-1 | grep "🔍 Tracing initialized"
curl http://localhost:NEW_SERVICE_PORT/health
curl -s "http://localhost:16686/api/services" | jq '.data' | grep new-service
```

---

This guide provides everything needed to add Jaeger distributed tracing to any new service in your microservices architecture. Keep this document updated as your tracing setup evolves.