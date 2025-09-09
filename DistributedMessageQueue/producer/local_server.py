"""
Local Producer Service for Demo - Updated to connect to localhost broker
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aiohttp
import asyncio
from typing import List, Optional

app = FastAPI(title="Message Queue Producer")

class ProduceMessage(BaseModel):
    topic: str
    key: Optional[str] = None
    value: str

# Configuration - use environment variables or defaults for Docker networking
import os
BROKER_URLS = os.getenv("BROKER_URLS", "http://msgqueue-broker-1:19001,http://msgqueue-broker-2:19001,http://msgqueue-broker-3:19001").split(",")

@app.on_event("startup")
async def startup():
    print("Producer service started on port 19002 - connecting to localhost broker")

@app.post("/produce")
async def produce_message(message: ProduceMessage):
    """Produce a single message to a topic."""
    
    async with aiohttp.ClientSession() as session:
        # Try each broker until one succeeds (failover)
        for broker_url in BROKER_URLS:
            try:
                async with session.post(
                    f"{broker_url}/topics/{message.topic}/messages",
                    json={
                        "topic": message.topic,
                        "key": message.key,
                        "value": message.value
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "status": "success",
                            "broker": broker_url,
                            "topic": message.topic,
                            "partition": result.get("partition"),
                            "offset": result.get("offset"),
                            "message_id": result.get("message_id")
                        }
                    elif response.status == 404:
                        raise HTTPException(status_code=404, detail=f"Topic {message.topic} not found")
            except aiohttp.ClientError:
                continue  # Try next broker
    
    raise HTTPException(status_code=503, detail="All brokers unavailable")

@app.post("/produce/batch")
async def produce_batch(messages: List[ProduceMessage]):
    """Produce multiple messages in batch."""
    results = []
    
    for message in messages:
        try:
            result = await produce_message(message)
            results.append(result)
        except HTTPException as e:
            results.append({
                "status": "error",
                "topic": message.topic,
                "error": e.detail
            })
        await asyncio.sleep(0.01)  # Small delay between messages
    
    return {
        "total_messages": len(messages),
        "successful": len([r for r in results if r.get("status") == "success"]),
        "failed": len([r for r in results if r.get("status") == "error"]),
        "results": results
    }

@app.get("/status")
async def get_status():
    """Get producer status and broker connectivity."""
    broker_status = []
    
    async with aiohttp.ClientSession() as session:
        for broker_url in BROKER_URLS:
            try:
                async with session.get(f"{broker_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        health = await response.json()
                        broker_status.append({
                            "url": broker_url,
                            "status": "healthy",
                            "details": health
                        })
                    else:
                        broker_status.append({
                            "url": broker_url,
                            "status": "unhealthy",
                            "details": {"error": f"HTTP {response.status}"}
                        })
            except:
                broker_status.append({
                    "url": broker_url,
                    "status": "unreachable",
                    "details": {"error": "Connection failed"}
                })
    
    healthy_brokers = len([b for b in broker_status if b["status"] == "healthy"])
    
    return {
        "service": "producer",
        "status": "healthy" if healthy_brokers > 0 else "unhealthy",
        "brokers": broker_status,
        "healthy_brokers": healthy_brokers,
        "total_brokers": len(BROKER_URLS)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "producer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19002)