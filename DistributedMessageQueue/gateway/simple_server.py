"""
Simple API Gateway for Demo
"""

from fastapi import FastAPI, HTTPException
import aiohttp
from typing import Any, Dict

app = FastAPI(title="Message Queue API Gateway")

# Service URLs
PRODUCER_URL = "http://msgqueue-producer:19002"
CONSUMER_URL = "http://msgqueue-consumer-1:19003"
BROKER_URL = "http://msgqueue-broker-1:19001"
COORDINATOR_URL = "http://msgqueue-coordinator:19004"

@app.on_event("startup")
async def startup():
    print("API Gateway started on port 19005")

@app.post("/api/v1/produce")
async def produce_message(request: Dict[str, Any]):
    """Proxy produce request to producer service."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PRODUCER_URL}/produce", json=request) as response:
            return await response.json()

@app.get("/api/v1/consume")
async def consume_messages(group: str = "demo-group", timeout: int = 5, limit: int = 10):
    """Proxy consume request to consumer service."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CONSUMER_URL}/consume",
            params={"group": group, "timeout": timeout, "limit": limit}
        ) as response:
            return await response.json()

@app.post("/api/v1/topics")
async def create_topic(request: Dict[str, Any]):
    """Proxy topic creation to broker."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BROKER_URL}/topics", json=request) as response:
            return await response.json()

@app.get("/api/v1/topics")
async def list_topics():
    """Proxy topic listing to broker."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BROKER_URL}/topics") as response:
            return await response.json()

@app.post("/api/v1/subscribe")
async def subscribe_to_topics(request: Dict[str, Any]):
    """Proxy subscription to consumer service."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{CONSUMER_URL}/subscribe", json=request) as response:
            return await response.json()

@app.get("/api/v1/status")
async def get_system_status():
    """Get aggregated system status."""
    services = {
        "producer": PRODUCER_URL,
        "consumer": CONSUMER_URL,
        "broker": BROKER_URL,
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
    
    return {"services": status}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19005)