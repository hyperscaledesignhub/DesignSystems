"""Consumer service implementation."""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import structlog

from ..shared.models import (
    Message, ConsumeRequest, ConsumeResponse, HealthStatus, ServiceStatus
)
from ..shared.config import Config
from ..shared.utils import make_http_request, generate_consumer_id
from .group_coordinator import ConsumerGroupCoordinator, OffsetManager, MessageProcessor

logger = structlog.get_logger()


class ConsumerService:
    """Main consumer service."""
    
    def __init__(self, group_id: str = None, consumer_id: str = None):
        self.group_id = group_id or "default-group"
        self.consumer_id = consumer_id or generate_consumer_id()
        
        self.group_coordinator = ConsumerGroupCoordinator(self.group_id, self.consumer_id)
        self.offset_manager = OffsetManager(self.group_id, self.consumer_id)
        self.message_processor = MessageProcessor(self.group_id, self.consumer_id)
        
        self.startup_time = datetime.utcnow()
        self.is_consuming = False
        self._consume_task: Optional[asyncio.Task] = None
        self.consumed_message_count = 0
        self.last_poll_time: Optional[datetime] = None
    
    async def startup(self):
        """Service startup."""
        logger.info("Starting consumer service", group_id=self.group_id, consumer_id=self.consumer_id)
        
        await self.group_coordinator.start()
        await self.offset_manager.start()
        
        # Join consumer group
        success = await self.group_coordinator.join_group()
        if not success:
            logger.error("Failed to join consumer group")
    
    async def shutdown(self):
        """Service shutdown."""
        logger.info("Shutting down consumer service")
        
        # Stop consuming
        await self.stop_consuming()
        
        # Shutdown components
        await self.offset_manager.stop()
        await self.group_coordinator.stop()
    
    async def start_consuming(self):
        """Start consuming messages."""
        if self.is_consuming:
            return
        
        self.is_consuming = True
        self._consume_task = asyncio.create_task(self._consume_loop())
        logger.info("Started consuming messages")
    
    async def stop_consuming(self):
        """Stop consuming messages."""
        self.is_consuming = False
        
        if self._consume_task:
            self._consume_task.cancel()
            self._consume_task = None
        
        logger.info("Stopped consuming messages")
    
    async def _consume_loop(self):
        """Main consumption loop."""
        while self.is_consuming:
            try:
                # Check if we have partition assignments
                if not self.group_coordinator.has_assignments():
                    await asyncio.sleep(1)
                    continue
                
                # Consume from all assigned partitions
                consumed_any = False
                
                for topic in self.group_coordinator.subscribed_topics:
                    partitions = self.group_coordinator.get_assigned_partitions(topic)
                    
                    for partition in partitions:
                        messages = await self._fetch_messages(topic, partition)
                        
                        if messages:
                            # Process messages
                            successful = await self.message_processor.process_batch(messages)
                            
                            if successful > 0:
                                # Update offset for last successful message
                                last_message = messages[successful - 1]
                                self.offset_manager.update_offset(
                                    topic, partition, last_message.offset + 1
                                )
                                
                                self.consumed_message_count += successful
                                consumed_any = True
                
                self.last_poll_time = datetime.utcnow()
                
                # If no messages consumed, wait a bit
                if not consumed_any:
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in consume loop", error=str(e))
                await asyncio.sleep(1)
    
    async def _fetch_messages(self, topic: str, partition: int, limit: int = 100) -> List[Message]:
        """Fetch messages from a broker for a topic-partition."""
        try:
            # Get current offset
            offset = self.offset_manager.get_local_offset(topic, partition)
            
            # Find broker for this partition
            broker_endpoint = await self._find_broker_for_partition(topic, partition)
            if not broker_endpoint:
                return []
            
            # Fetch messages
            url = f"{broker_endpoint}/topics/{topic}/partitions/{partition}/messages"
            params = f"?offset={offset}&limit={limit}"
            
            response = await make_http_request("GET", url + params)
            
            if response and "messages" in response:
                messages = []
                for msg_data in response["messages"]:
                    message = Message(
                        key=msg_data.get("key"),
                        value=msg_data["value"],
                        topic=msg_data["topic"],
                        partition=msg_data["partition"],
                        offset=msg_data["offset"],
                        timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                        size=msg_data["size"]
                    )
                    messages.append(message)
                
                if messages:
                    logger.debug(
                        "Fetched messages",
                        topic=topic,
                        partition=partition,
                        count=len(messages),
                        offset_range=f"{messages[0].offset}-{messages[-1].offset}"
                    )
                
                return messages
            
            return []
            
        except Exception as e:
            logger.error("Failed to fetch messages", topic=topic, partition=partition, error=str(e))
            return []
    
    async def _find_broker_for_partition(self, topic: str, partition: int) -> Optional[str]:
        """Find the broker endpoint for a topic-partition."""
        try:
            # Query coordinator for partition info
            coordinator_endpoint = Config.get_coordinator_endpoint()
            url = f"{coordinator_endpoint}/topics/{topic}/partitions"
            
            response = await make_http_request("GET", url)
            if response:
                for partition_info in response.get("partitions", []):
                    if partition_info["partition"] == partition:
                        leader_broker_id = partition_info["leader"]
                        
                        # Get broker endpoint
                        brokers_url = f"{coordinator_endpoint}/brokers"
                        brokers_response = await make_http_request("GET", brokers_url)
                        
                        if brokers_response:
                            for broker in brokers_response.get("brokers", []):
                                if broker["broker_id"] == leader_broker_id:
                                    return f"http://{broker['host']}:{broker['port']}"
            
            return None
            
        except Exception as e:
            logger.error("Failed to find broker for partition", error=str(e))
            return None


# Global service instance (will be configured via environment or API)
consumer_service: Optional[ConsumerService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global consumer_service
    if consumer_service:
        await consumer_service.startup()
    yield
    if consumer_service:
        await consumer_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Message Queue Consumer Service",
    description="Pull-based message consumption service",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/consumer/init", response_model=dict)
async def initialize_consumer(config: dict):
    """Initialize consumer with group and consumer ID."""
    global consumer_service
    
    try:
        group_id = config.get("group_id", "default-group")
        consumer_id = config.get("consumer_id")
        
        if consumer_service:
            await consumer_service.shutdown()
        
        consumer_service = ConsumerService(group_id, consumer_id)
        await consumer_service.startup()
        
        logger.info("Consumer initialized", group_id=group_id, consumer_id=consumer_service.consumer_id)
        
        return {
            "status": "initialized",
            "group_id": consumer_service.group_id,
            "consumer_id": consumer_service.consumer_id
        }
    
    except Exception as e:
        logger.error("Failed to initialize consumer", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/subscribe", response_model=dict)
async def subscribe_to_topics(request: dict):
    """Subscribe to topics."""
    global consumer_service
    
    try:
        if not consumer_service:
            raise HTTPException(status_code=400, detail="Consumer not initialized")
        
        topics = request.get("topics", [])
        if not topics:
            raise HTTPException(status_code=400, detail="No topics provided")
        
        await consumer_service.group_coordinator.subscribe_to_topics(topics)
        
        logger.info("Subscribed to topics", topics=topics, group_id=consumer_service.group_id)
        
        return {
            "status": "subscribed",
            "topics": topics,
            "group_id": consumer_service.group_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to subscribe to topics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/unsubscribe", response_model=dict)
async def unsubscribe_from_topics(request: dict):
    """Unsubscribe from topics."""
    global consumer_service
    
    try:
        if not consumer_service:
            raise HTTPException(status_code=400, detail="Consumer not initialized")
        
        topics = request.get("topics", [])
        if not topics:
            raise HTTPException(status_code=400, detail="No topics provided")
        
        await consumer_service.group_coordinator.unsubscribe_from_topics(topics)
        
        logger.info("Unsubscribed from topics", topics=topics, group_id=consumer_service.group_id)
        
        return {
            "status": "unsubscribed",
            "topics": topics,
            "group_id": consumer_service.group_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to unsubscribe from topics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/consume", response_model=dict)
async def poll_messages(timeout: int = 5000):
    """Poll for messages (alternative to automatic consumption)."""
    global consumer_service
    
    try:
        if not consumer_service:
            raise HTTPException(status_code=400, detail="Consumer not initialized")
        
        # Temporarily fetch messages manually
        all_messages = []
        
        for topic in consumer_service.group_coordinator.subscribed_topics:
            partitions = consumer_service.group_coordinator.get_assigned_partitions(topic)
            
            for partition in partitions:
                messages = await consumer_service._fetch_messages(topic, partition, 10)
                all_messages.extend(messages)
        
        # Update offsets for fetched messages
        for message in all_messages:
            consumer_service.offset_manager.update_offset(
                message.topic, message.partition, message.offset + 1
            )
        
        consumer_service.last_poll_time = datetime.utcnow()
        
        return {
            "status": "polled",
            "message_count": len(all_messages),
            "messages": [
                {
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "key": msg.key,
                    "value": msg.value,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in all_messages[:50]  # Limit response size
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to poll messages", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/consume/start", response_model=dict)
async def start_consuming():
    """Start automatic message consumption."""
    global consumer_service
    
    try:
        if not consumer_service:
            raise HTTPException(status_code=400, detail="Consumer not initialized")
        
        await consumer_service.start_consuming()
        
        return {
            "status": "started",
            "group_id": consumer_service.group_id,
            "consumer_id": consumer_service.consumer_id
        }
    
    except Exception as e:
        logger.error("Failed to start consuming", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/consume/stop", response_model=dict)
async def stop_consuming():
    """Stop automatic message consumption."""
    global consumer_service
    
    try:
        if not consumer_service:
            raise HTTPException(status_code=400, detail="Consumer not initialized")
        
        await consumer_service.stop_consuming()
        
        return {
            "status": "stopped",
            "group_id": consumer_service.group_id,
            "consumer_id": consumer_service.consumer_id
        }
    
    except Exception as e:
        logger.error("Failed to stop consuming", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/commit", response_model=dict)
async def commit_offsets(request: dict = None):
    """Commit current offsets."""
    global consumer_service
    
    try:
        if not consumer_service:
            raise HTTPException(status_code=400, detail="Consumer not initialized")
        
        # Extract specific topic-partitions if provided
        topics_partitions = None
        if request and "offsets" in request:
            topics_partitions = [
                (offset_data["topic"], offset_data["partition"])
                for offset_data in request["offsets"]
            ]
        
        success = await consumer_service.offset_manager.commit_offsets(topics_partitions)
        
        if success:
            return {"status": "committed", "timestamp": datetime.utcnow().isoformat()}
        else:
            raise HTTPException(status_code=500, detail="Failed to commit offsets")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to commit offsets", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=dict)
async def get_status():
    """Get consumer service status and metrics."""
    global consumer_service
    
    try:
        if not consumer_service:
            return {"status": "not_initialized"}
        
        uptime_seconds = (datetime.utcnow() - consumer_service.startup_time).total_seconds()
        
        # Get processing stats
        processing_stats = consumer_service.message_processor.get_stats()
        
        # Get assignment info
        assignments = {}
        for topic in consumer_service.group_coordinator.subscribed_topics:
            assignments[topic] = consumer_service.group_coordinator.get_assigned_partitions(topic)
        
        return {
            "service": "consumer",
            "status": "healthy",
            "group_id": consumer_service.group_id,
            "consumer_id": consumer_service.consumer_id,
            "uptime_seconds": uptime_seconds,
            "is_consuming": consumer_service.is_consuming,
            "is_group_member": consumer_service.group_coordinator.is_member,
            "metrics": {
                "consumed_messages": consumer_service.consumed_message_count,
                "processing_stats": processing_stats,
                "last_poll": consumer_service.last_poll_time.isoformat() if consumer_service.last_poll_time else None
            },
            "assignments": assignments,
            "subscribed_topics": list(consumer_service.group_coordinator.subscribed_topics)
        }
    
    except Exception as e:
        logger.error("Failed to get status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    global consumer_service
    
    try:
        if not consumer_service:
            return HealthStatus(
                service="consumer",
                status=ServiceStatus.UNHEALTHY,
                details={"error": "Consumer not initialized"}
            )
        
        # Check coordinator connectivity
        coordinator_healthy = False
        try:
            coordinator_endpoint = Config.get_coordinator_endpoint()
            url = f"{coordinator_endpoint}/health"
            response = await make_http_request("GET", url, timeout=5)
            coordinator_healthy = response and response.get("status") == "healthy"
        except:
            pass
        
        details = {
            "group_id": consumer_service.group_id,
            "consumer_id": consumer_service.consumer_id,
            "is_consuming": consumer_service.is_consuming,
            "is_group_member": consumer_service.group_coordinator.is_member,
            "consumed_messages": consumer_service.consumed_message_count,
            "coordinator_healthy": coordinator_healthy,
            "subscribed_topics": len(consumer_service.group_coordinator.subscribed_topics),
            "uptime_seconds": (datetime.utcnow() - consumer_service.startup_time).total_seconds()
        }
        
        # Determine overall health
        if not coordinator_healthy or not consumer_service.group_coordinator.is_member:
            status = ServiceStatus.UNHEALTHY
        else:
            status = ServiceStatus.HEALTHY
        
        return HealthStatus(
            service="consumer",
            status=status,
            details=details
        )
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthStatus(
            service="consumer",
            status=ServiceStatus.UNHEALTHY,
            details={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.consumer.server:app",
        host="0.0.0.0",
        port=Config.CONSUMER_PORT,
        log_level=Config.LOG_LEVEL.lower()
    )