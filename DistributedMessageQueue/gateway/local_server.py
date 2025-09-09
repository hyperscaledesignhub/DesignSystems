"""
Simple API Gateway for Demo with Local Service URLs
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
import aiohttp
from typing import Any, Dict, List
import time
import asyncio

app = FastAPI(title="Message Queue API Gateway")

# Service URLs - use environment variables or defaults for Docker networking
import os
PRODUCER_URL = os.getenv("PRODUCER_URL", "http://msgqueue-producer:19002")
CONSUMER_URL = os.getenv("CONSUMER_URL", "http://msgqueue-consumer-1:19003")
BROKER_URL = os.getenv("BROKER_URL", "http://msgqueue-broker-1:19001")
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://msgqueue-coordinator:19004")

# Simple API key store and request tracking
api_keys = {"admin-key", "user-key", "test-key"}
request_counts = {}  # client_ip -> {count, last_reset}
RATE_LIMIT = 100  # requests per minute

@app.on_event("startup")
async def startup():
    print("API Gateway started on port 19005")

# Authentication dependency
async def validate_api_key(request: Request):
    """Validate API key from header."""
    api_key = request.headers.get("X-API-Key")
    
    if not api_key or api_key not in api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key

# Rate limiting dependency
async def check_rate_limit(request: Request):
    """Simple rate limiting per IP."""
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip not in request_counts:
        request_counts[client_ip] = {"count": 1, "last_reset": current_time}
        return
    
    client_data = request_counts[client_ip]
    
    # Reset if more than a minute has passed
    if current_time - client_data["last_reset"] > 60:
        client_data["count"] = 1
        client_data["last_reset"] = current_time
        return
    
    # Check if rate limit exceeded
    if client_data["count"] >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    client_data["count"] += 1

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.url.path} - Client: {request.client.host}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Response: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

@app.post("/api/v1/produce")
async def produce_message(
    request: Request, 
    message_data: Dict[str, Any],
    api_key: str = Depends(validate_api_key),
    _rate_limit: None = Depends(check_rate_limit)
):
    """Proxy produce request to producer service with auth and rate limiting."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{PRODUCER_URL}/produce", json=message_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=error_text)
        except aiohttp.ClientError:
            raise HTTPException(status_code=503, detail="Producer service unavailable")

@app.get("/api/v1/consume")
async def consume_messages(
    request: Request,
    group: str = "demo-group", 
    timeout: int = 5, 
    limit: int = 10,
    api_key: str = Depends(validate_api_key),
    _rate_limit: None = Depends(check_rate_limit)
):
    """Proxy consume request to consumer service with auth and rate limiting."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{CONSUMER_URL}/consume",
                params={"group": group, "timeout": timeout, "limit": limit}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=error_text)
        except aiohttp.ClientError:
            raise HTTPException(status_code=503, detail="Consumer service unavailable")

@app.post("/api/v1/subscribe")
async def subscribe_to_topics(
    request: Request,
    subscription_data: Dict[str, Any],
    api_key: str = Depends(validate_api_key),
    _rate_limit: None = Depends(check_rate_limit)
):
    """Proxy subscription to consumer service with auth and rate limiting."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{CONSUMER_URL}/subscribe", json=subscription_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=error_text)
        except aiohttp.ClientError:
            raise HTTPException(status_code=503, detail="Consumer service unavailable")

# Load balancing test - multiple producer instances (simulated)
PRODUCER_INSTANCES = [
    "http://localhost:19002",  # Our actual producer
    "http://localhost:19102",  # Simulated second instance (will fail)
    "http://localhost:19202",  # Simulated third instance (will fail)
]
current_producer_index = 0

@app.post("/api/v1/produce-lb")
async def produce_with_load_balancing(
    request: Request,
    message_data: Dict[str, Any],
    api_key: str = Depends(validate_api_key),
    _rate_limit: None = Depends(check_rate_limit)
):
    """Demonstrate load balancing across producer instances."""
    global current_producer_index
    
    # Try each producer instance in round-robin fashion
    for i in range(len(PRODUCER_INSTANCES)):
        producer_url = PRODUCER_INSTANCES[current_producer_index]
        current_producer_index = (current_producer_index + 1) % len(PRODUCER_INSTANCES)
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{producer_url}/produce", json=message_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        result["used_instance"] = producer_url
                        return result
            except aiohttp.ClientError:
                continue  # Try next instance
    
    raise HTTPException(status_code=503, detail="All producer instances unavailable")

@app.get("/api/v1/status")
async def get_system_status(api_key: str = Depends(validate_api_key)):
    """Get aggregated system status with authentication."""
    services = {
        "producer": PRODUCER_URL,
        "consumer": CONSUMER_URL,
        "coordinator": COORDINATOR_URL
    }
    
    status = {}
    async with aiohttp.ClientSession() as session:
        for service, url in services.items():
            try:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        health = await response.json()
                        status[service] = {"status": "healthy", "details": health}
                    else:
                        status[service] = {"status": "unhealthy", "details": f"HTTP {response.status}"}
            except:
                status[service] = {"status": "unreachable", "details": "Connection failed"}
    
    return {
        "services": status,
        "gateway_stats": {
            "rate_limit_info": len(request_counts),
            "clients_tracked": list(request_counts.keys())
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "gateway"}

# Test endpoint to trigger rate limiting
@app.get("/api/v1/test-rate-limit")
async def test_rate_limit(request: Request, _rate_limit: None = Depends(check_rate_limit)):
    """Test endpoint to demonstrate rate limiting."""
    return {"message": "Rate limit test successful", "timestamp": time.time()}

# Topic management endpoints
@app.post("/api/v1/topics")
async def create_topic(
    request: Request,
    topic_data: Dict[str, Any],
    api_key: str = Depends(validate_api_key),
    _rate_limit: None = Depends(check_rate_limit)
):
    """Proxy topic creation to broker service."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{BROKER_URL}/topics", json=topic_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=error_text)
        except aiohttp.ClientError:
            raise HTTPException(status_code=503, detail="Broker service unavailable")

@app.get("/api/v1/topics")
async def list_topics(
    request: Request,
    api_key: str = Depends(validate_api_key),
    _rate_limit: None = Depends(check_rate_limit)
):
    """Proxy topic listing to broker service."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BROKER_URL}/topics") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=error_text)
        except aiohttp.ClientError:
            raise HTTPException(status_code=503, detail="Broker service unavailable")

# Partition-specific message retrieval
@app.get("/api/v1/topics/{topic}/partitions/{partition}/messages")
async def get_partition_messages(
    topic: str,
    partition: int,
    request: Request,
    offset: int = 0,
    limit: int = 10,
    api_key: str = Depends(validate_api_key),
    _rate_limit: None = Depends(check_rate_limit)
):
    """Proxy partition-specific message retrieval to broker service."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{BROKER_URL}/topics/{topic}/partitions/{partition}/messages",
                params={"offset": offset, "limit": limit}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=error_text)
        except aiohttp.ClientError:
            raise HTTPException(status_code=503, detail="Broker service unavailable")

# Test endpoint without authentication
@app.get("/api/v1/public")
async def public_endpoint():
    """Public endpoint without authentication."""
    return {"message": "This is a public endpoint", "timestamp": time.time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19005)