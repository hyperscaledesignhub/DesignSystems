"""
Simple Broker Service for Demo
Implements basic broker functionality for testing
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import os
import time
from datetime import datetime
import uuid

app = FastAPI(title="Message Queue Broker")

# Global state
topics = {}  # topic_name -> {partitions: [], config: {}}
messages_store = {}  # topic -> partition -> [messages]
offsets = {}  # topic -> partition -> current_offset

class TopicConfig(BaseModel):
    name: str
    partitions: int = 3
    replication_factor: int = 3
    retention_ms: int = 604800000  # 7 days

class Message(BaseModel):
    key: Optional[str] = None
    value: str
    topic: str
    partition: int = 0
    offset: int = 0
    timestamp: str = None

class ProduceRequest(BaseModel):
    topic: str
    key: Optional[str] = None
    value: str

def hash_key(key: str, num_partitions: int) -> int:
    """Hash function for partition assignment."""
    if not key:
        return int(time.time()) % num_partitions
    return hash(key) % num_partitions

def ensure_topic_storage(topic: str):
    """Ensure topic storage directories exist."""
    if topic not in messages_store:
        messages_store[topic] = {}
        offsets[topic] = {}
        
        partitions = topics[topic]["config"]["partitions"]
        for i in range(partitions):
            messages_store[topic][i] = []
            offsets[topic][i] = 0

@app.on_event("startup")
async def startup():
    """Initialize broker on startup."""
    # Create data directory
    os.makedirs("./data/broker", exist_ok=True)
    print(f"Broker service started on port 19001")

@app.post("/topics")
async def create_topic(topic_config: TopicConfig):
    """Create a new topic."""
    if topic_config.name in topics:
        raise HTTPException(status_code=400, detail=f"Topic {topic_config.name} already exists")
    
    # Create topic configuration
    topics[topic_config.name] = {
        "config": {
            "partitions": topic_config.partitions,
            "replication_factor": topic_config.replication_factor,
            "retention_ms": topic_config.retention_ms
        },
        "partitions": list(range(topic_config.partitions)),
        "created_at": datetime.now().isoformat()
    }
    
    # Initialize storage
    ensure_topic_storage(topic_config.name)
    
    # Write to WAL (Write-Ahead Log) - simulate file-based storage
    wal_path = f"./data/broker/topic-{topic_config.name}.wal"
    with open(wal_path, "a") as f:
        wal_entry = {
            "action": "create_topic",
            "topic": topic_config.name,
            "config": topics[topic_config.name]["config"],
            "timestamp": datetime.now().isoformat()
        }
        f.write(json.dumps(wal_entry) + "\n")
    
    return {
        "topic": topic_config.name,
        "partitions": topic_config.partitions,
        "replication_factor": topic_config.replication_factor,
        "status": "created"
    }

@app.get("/topics")
async def list_topics():
    """List all topics."""
    return [
        {
            "name": name,
            "partitions": config["config"]["partitions"],
            "replication_factor": config["config"]["replication_factor"],
            "created_at": config["created_at"]
        }
        for name, config in topics.items()
    ]

@app.post("/topics/{topic}/messages")
async def produce_message(topic: str, request: ProduceRequest):
    """Produce a message to a topic."""
    if topic not in topics:
        raise HTTPException(status_code=404, detail=f"Topic {topic} not found")
    
    ensure_topic_storage(topic)
    
    # Calculate partition
    num_partitions = topics[topic]["config"]["partitions"]
    partition = hash_key(request.key, num_partitions)
    
    # Create message
    message = {
        "key": request.key,
        "value": request.value,
        "topic": topic,
        "partition": partition,
        "offset": offsets[topic][partition],
        "timestamp": datetime.now().isoformat(),
        "message_id": str(uuid.uuid4())
    }
    
    # Store message
    messages_store[topic][partition].append(message)
    offsets[topic][partition] += 1
    
    # Write to WAL (partition-specific)
    wal_path = f"./data/broker/{topic}-partition-{partition}.wal"
    os.makedirs(os.path.dirname(wal_path), exist_ok=True)
    with open(wal_path, "a") as f:
        f.write(json.dumps(message) + "\n")
    
    # Simulate replication to 2 other brokers (3 total replicas)
    replicas = ["broker-1", "broker-2", "broker-3"]
    replication_log = {
        "message_id": message["message_id"],
        "replicas": replicas,
        "leader": "broker-1",  # This broker is leader
        "timestamp": datetime.now().isoformat()
    }
    
    repl_path = f"./data/broker/replication.log"
    with open(repl_path, "a") as f:
        f.write(json.dumps(replication_log) + "\n")
    
    return {
        "topic": topic,
        "partition": partition,
        "offset": message["offset"],
        "message_id": message["message_id"],
        "replicated_to": replicas
    }

@app.get("/topics/{topic}/partitions/{partition}/messages")
async def consume_messages(
    topic: str, 
    partition: int,
    offset: int = 0,
    limit: int = 10
):
    """Consume messages from a specific partition."""
    if topic not in topics:
        raise HTTPException(status_code=404, detail=f"Topic {topic} not found")
    
    ensure_topic_storage(topic)
    
    if partition >= topics[topic]["config"]["partitions"]:
        raise HTTPException(status_code=400, detail=f"Partition {partition} does not exist")
    
    # Get messages from the specified offset
    partition_messages = messages_store[topic][partition]
    
    # Filter messages from offset
    filtered_messages = [
        msg for msg in partition_messages 
        if msg["offset"] >= offset
    ][:limit]
    
    return {
        "topic": topic,
        "partition": partition,
        "messages": filtered_messages,
        "next_offset": offset + len(filtered_messages) if filtered_messages else offset,
        "total_messages": len(partition_messages),
        "current_offset": offsets[topic][partition]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check storage availability
    storage_healthy = os.path.exists("./data/broker")
    
    # Check topic status
    topics_count = len(topics)
    total_messages = sum(
        sum(len(partition_msgs) for partition_msgs in topic_data.values())
        for topic_data in messages_store.values()
    )
    
    return {
        "status": "healthy" if storage_healthy else "unhealthy",
        "broker_id": "broker-1",
        "topics_count": topics_count,
        "total_messages": total_messages,
        "storage_healthy": storage_healthy,
        "uptime": time.time(),
        "replication_status": {
            "role": "leader",
            "replicas": ["broker-2", "broker-3"],
            "in_sync": True
        }
    }

@app.get("/replica/{topic}/{partition}/offset")
async def get_replica_offset(topic: str, partition: int):
    """Get current offset for replication."""
    if topic not in topics:
        raise HTTPException(status_code=404, detail=f"Topic {topic} not found")
    
    ensure_topic_storage(topic)
    
    return {
        "topic": topic,
        "partition": partition,
        "offset": offsets[topic][partition],
        "message_count": len(messages_store[topic][partition])
    }

@app.post("/replica/messages")
async def append_replica_messages(request: Dict[str, Any]):
    """Append messages from leader (replication)."""
    # Simulate follower receiving messages from leader
    return {"status": "replicated", "count": len(request.get("messages", []))}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19001)