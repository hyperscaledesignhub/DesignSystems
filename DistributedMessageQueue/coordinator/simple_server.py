"""
Simple Coordinator Service for Demo
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
import time

app = FastAPI(title="Message Queue Coordinator")

# Global state
brokers = {}  # broker_id -> broker_info
consumer_groups = {}  # group_id -> group_info
topics_metadata = {}  # topic -> metadata

class BrokerInfo(BaseModel):
    broker_id: str
    host: str
    port: int
    status: str = "active"

class ConsumerGroupJoin(BaseModel):
    consumer_id: str
    topics: List[str]

@app.on_event("startup")
async def startup():
    print("Coordinator service started on port 19004")

@app.post("/brokers/register")
async def register_broker(broker: BrokerInfo):
    """Register a broker instance."""
    brokers[broker.broker_id] = {
        "broker_id": broker.broker_id,
        "host": broker.host,
        "port": broker.port,
        "status": "active",
        "last_heartbeat": time.time()
    }
    return {"status": "registered", "broker_id": broker.broker_id}

@app.get("/brokers")
async def list_brokers():
    """List all active brokers."""
    return list(brokers.values())

@app.post("/consumer-groups/{group_id}/join")
async def join_consumer_group(group_id: str, request: ConsumerGroupJoin):
    """Join a consumer group."""
    if group_id not in consumer_groups:
        consumer_groups[group_id] = {
            "group_id": group_id,
            "consumers": {},
            "assignments": {}
        }
    
    consumer_groups[group_id]["consumers"][request.consumer_id] = {
        "consumer_id": request.consumer_id,
        "topics": request.topics,
        "status": "active",
        "joined_at": time.time()
    }
    
    return {
        "group_id": group_id,
        "consumer_id": request.consumer_id,
        "status": "joined"
    }

@app.get("/consumer-groups/{group_id}/assignment")
async def get_partition_assignment(group_id: str):
    """Get partition assignments for a consumer group."""
    if group_id not in consumer_groups:
        return {"assignments": {}}
    
    # Simple round-robin assignment
    assignments = {}
    group = consumer_groups[group_id]
    consumers = list(group["consumers"].keys())
    
    if not consumers:
        return {"assignments": {}}
    
    # Assign partitions (assuming 3 partitions per topic)
    for consumer_id in consumers:
        consumer = group["consumers"][consumer_id]
        assignments[consumer_id] = {
            "consumer_id": consumer_id,
            "partitions": []
        }
        
        for topic in consumer["topics"]:
            # Simple assignment: each consumer gets some partitions
            partition_assignments = [0, 1, 2]  # All partitions for demo
            assignments[consumer_id]["partitions"].extend([
                {"topic": topic, "partition": p} for p in partition_assignments
            ])
    
    return {"assignments": assignments}

@app.post("/leader-election/{topic}/{partition}")
async def trigger_leader_election(topic: str, partition: int):
    """Trigger leader election for a partition."""
    # Simple leader election - first broker wins
    active_brokers = [b for b in brokers.values() if b["status"] == "active"]
    if not active_brokers:
        raise HTTPException(status_code=503, detail="No active brokers")
    
    leader = active_brokers[0]
    followers = active_brokers[1:3]  # Up to 2 followers for 3-way replication
    
    return {
        "topic": topic,
        "partition": partition,
        "leader": leader["broker_id"],
        "followers": [f["broker_id"] for f in followers],
        "replication_factor": len([leader] + followers)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "brokers_count": len(brokers),
        "consumer_groups_count": len(consumer_groups),
        "uptime": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19004)