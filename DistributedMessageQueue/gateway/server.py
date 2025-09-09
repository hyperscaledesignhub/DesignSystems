"""API Gateway service implementation."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..shared.models import (
    ProduceRequest, TopicConfig, HealthStatus, ServiceStatus
)
from ..shared.config import Config
from ..shared.utils import make_http_request, CircuitBreaker

logger = structlog.get_logger()


class ServiceRegistry:
    """Service discovery and load balancing."""
    
    def __init__(self):
        self.services: Dict[str, List[str]] = {
            "producer": [f"http://localhost:{Config.PRODUCER_PORT}"],
            "consumer": [f"http://localhost:{Config.CONSUMER_PORT}"],
            "broker": Config.get_broker_endpoints(),
            "coordinator": [Config.get_coordinator_endpoint()],
            "monitoring": [f"http://localhost:{Config.MONITORING_PORT}"]
        }
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.request_counts: Dict[str, int] = {}
        self.current_index: Dict[str, int] = {}
    
    def get_service_endpoint(self, service_name: str) -> Optional[str]:
        """Get next available endpoint for a service (round-robin)."""
        if service_name not in self.services:
            return None
        
        endpoints = self.services[service_name]
        if not endpoints:
            return None
        
        # Round-robin selection
        if service_name not in self.current_index:
            self.current_index[service_name] = 0
        
        index = self.current_index[service_name] % len(endpoints)
        self.current_index[service_name] = index + 1
        
        endpoint = endpoints[index]
        
        # Check circuit breaker
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker()
        
        circuit_breaker = self.circuit_breakers[endpoint]
        
        if circuit_breaker.can_execute():
            return endpoint
        else:
            # Try next endpoint
            if len(endpoints) > 1:
                self.current_index[service_name] += 1
                return self.get_service_endpoint(service_name)
            return None
    
    def record_success(self, endpoint: str):
        """Record successful request."""
        if endpoint in self.circuit_breakers:
            self.circuit_breakers[endpoint].record_success()
    
    def record_failure(self, endpoint: str):
        """Record failed request."""
        if endpoint in self.circuit_breakers:
            self.circuit_breakers[endpoint].record_failure()


class APIGatewayService:
    """Main API Gateway service."""
    
    def __init__(self):
        self.service_registry = ServiceRegistry()
        self.startup_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0
        self.api_keys = {"admin": "admin-key", "user": "user-key"}  # Simple API key store
    
    async def startup(self):
        """Service startup."""
        logger.info("Starting API Gateway service")
    
    async def shutdown(self):
        """Service shutdown."""
        logger.info("Shutting down API Gateway service")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        return api_key in self.api_keys.values()
    
    async def proxy_request(
        self, 
        service_name: str, 
        path: str, 
        method: str = "GET", 
        data: dict = None
    ) -> dict:
        """Proxy request to a backend service."""
        endpoint = self.service_registry.get_service_endpoint(service_name)
        
        if not endpoint:
            raise HTTPException(
                status_code=503, 
                detail=f"Service {service_name} not available"
            )
        
        url = f"{endpoint.rstrip('/')}/{path.lstrip('/')}"
        
        try:
            response = await make_http_request(
                method, 
                url, 
                data, 
                timeout=Config.REQUEST_TIMEOUT_MS / 1000
            )
            
            if response:
                self.service_registry.record_success(endpoint)
                return response
            else:
                self.service_registry.record_failure(endpoint)
                raise HTTPException(status_code=502, detail="Bad Gateway")
                
        except Exception as e:
            self.service_registry.record_failure(endpoint)
            logger.error("Proxy request failed", service=service_name, url=url, error=str(e))
            raise HTTPException(status_code=502, detail=f"Service error: {str(e)}")


# Global service instance
gateway_service = APIGatewayService()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await gateway_service.startup()
    yield
    await gateway_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Message Queue API Gateway",
    description="Unified API gateway for the distributed message queue system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Authentication dependency
async def validate_api_key(request: Request):
    """Validate API key from header."""
    api_key = request.headers.get("X-API-Key")
    
    if not api_key or not gateway_service.validate_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key


# Producer endpoints
@app.post("/api/v1/produce")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def produce_message(
    request: Request,
    produce_request: ProduceRequest,
    api_key: str = Depends(validate_api_key)
):
    """Produce a message (proxy to producer service)."""
    try:
        gateway_service.request_count += 1
        
        response = await gateway_service.proxy_request(
            "producer",
            "produce",
            "POST",
            produce_request.dict()
        )
        
        logger.info("Message produced via gateway", topic=produce_request.topic)
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("Produce request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/produce/batch")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def produce_batch(
    request: Request,
    produce_requests: List[ProduceRequest],
    api_key: str = Depends(validate_api_key)
):
    """Produce multiple messages (proxy to producer service)."""
    try:
        gateway_service.request_count += 1
        
        batch_data = [req.dict() for req in produce_requests]
        
        response = await gateway_service.proxy_request(
            "producer",
            "produce/batch",
            "POST",
            batch_data
        )
        
        logger.info("Batch produced via gateway", count=len(produce_requests))
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("Batch produce request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Consumer endpoints
@app.post("/api/v1/consumer/init")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def init_consumer(
    request: Request,
    config: dict,
    api_key: str = Depends(validate_api_key)
):
    """Initialize consumer (proxy to consumer service)."""
    try:
        gateway_service.request_count += 1
        
        response = await gateway_service.proxy_request(
            "consumer",
            "consumer/init",
            "POST",
            config
        )
        
        logger.info("Consumer initialized via gateway", group_id=config.get("group_id"))
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("Consumer init request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/subscribe")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def subscribe_to_topics(
    request: Request,
    subscription: dict,
    api_key: str = Depends(validate_api_key)
):
    """Subscribe to topics (proxy to consumer service)."""
    try:
        gateway_service.request_count += 1
        
        response = await gateway_service.proxy_request(
            "consumer",
            "subscribe",
            "POST",
            subscription
        )
        
        logger.info("Subscribed via gateway", topics=subscription.get("topics"))
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("Subscribe request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/consume")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def consume_messages(
    request: Request,
    timeout: int = 5000,
    api_key: str = Depends(validate_api_key)
):
    """Consume messages (proxy to consumer service)."""
    try:
        gateway_service.request_count += 1
        
        response = await gateway_service.proxy_request(
            "consumer",
            f"consume?timeout={timeout}",
            "GET"
        )
        
        logger.info("Messages consumed via gateway", count=response.get("message_count", 0))
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("Consume request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/commit")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def commit_offsets(
    request: Request,
    commit_data: dict = None,
    api_key: str = Depends(validate_api_key)
):
    """Commit offsets (proxy to consumer service)."""
    try:
        gateway_service.request_count += 1
        
        response = await gateway_service.proxy_request(
            "consumer",
            "commit",
            "POST",
            commit_data
        )
        
        logger.info("Offsets committed via gateway")
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("Commit request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Topic management endpoints
@app.post("/api/v1/topics")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def create_topic(
    request: Request,
    topic_config: TopicConfig,
    api_key: str = Depends(validate_api_key)
):
    """Create topic (proxy to producer service)."""
    try:
        gateway_service.request_count += 1
        
        response = await gateway_service.proxy_request(
            "producer",
            "topics",
            "POST",
            topic_config.dict()
        )
        
        logger.info("Topic created via gateway", topic=topic_config.name)
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("Create topic request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/topics")
@limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE}/minute")
async def list_topics(
    request: Request,
    api_key: str = Depends(validate_api_key)
):
    """List topics (proxy to producer service)."""
    try:
        gateway_service.request_count += 1
        
        response = await gateway_service.proxy_request(
            "producer",
            "topics",
            "GET"
        )
        
        logger.info("Topics listed via gateway")
        return response
        
    except HTTPException:
        gateway_service.error_count += 1
        raise
    except Exception as e:
        gateway_service.error_count += 1
        logger.error("List topics request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# System status endpoints
@app.get("/api/v1/status")
async def get_system_status(api_key: str = Depends(validate_api_key)):
    """Get aggregated system status."""
    try:
        status_data = {
            "gateway": {
                "uptime_seconds": (datetime.utcnow() - gateway_service.startup_time).total_seconds(),
                "request_count": gateway_service.request_count,
                "error_count": gateway_service.error_count,
                "error_rate": gateway_service.error_count / max(gateway_service.request_count, 1)
            }
        }
        
        # Get status from all services
        services = ["producer", "consumer", "coordinator", "monitoring"]
        
        for service in services:
            try:
                response = await gateway_service.proxy_request(service, "status", "GET")
                status_data[service] = response
            except:
                status_data[service] = {"status": "unavailable"}
        
        # Get broker status
        try:
            broker_response = await gateway_service.proxy_request("broker", "health", "GET")
            status_data["broker"] = broker_response
        except:
            status_data["broker"] = {"status": "unavailable"}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": status_data
        }
        
    except Exception as e:
        logger.error("Failed to get system status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metrics")
async def get_system_metrics(api_key: str = Depends(validate_api_key)):
    """Get system metrics (proxy to monitoring service)."""
    try:
        response = await gateway_service.proxy_request("monitoring", "metrics", "GET")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get metrics request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check connectivity to key services
        service_health = {}
        critical_services = ["producer", "consumer", "coordinator"]
        
        healthy_services = 0
        for service in critical_services:
            try:
                response = await gateway_service.proxy_request(service, "health", "GET")
                if response and response.get("status") == "healthy":
                    service_health[service] = "healthy"
                    healthy_services += 1
                else:
                    service_health[service] = "unhealthy"
            except:
                service_health[service] = "unavailable"
        
        # Overall health
        if healthy_services == len(critical_services):
            overall_status = ServiceStatus.HEALTHY
        elif healthy_services > 0:
            overall_status = ServiceStatus.UNHEALTHY  # Could be "degraded" in more sophisticated system
        else:
            overall_status = ServiceStatus.UNHEALTHY
        
        details = {
            "request_count": gateway_service.request_count,
            "error_count": gateway_service.error_count,
            "service_health": service_health,
            "healthy_services": healthy_services,
            "total_services": len(critical_services),
            "uptime_seconds": (datetime.utcnow() - gateway_service.startup_time).total_seconds()
        }
        
        return HealthStatus(
            service="gateway",
            status=overall_status,
            details=details
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthStatus(
            service="gateway",
            status=ServiceStatus.UNHEALTHY,
            details={"error": str(e)}
        )


# Admin endpoints
@app.post("/admin/flush")
async def flush_producer_batches(api_key: str = Depends(validate_api_key)):
    """Force flush producer batches."""
    try:
        response = await gateway_service.proxy_request("producer", "flush", "POST")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Flush request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/circuit-breakers")
async def get_circuit_breaker_status(api_key: str = Depends(validate_api_key)):
    """Get circuit breaker status for all services."""
    try:
        circuit_breaker_status = {}
        
        for endpoint, cb in gateway_service.service_registry.circuit_breakers.items():
            circuit_breaker_status[endpoint] = {
                "state": cb.state,
                "failure_count": cb.failure_count,
                "last_failure_time": cb.last_failure_time.isoformat() if cb.last_failure_time else None
            }
        
        return {
            "circuit_breakers": circuit_breaker_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get circuit breaker status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.gateway.server:app",
        host="0.0.0.0",
        port=Config.GATEWAY_PORT,
        log_level=Config.LOG_LEVEL.lower()
    )