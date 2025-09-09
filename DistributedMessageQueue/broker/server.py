"""Broker service implementation."""
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import structlog

from ..shared.models import (
    Message, TopicConfig, ProduceRequest, ProduceResponse,
    ConsumeRequest, ConsumeResponse, HealthStatus, ServiceStatus
)
from ..shared.config import Config
from ..shared.utils import generate_broker_id, calculate_partition_for_key
from .storage import WALStorage
from .replication import ReplicationManager

logger = structlog.get_logger()


class BrokerService:
    """Main broker service."""
    
    def __init__(self):
        self.broker_id = generate_broker_id()
        self.storage = WALStorage()
        self.replication_manager = ReplicationManager(
            self.broker_id,
            self.storage,
            Config.get_coordinator_endpoint()
        )
        self.startup_time = datetime.utcnow()
    
    async def startup(self):
        """Service startup."""
        logger.info("Starting broker service", broker_id=self.broker_id)
        await self.replication_manager.start()
    
    async def shutdown(self):
        """Service shutdown."""
        logger.info("Shutting down broker service", broker_id=self.broker_id)
        await self.replication_manager.stop()


# Global service instance
broker_service = BrokerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await broker_service.startup()
    yield
    await broker_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Message Queue Broker Service",
    description="Core message storage and replication service",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/topics", response_model=dict)
async def create_topic(topic_config: TopicConfig):
    """Create a new topic."""
    try:
        success = await broker_service.storage.create_topic(topic_config)
        if not success:
            raise HTTPException(status_code=409, detail="Topic already exists")
        
        logger.info("Topic created", topic=topic_config.name)
        return {"status": "created", "topic": topic_config.name}
    
    except Exception as e:
        logger.error("Failed to create topic", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics", response_model=dict)
async def list_topics():
    """List all topics."""
    try:
        topics = broker_service.storage.get_topics()
        topic_details = []
        
        for topic in topics:
            topic_info = broker_service.storage.get_topic_info(topic)
            if topic_info:
                topic_details.append({
                    "name": topic,
                    "partitions": topic_info.partitions,
                    "replication_factor": topic_info.replication_factor
                })
        
        return {"topics": topic_details}
    
    except Exception as e:
        logger.error("Failed to list topics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/topics/{topic}/messages", response_model=ProduceResponse)
async def produce_message(topic: str, request: ProduceRequest):
    """Produce a message to a topic."""
    try:
        # Validate topic exists
        if topic not in broker_service.storage.get_topics():
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Determine partition
        partition_count = broker_service.storage.get_partition_count(topic)
        if request.partition is not None:
            if request.partition >= partition_count:
                raise HTTPException(status_code=400, detail="Invalid partition")
            partition = request.partition
        else:
            partition = calculate_partition_for_key(request.key, partition_count)
        
        # Check if we're the leader for this partition
        if not broker_service.replication_manager.is_leader(topic, partition):
            # If we're not the leader, we should redirect to the leader
            # For simplicity, we'll reject the request
            raise HTTPException(
                status_code=503, 
                detail="Not the leader for this partition"
            )
        
        # Create message
        message = Message(
            key=request.key,
            value=request.value,
            topic=topic,
            partition=partition,
            timestamp=datetime.utcnow()
        )
        
        # Store message
        offset = await broker_service.storage.append_message(message)
        if offset is None:
            raise HTTPException(status_code=500, detail="Failed to store message")
        
        # Return response
        return ProduceResponse(
            topic=topic,
            partition=partition,
            offset=offset,
            timestamp=message.timestamp
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to produce message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics/{topic}/partitions/{partition}/messages", response_model=ConsumeResponse)
async def consume_messages(
    topic: str,
    partition: int,
    offset: int = 0,
    limit: int = 100
):
    """Consume messages from a topic partition."""
    try:
        # Validate topic and partition
        if topic not in broker_service.storage.get_topics():
            raise HTTPException(status_code=404, detail="Topic not found")
        
        partition_count = broker_service.storage.get_partition_count(topic)
        if partition >= partition_count:
            raise HTTPException(status_code=400, detail="Invalid partition")
        
        # Check if we have this partition (leader or replica)
        if not broker_service.replication_manager.is_replica(topic, partition):
            raise HTTPException(
                status_code=503,
                detail="Partition not available on this broker"
            )
        
        # Read messages
        messages, next_offset = await broker_service.storage.read_messages(
            topic, partition, offset, limit
        )
        
        return ConsumeResponse(
            messages=messages,
            next_offset=next_offset
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to consume messages", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    try:
        # Check storage health
        topics = broker_service.storage.get_topics()
        
        # Check replication health
        cluster_brokers = len(broker_service.replication_manager.cluster_brokers)
        
        details = {
            "broker_id": broker_service.broker_id,
            "topics_count": len(topics),
            "cluster_size": cluster_brokers,
            "uptime_seconds": (datetime.utcnow() - broker_service.startup_time).total_seconds()
        }
        
        return HealthStatus(
            service="broker",
            status=ServiceStatus.HEALTHY,
            details=details
        )
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthStatus(
            service="broker",
            status=ServiceStatus.UNHEALTHY,
            details={"error": str(e)}
        )


# Internal replication endpoints
@app.get("/internal/replica/offset/{topic}/{partition}")
async def get_replica_offset(topic: str, partition: int):
    """Get the current offset for a partition replica."""
    try:
        offset = await broker_service.storage.get_latest_offset(topic, partition)
        return {"offset": offset}
    except Exception as e:
        logger.error("Failed to get replica offset", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/replica/append")
async def append_replica_messages(request: dict):
    """Append messages from leader to follower replica."""
    try:
        topic = request["topic"]
        partition = request["partition"]
        messages_data = request["messages"]
        
        # Only allow if we're a follower for this partition
        if broker_service.replication_manager.is_leader(topic, partition):
            raise HTTPException(status_code=400, detail="Cannot replicate to leader")
        
        # Append messages
        for msg_data in messages_data:
            message = Message(
                key=msg_data.get("key"),
                value=msg_data["value"],
                topic=topic,
                partition=partition,
                offset=msg_data["offset"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"])
            )
            await broker_service.storage.append_message(message)
        
        return {"status": "replicated", "count": len(messages_data)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to append replica messages", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.broker.server:app",
        host="0.0.0.0",
        port=Config.BROKER_PORT,
        log_level=Config.LOG_LEVEL.lower()
    )