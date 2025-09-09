"""Batch management for producer service."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import structlog

from ..shared.models import ProduceRequest, Message
from ..shared.config import Config
from ..shared.utils import make_http_request, calculate_partition_for_key

logger = structlog.get_logger()


@dataclass
class MessageBatch:
    """Represents a batch of messages for a topic-partition."""
    topic: str
    partition: int
    messages: List[ProduceRequest] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_full(self) -> bool:
        """Check if batch is full."""
        return len(self.messages) >= Config.BATCH_SIZE
    
    def is_expired(self) -> bool:
        """Check if batch has expired."""
        timeout = timedelta(milliseconds=Config.BATCH_TIMEOUT_MS)
        return datetime.utcnow() - self.created_at > timeout
    
    def add_message(self, message: ProduceRequest) -> bool:
        """Add message to batch if not full."""
        if self.is_full():
            return False
        self.messages.append(message)
        return True


class BatchManager:
    """Manages message batching for efficient sending."""
    
    def __init__(self, broker_endpoints: List[str]):
        self.broker_endpoints = broker_endpoints
        self.batches: Dict[str, MessageBatch] = {}  # topic:partition -> batch
        self.topic_partitions: Dict[str, int] = {}  # topic -> partition_count
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start the batch manager."""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("Batch manager started")
    
    async def stop(self):
        """Stop the batch manager."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
        
        # Flush all remaining batches
        await self._flush_all_batches()
        logger.info("Batch manager stopped")
    
    async def add_message(self, message: ProduceRequest) -> Dict[str, any]:
        """Add message to batch and return response when sent."""
        async with self._lock:
            # Get topic partition count
            partition_count = await self._get_topic_partition_count(message.topic)
            if partition_count == 0:
                raise ValueError(f"Topic {message.topic} not found or has no partitions")
            
            # Determine partition
            if message.partition is not None:
                if message.partition >= partition_count:
                    raise ValueError(f"Invalid partition {message.partition}")
                partition = message.partition
            else:
                partition = calculate_partition_for_key(message.key, partition_count)
            
            batch_key = f"{message.topic}:{partition}"
            
            # Get or create batch
            if batch_key not in self.batches:
                self.batches[batch_key] = MessageBatch(message.topic, partition)
            
            batch = self.batches[batch_key]
            
            # Add message to batch
            if not batch.add_message(message):
                # Batch is full, flush it first
                await self._flush_batch(batch_key)
                
                # Create new batch and add message
                self.batches[batch_key] = MessageBatch(message.topic, partition)
                self.batches[batch_key].add_message(message)
            
            # If batch is now full, flush immediately
            if self.batches[batch_key].is_full():
                return await self._flush_batch(batch_key)
            
            # Return pending response (will be resolved during periodic flush)
            return {"status": "batched", "partition": partition}
    
    async def _get_topic_partition_count(self, topic: str) -> int:
        """Get partition count for a topic."""
        if topic in self.topic_partitions:
            return self.topic_partitions[topic]
        
        # Query broker for topic info
        for endpoint in self.broker_endpoints:
            try:
                url = f"{endpoint}/topics"
                response = await make_http_request("GET", url)
                
                if response:
                    for topic_info in response.get("topics", []):
                        if topic_info["name"] == topic:
                            partition_count = topic_info["partitions"]
                            self.topic_partitions[topic] = partition_count
                            return partition_count
            except Exception as e:
                logger.warning("Failed to get topic info from broker", endpoint=endpoint, error=str(e))
                continue
        
        return 0
    
    async def _periodic_flush(self):
        """Periodically flush expired batches."""
        while self._running:
            try:
                await asyncio.sleep(Config.BATCH_TIMEOUT_MS / 1000 / 2)  # Check at half the timeout
                
                async with self._lock:
                    expired_batches = []
                    
                    for batch_key, batch in self.batches.items():
                        if batch.is_expired():
                            expired_batches.append(batch_key)
                    
                    for batch_key in expired_batches:
                        await self._flush_batch(batch_key)
                        
            except Exception as e:
                logger.error("Error in periodic flush", error=str(e))
                await asyncio.sleep(1)
    
    async def _flush_batch(self, batch_key: str) -> Dict[str, any]:
        """Flush a specific batch."""
        if batch_key not in self.batches:
            return {"status": "no_batch"}
        
        batch = self.batches[batch_key]
        del self.batches[batch_key]
        
        if not batch.messages:
            return {"status": "empty_batch"}
        
        # Find leader broker for this partition
        leader_broker = await self._find_leader_broker(batch.topic, batch.partition)
        if not leader_broker:
            logger.error("No leader broker found", topic=batch.topic, partition=batch.partition)
            return {"status": "no_leader", "error": "No leader broker available"}
        
        # Send batch to leader broker
        try:
            responses = []
            for message in batch.messages:
                response = await self._send_message_to_broker(leader_broker, message)
                responses.append(response)
            
            logger.info(
                "Batch flushed successfully",
                topic=batch.topic,
                partition=batch.partition,
                message_count=len(batch.messages),
                broker=leader_broker
            )
            
            return {
                "status": "sent",
                "topic": batch.topic,
                "partition": batch.partition,
                "message_count": len(batch.messages),
                "responses": responses
            }
            
        except Exception as e:
            logger.error(
                "Failed to flush batch",
                topic=batch.topic,
                partition=batch.partition,
                error=str(e)
            )
            return {"status": "failed", "error": str(e)}
    
    async def _flush_all_batches(self):
        """Flush all remaining batches."""
        async with self._lock:
            batch_keys = list(self.batches.keys())
            for batch_key in batch_keys:
                await self._flush_batch(batch_key)
    
    async def _find_leader_broker(self, topic: str, partition: int) -> Optional[str]:
        """Find the leader broker for a topic-partition."""
        # Query coordinator for partition info
        coordinator_endpoint = Config.get_coordinator_endpoint()
        url = f"{coordinator_endpoint}/topics/{topic}/partitions"
        
        try:
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
        except Exception as e:
            logger.error("Failed to find leader broker", error=str(e))
        
        return None
    
    async def _send_message_to_broker(self, broker_endpoint: str, message: ProduceRequest) -> Dict[str, any]:
        """Send a single message to a broker."""
        url = f"{broker_endpoint}/topics/{message.topic}/messages"
        
        message_data = {
            "topic": message.topic,
            "key": message.key,
            "value": message.value,
            "partition": message.partition
        }
        
        response = await make_http_request("POST", url, message_data, retries=Config.RETRY_ATTEMPTS)
        
        if response:
            return response
        else:
            raise Exception("Failed to send message to broker")


class RetryManager:
    """Manages retry logic for failed message sends."""
    
    def __init__(self, max_retries: int = None):
        self.max_retries = max_retries or Config.RETRY_ATTEMPTS
        self.retry_queues: Dict[str, List[ProduceRequest]] = {}  # topic:partition -> messages
        self._retry_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the retry manager."""
        self._running = True
        self._retry_task = asyncio.create_task(self._process_retries())
        logger.info("Retry manager started")
    
    async def stop(self):
        """Stop the retry manager."""
        self._running = False
        if self._retry_task:
            self._retry_task.cancel()
        logger.info("Retry manager stopped")
    
    async def add_failed_message(self, message: ProduceRequest, partition: int):
        """Add a failed message for retry."""
        key = f"{message.topic}:{partition}"
        
        if key not in self.retry_queues:
            self.retry_queues[key] = []
        
        # Add retry count to message (using a custom attribute)
        if not hasattr(message, 'retry_count'):
            message.retry_count = 0
        
        if message.retry_count < self.max_retries:
            message.retry_count += 1
            self.retry_queues[key].append(message)
            logger.info(
                "Message queued for retry",
                topic=message.topic,
                partition=partition,
                retry_count=message.retry_count
            )
        else:
            logger.error(
                "Message exceeded max retries",
                topic=message.topic,
                partition=partition,
                retry_count=message.retry_count
            )
    
    async def _process_retries(self):
        """Process retry queues periodically."""
        while self._running:
            try:
                for key, messages in list(self.retry_queues.items()):
                    if messages:
                        # Try to resend the first message in the queue
                        message = messages.pop(0)
                        
                        # In a real implementation, you would integrate this with the batch manager
                        # For now, we'll just log the retry attempt
                        logger.info(
                            "Retrying message",
                            topic=message.topic,
                            key=key,
                            retry_count=getattr(message, 'retry_count', 0)
                        )
                
                await asyncio.sleep(1)  # Retry every second
                
            except Exception as e:
                logger.error("Error in retry processing", error=str(e))
                await asyncio.sleep(5)