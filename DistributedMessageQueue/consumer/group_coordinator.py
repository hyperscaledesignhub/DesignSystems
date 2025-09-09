"""Consumer group coordination for the consumer service."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import structlog

from ..shared.models import Message, ConsumerGroupInfo
from ..shared.config import Config
from ..shared.utils import make_http_request, generate_consumer_id

logger = structlog.get_logger()


class ConsumerGroupCoordinator:
    """Manages consumer group membership and partition assignments."""
    
    def __init__(self, group_id: str, consumer_id: str = None):
        self.group_id = group_id
        self.consumer_id = consumer_id or generate_consumer_id()
        self.coordinator_endpoint = Config.get_coordinator_endpoint()
        self.subscribed_topics: Set[str] = set()
        self.assigned_partitions: Dict[str, List[int]] = {}  # topic -> [partition_ids]
        self.is_member = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the group coordinator."""
        self._running = True
        logger.info("Consumer group coordinator started", group_id=self.group_id, consumer_id=self.consumer_id)
    
    async def stop(self):
        """Stop the group coordinator."""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        # Leave group if member
        if self.is_member:
            await self.leave_group()
        
        logger.info("Consumer group coordinator stopped", group_id=self.group_id, consumer_id=self.consumer_id)
    
    async def join_group(self) -> bool:
        """Join the consumer group."""
        try:
            url = f"{self.coordinator_endpoint}/consumer-groups/{self.group_id}/join"
            request_data = {"consumer_id": self.consumer_id}
            
            response = await make_http_request("POST", url, request_data)
            
            if response and response.get("status") == "joined":
                self.is_member = True
                
                # Start heartbeat
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # Get initial partition assignment
                await self._sync_assignment()
                
                logger.info("Joined consumer group", group_id=self.group_id, consumer_id=self.consumer_id)
                return True
            else:
                logger.error("Failed to join consumer group", response=response)
                return False
                
        except Exception as e:
            logger.error("Error joining consumer group", error=str(e))
            return False
    
    async def leave_group(self) -> bool:
        """Leave the consumer group."""
        try:
            if not self.is_member:
                return True
            
            url = f"{self.coordinator_endpoint}/consumer-groups/{self.group_id}/members/{self.consumer_id}"
            response = await make_http_request("DELETE", url)
            
            self.is_member = False
            self.assigned_partitions = {}
            
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            
            logger.info("Left consumer group", group_id=self.group_id, consumer_id=self.consumer_id)
            return True
            
        except Exception as e:
            logger.error("Error leaving consumer group", error=str(e))
            return False
    
    async def subscribe_to_topics(self, topics: List[str]):
        """Subscribe to topics (triggers rebalancing)."""
        self.subscribed_topics.update(topics)
        
        if self.is_member:
            # In a real implementation, we would send subscription info to coordinator
            # For simplicity, we'll just sync assignment
            await self._sync_assignment()
        
        logger.info("Subscribed to topics", topics=topics, group_id=self.group_id)
    
    async def unsubscribe_from_topics(self, topics: List[str]):
        """Unsubscribe from topics."""
        self.subscribed_topics.difference_update(topics)
        
        # Remove assignments for unsubscribed topics
        for topic in topics:
            if topic in self.assigned_partitions:
                del self.assigned_partitions[topic]
        
        logger.info("Unsubscribed from topics", topics=topics, group_id=self.group_id)
    
    def get_assigned_partitions(self, topic: str) -> List[int]:
        """Get assigned partitions for a topic."""
        return self.assigned_partitions.get(topic, [])
    
    def has_assignments(self) -> bool:
        """Check if consumer has any partition assignments."""
        return any(partitions for partitions in self.assigned_partitions.values())
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to coordinator."""
        while self._running and self.is_member:
            try:
                url = f"{self.coordinator_endpoint}/consumer-groups/{self.group_id}/heartbeat"
                heartbeat_data = {"consumer_id": self.consumer_id}
                
                response = await make_http_request("POST", url, heartbeat_data)
                
                if not response:
                    logger.warning("Heartbeat failed", group_id=self.group_id, consumer_id=self.consumer_id)
                
                # Sync assignment periodically
                await self._sync_assignment()
                
                await asyncio.sleep(Config.HEARTBEAT_INTERVAL_MS / 1000)
                
            except Exception as e:
                logger.error("Heartbeat error", error=str(e))
                await asyncio.sleep(5)
    
    async def _sync_assignment(self):
        """Sync partition assignment from coordinator."""
        try:
            url = f"{self.coordinator_endpoint}/consumer-groups/{self.group_id}/assignment"
            response = await make_http_request("GET", url)
            
            if response and "assignments" in response:
                assignments = response["assignments"]
                consumer_assignment = assignments.get(self.consumer_id, [])
                
                # For simplicity, we assume all assigned partitions are for all subscribed topics
                # In a real implementation, this would be more sophisticated
                new_assignments = {}
                for topic in self.subscribed_topics:
                    new_assignments[topic] = consumer_assignment
                
                # Check if assignment changed
                if new_assignments != self.assigned_partitions:
                    old_assignments = self.assigned_partitions.copy()
                    self.assigned_partitions = new_assignments
                    
                    logger.info(
                        "Partition assignment updated",
                        group_id=self.group_id,
                        consumer_id=self.consumer_id,
                        old_assignments=old_assignments,
                        new_assignments=new_assignments
                    )
                
        except Exception as e:
            logger.error("Failed to sync assignment", error=str(e))


class OffsetManager:
    """Manages consumer offsets for tracking consumption progress."""
    
    def __init__(self, group_id: str, consumer_id: str):
        self.group_id = group_id
        self.consumer_id = consumer_id
        self.coordinator_endpoint = Config.get_coordinator_endpoint()
        self.local_offsets: Dict[str, Dict[int, int]] = {}  # topic -> {partition -> offset}
        self.committed_offsets: Dict[str, Dict[int, int]] = {}  # topic -> {partition -> offset}
        self._auto_commit_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the offset manager."""
        self._running = True
        
        # Start auto-commit if enabled
        if Config.AUTO_COMMIT_INTERVAL_MS > 0:
            self._auto_commit_task = asyncio.create_task(self._auto_commit_loop())
        
        logger.info("Offset manager started", group_id=self.group_id)
    
    async def stop(self):
        """Stop the offset manager."""
        self._running = False
        
        if self._auto_commit_task:
            self._auto_commit_task.cancel()
        
        # Commit any pending offsets
        await self.commit_offsets()
        
        logger.info("Offset manager stopped", group_id=self.group_id)
    
    def update_offset(self, topic: str, partition: int, offset: int):
        """Update local offset for a topic-partition."""
        if topic not in self.local_offsets:
            self.local_offsets[topic] = {}
        
        self.local_offsets[topic][partition] = offset
        
        logger.debug(
            "Offset updated locally",
            topic=topic,
            partition=partition,
            offset=offset,
            group_id=self.group_id
        )
    
    def get_committed_offset(self, topic: str, partition: int) -> int:
        """Get last committed offset for a topic-partition."""
        if topic in self.committed_offsets and partition in self.committed_offsets[topic]:
            return self.committed_offsets[topic][partition]
        return 0
    
    def get_local_offset(self, topic: str, partition: int) -> int:
        """Get current local offset for a topic-partition."""
        if topic in self.local_offsets and partition in self.local_offsets[topic]:
            return self.local_offsets[topic][partition]
        return self.get_committed_offset(topic, partition)
    
    async def commit_offsets(self, topics_partitions: List[tuple] = None) -> bool:
        """Commit offsets to coordinator."""
        try:
            if topics_partitions is None:
                # Commit all local offsets
                topics_partitions = []
                for topic, partitions in self.local_offsets.items():
                    for partition in partitions:
                        topics_partitions.append((topic, partition))
            
            if not topics_partitions:
                return True
            
            # Commit each offset
            success = True
            for topic, partition in topics_partitions:
                offset = self.get_local_offset(topic, partition)
                
                # For simplicity, we'll use a mock commit endpoint
                # In a real system, this would go to the broker or coordinator
                commit_data = {
                    "group_id": self.group_id,
                    "topic": topic,
                    "partition": partition,
                    "offset": offset
                }
                
                # Mock commit (in real implementation, this would be a real API call)
                if topic not in self.committed_offsets:
                    self.committed_offsets[topic] = {}
                
                self.committed_offsets[topic][partition] = offset
                
                logger.debug(
                    "Offset committed",
                    topic=topic,
                    partition=partition,
                    offset=offset,
                    group_id=self.group_id
                )
            
            return success
            
        except Exception as e:
            logger.error("Failed to commit offsets", error=str(e))
            return False
    
    async def _auto_commit_loop(self):
        """Automatically commit offsets periodically."""
        while self._running:
            try:
                await asyncio.sleep(Config.AUTO_COMMIT_INTERVAL_MS / 1000)
                await self.commit_offsets()
                
            except Exception as e:
                logger.error("Auto-commit error", error=str(e))
                await asyncio.sleep(5)


class MessageProcessor:
    """Processes consumed messages with error handling."""
    
    def __init__(self, group_id: str, consumer_id: str):
        self.group_id = group_id
        self.consumer_id = consumer_id
        self.processed_count = 0
        self.error_count = 0
        self.message_handlers = {}  # topic -> handler function
    
    def register_handler(self, topic: str, handler_func):
        """Register a message handler for a topic."""
        self.message_handlers[topic] = handler_func
        logger.info("Handler registered", topic=topic, group_id=self.group_id)
    
    async def process_message(self, message: Message) -> bool:
        """Process a single message."""
        try:
            # Get handler for topic
            handler = self.message_handlers.get(message.topic)
            
            if handler:
                # Call custom handler
                await handler(message)
            else:
                # Default processing (just log)
                logger.info(
                    "Message processed (default)",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    key=message.key,
                    value_length=len(message.value)
                )
            
            self.processed_count += 1
            return True
            
        except Exception as e:
            self.error_count += 1
            logger.error(
                "Message processing failed",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                error=str(e)
            )
            return False
    
    async def process_batch(self, messages: List[Message]) -> int:
        """Process a batch of messages and return count of successfully processed."""
        successful = 0
        
        for message in messages:
            if await self.process_message(message):
                successful += 1
        
        return successful
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.processed_count + self.error_count, 1)
        }