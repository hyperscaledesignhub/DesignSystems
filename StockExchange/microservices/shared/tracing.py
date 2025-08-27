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
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
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
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
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
        print("📨 HTTPX instrumentation enabled for distributed tracing")
    except ImportError:
        print("⚠️ HTTPX instrumentation not available")
    AsyncPGInstrumentor().instrument()
    RedisInstrumentor().instrument()
    
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

class TracingMiddleware:
    """
    Custom middleware for adding additional tracing context
    """
    def __init__(self, app, service_name: str):
        self.app = app
        self.service_name = service_name
        self.tracer = trace.get_tracer(service_name)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from opentelemetry import propagate
            
            # Extract path and method
            path = scope["path"]
            method = scope["method"]
            
            # Extract headers and convert to dict for context extraction
            headers = dict(scope.get("headers", []))
            # Convert bytes headers to strings for propagation
            string_headers = {
                key.decode() if isinstance(key, bytes) else key: 
                value.decode() if isinstance(value, bytes) else value
                for key, value in headers.items()
            }
            
            # Extract trace context from incoming headers
            context = propagate.extract(string_headers)
            
            # Create span as child of extracted context
            with self.tracer.start_as_current_span(
                f"{method} {path}",
                context=context,
                kind=trace.SpanKind.SERVER,
                attributes={
                    "http.method": method,
                    "http.path": path,
                    "http.scheme": scope["scheme"],
                    "service.name": self.service_name
                }
            ) as span:
                # Add request ID if present
                request_id = headers.get(b"x-request-id", b"").decode() if b"x-request-id" in headers else None
                if request_id:
                    span.set_attribute("http.request_id", request_id)
                
                await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)