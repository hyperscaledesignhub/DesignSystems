"""Write-Ahead Log storage implementation for the broker."""
import json
import asyncio
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import structlog

from ..shared.models import Message, TopicConfig
from ..shared.utils import AsyncFileWriter, ensure_directory, serialize_message, deserialize_message
from ..shared.config import Config

logger = structlog.get_logger()


class SegmentFile:
    """Represents a single log segment file."""
    
    def __init__(self, topic: str, partition: int, segment_id: int, base_dir: str):
        self.topic = topic
        self.partition = partition
        self.segment_id = segment_id
        self.base_dir = base_dir
        self.file_path = self._get_file_path()
        self.writer = AsyncFileWriter(self.file_path)
        self.current_offset = 0
        self.size_bytes = 0
        
    def _get_file_path(self) -> str:
        """Get the file path for this segment."""
        partition_dir = Path(self.base_dir) / self.topic / f"partition-{self.partition}"
        ensure_directory(str(partition_dir))
        return str(partition_dir / f"segment-{self.segment_id}.log")
    
    async def append_message(self, message: Message) -> int:
        """Append a message to this segment and return the offset."""
        message.offset = self.current_offset
        message.timestamp = datetime.utcnow()
        
        # Serialize message
        message_data = {
            "key": message.key,
            "value": message.value,
            "topic": message.topic,
            "partition": message.partition,
            "offset": message.offset,
            "timestamp": message.timestamp.isoformat(),
            "size": len(message.value.encode('utf-8'))
        }
        
        serialized = json.dumps(message_data)
        await self.writer.append(serialized)
        
        self.size_bytes += len(serialized.encode('utf-8'))
        offset = self.current_offset
        self.current_offset += 1
        
        logger.info(
            "Message appended to segment",
            topic=self.topic,
            partition=self.partition,
            segment=self.segment_id,
            offset=offset
        )
        
        return offset
    
    async def read_messages(self, start_offset: int, limit: int) -> List[Message]:
        """Read messages from this segment starting from offset."""
        lines = await self.writer.read_lines()
        messages = []
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
                if data["offset"] >= start_offset:
                    message = Message(
                        key=data.get("key"),
                        value=data["value"],
                        topic=data["topic"],
                        partition=data["partition"],
                        offset=data["offset"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        size=data["size"]
                    )
                    messages.append(message)
                    
                    if len(messages) >= limit:
                        break
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Invalid message format in segment", error=str(e))
                continue
        
        return messages
    
    def is_full(self) -> bool:
        """Check if segment is full."""
        return self.size_bytes >= Config.MAX_SEGMENT_SIZE


class Partition:
    """Represents a topic partition with multiple segments."""
    
    def __init__(self, topic: str, partition_id: int, base_dir: str):
        self.topic = topic
        self.partition_id = partition_id
        self.base_dir = base_dir
        self.segments: List[SegmentFile] = []
        self.active_segment: Optional[SegmentFile] = None
        self.next_offset = 0
        self._create_initial_segment()
    
    def _create_initial_segment(self):
        """Create the initial segment for this partition."""
        segment = SegmentFile(self.topic, self.partition_id, 0, self.base_dir)
        self.segments.append(segment)
        self.active_segment = segment
    
    async def append_message(self, message: Message) -> int:
        """Append message to the partition."""
        # Check if we need a new segment
        if self.active_segment and self.active_segment.is_full():
            await self._create_new_segment()
        
        message.partition = self.partition_id
        offset = await self.active_segment.append_message(message)
        self.next_offset = max(self.next_offset, offset + 1)
        return offset
    
    async def _create_new_segment(self):
        """Create a new active segment."""
        new_segment_id = len(self.segments)
        new_segment = SegmentFile(self.topic, self.partition_id, new_segment_id, self.base_dir)
        new_segment.current_offset = self.next_offset
        self.segments.append(new_segment)
        self.active_segment = new_segment
        
        logger.info(
            "Created new segment",
            topic=self.topic,
            partition=self.partition_id,
            segment_id=new_segment_id
        )
    
    async def read_messages(self, start_offset: int, limit: int) -> Tuple[List[Message], int]:
        """Read messages from the partition starting from offset."""
        messages = []
        remaining_limit = limit
        
        for segment in self.segments:
            if remaining_limit <= 0:
                break
                
            segment_messages = await segment.read_messages(start_offset, remaining_limit)
            messages.extend(segment_messages)
            remaining_limit -= len(segment_messages)
            
            # Update start_offset for next segment
            if segment_messages:
                start_offset = max(start_offset, segment_messages[-1].offset + 1)
        
        next_offset = start_offset if not messages else messages[-1].offset + 1
        return messages, next_offset


class WALStorage:
    """Write-Ahead Log storage implementation."""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or Config.DATA_DIR
        self.topics: Dict[str, Dict[int, Partition]] = {}
        self.topic_configs: Dict[str, TopicConfig] = {}
        ensure_directory(self.base_dir)
    
    async def create_topic(self, topic_config: TopicConfig) -> bool:
        """Create a new topic with partitions."""
        if topic_config.name in self.topics:
            return False
        
        self.topic_configs[topic_config.name] = topic_config
        self.topics[topic_config.name] = {}
        
        # Create partitions
        for partition_id in range(topic_config.partitions):
            partition = Partition(topic_config.name, partition_id, self.base_dir)
            self.topics[topic_config.name][partition_id] = partition
        
        logger.info(
            "Topic created",
            topic=topic_config.name,
            partitions=topic_config.partitions,
            replication_factor=topic_config.replication_factor
        )
        
        return True
    
    async def append_message(self, message: Message) -> Optional[int]:
        """Append a message to the specified topic and partition."""
        if message.topic not in self.topics:
            logger.warning("Topic not found", topic=message.topic)
            return None
        
        if message.partition not in self.topics[message.topic]:
            logger.warning(
                "Partition not found",
                topic=message.topic,
                partition=message.partition
            )
            return None
        
        partition = self.topics[message.topic][message.partition]
        offset = await partition.append_message(message)
        
        logger.debug(
            "Message appended",
            topic=message.topic,
            partition=message.partition,
            offset=offset
        )
        
        return offset
    
    async def read_messages(
        self,
        topic: str,
        partition: int,
        start_offset: int,
        limit: int = 100
    ) -> Tuple[List[Message], int]:
        """Read messages from the specified topic and partition."""
        if topic not in self.topics:
            return [], start_offset
        
        if partition not in self.topics[topic]:
            return [], start_offset
        
        partition_obj = self.topics[topic][partition]
        return await partition_obj.read_messages(start_offset, limit)
    
    def get_topics(self) -> List[str]:
        """Get list of all topics."""
        return list(self.topics.keys())
    
    def get_topic_info(self, topic: str) -> Optional[TopicConfig]:
        """Get topic configuration."""
        return self.topic_configs.get(topic)
    
    def get_partition_count(self, topic: str) -> int:
        """Get number of partitions for a topic."""
        if topic in self.topics:
            return len(self.topics[topic])
        return 0
    
    async def get_latest_offset(self, topic: str, partition: int) -> int:
        """Get the latest offset for a partition."""
        if topic not in self.topics or partition not in self.topics[topic]:
            return 0
        
        partition_obj = self.topics[topic][partition]
        return partition_obj.next_offset