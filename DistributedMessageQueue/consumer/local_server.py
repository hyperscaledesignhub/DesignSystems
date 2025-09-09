"""
Local Consumer Service for Demo - Updated to connect to localhost broker
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aiohttp
from typing import List, Optional

app = FastAPI(title="Message Queue Consumer")

class SubscribeRequest(BaseModel):
    topics: List[str]
    group: str = "default-group"

# Consumer state
subscriptions = {}  # group -> {topics: [], offsets: {}}
import os
BROKER_URLS = os.getenv("BROKER_URLS", "http://msgqueue-broker-1:19001,http://msgqueue-broker-2:19001,http://msgqueue-broker-3:19001").split(",")
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://msgqueue-coordinator:19004")

@app.on_event("startup")
async def startup():
    print("Consumer service started on port 19003 - connecting to localhost broker")

@app.post("/subscribe")
async def subscribe_to_topics(request: SubscribeRequest):
    """Subscribe to topics."""
    group_id = request.group
    
    if group_id not in subscriptions:
        subscriptions[group_id] = {
            "topics": [],
            "offsets": {}  # topic -> partition -> offset
        }
    
    # Add topics to subscription
    for topic in request.topics:
        if topic not in subscriptions[group_id]["topics"]:
            subscriptions[group_id]["topics"].append(topic)
            subscriptions[group_id]["offsets"][topic] = {0: 0, 1: 0, 2: 0}  # 3 partitions
    
    # Register with coordinator
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{COORDINATOR_URL}/consumer-groups/{group_id}/join",
                json={
                    "consumer_id": f"consumer-{group_id}",
                    "topics": request.topics
                }
            ) as response:
                coordinator_result = await response.json() if response.status == 200 else {}
        except:
            coordinator_result = {"error": "coordinator unavailable"}
    
    return {
        "group": group_id,
        "topics": subscriptions[group_id]["topics"],
        "coordinator_status": coordinator_result
    }

@app.get("/consume")
async def consume_messages(group: str = "default-group", timeout: int = 5, limit: int = 10):
    """Consume messages from subscribed topics."""
    if group not in subscriptions:
        raise HTTPException(status_code=404, detail=f"Group {group} not subscribed to any topics")
    
    all_messages = []
    group_data = subscriptions[group]
    
    async with aiohttp.ClientSession() as session:
        for topic in group_data["topics"]:
            for partition in range(3):  # 3 partitions per topic
                current_offset = group_data["offsets"][topic][partition]
                
                # Try to fetch from any available broker
                for broker_url in BROKER_URLS:
                    try:
                        async with session.get(
                            f"{broker_url}/topics/{topic}/partitions/{partition}/messages",
                            params={
                                "offset": current_offset,
                                "limit": limit // 3  # Distribute limit across partitions
                            }
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                messages = result.get("messages", [])
                                
                                if messages:
                                    all_messages.extend(messages)
                                    # Update offset to next message
                                    last_offset = max(msg["offset"] for msg in messages)
                                    group_data["offsets"][topic][partition] = last_offset + 1
                                break  # Successfully got messages from this broker
                    except:
                        continue  # Try next broker
    
    return {
        "group": group,
        "messages": all_messages,
        "message_count": len(all_messages),
        "offsets": group_data["offsets"]
    }

@app.post("/commit")
async def commit_offsets(group: str = "default-group"):
    """Commit current offsets."""
    if group not in subscriptions:
        raise HTTPException(status_code=404, detail=f"Group {group} not found")
    
    # In a real system, this would persist offsets to storage
    return {
        "group": group,
        "committed_offsets": subscriptions[group]["offsets"],
        "status": "committed"
    }

@app.get("/status")
async def get_status():
    """Get consumer status."""
    return {
        "service": "consumer",
        "subscriptions": len(subscriptions),
        "groups": list(subscriptions.keys())
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "consumer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19003)