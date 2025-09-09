"""Shared data models for the distributed message queue system."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MessageStatus(str, Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    FAILED = "failed"


class ReplicaRole(str, Enum):
    LEADER = "leader"
    FOLLOWER = "follower"


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class Message(BaseModel):
    """Core message model."""
    key: Optional[str] = None
    value: str
    topic: str
    partition: int
    offset: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    size: int = 0
    
    def model_post_init(self, __context) -> None:
        if self.size == 0:
            self.size = len(self.value.encode('utf-8'))


class ProduceRequest(BaseModel):
    """Request to produce a message."""
    topic: str
    key: Optional[str] = None
    value: str
    partition: Optional[int] = None


class ProduceResponse(BaseModel):
    """Response for produce request."""
    topic: str
    partition: int
    offset: int
    timestamp: datetime


class ConsumeRequest(BaseModel):
    """Request to consume messages."""
    topic: str
    partition: int
    offset: int = 0
    limit: int = 100
    timeout: int = 5000  # milliseconds


class ConsumeResponse(BaseModel):
    """Response for consume request."""
    messages: List[Message]
    next_offset: int


class TopicConfig(BaseModel):
    """Topic configuration."""
    name: str
    partitions: int = 3
    replication_factor: int = 3
    retention_ms: int = 604800000  # 7 days
    max_segment_size: int = 1073741824  # 1GB


class PartitionInfo(BaseModel):
    """Partition information."""
    topic: str
    partition: int
    leader: str  # broker_id
    replicas: List[str]
    in_sync_replicas: List[str]


class BrokerInfo(BaseModel):
    """Broker information."""
    broker_id: str
    host: str
    port: int
    status: ServiceStatus = ServiceStatus.HEALTHY
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)


class ConsumerGroupInfo(BaseModel):
    """Consumer group information."""
    group_id: str
    members: List[str]
    assignments: Dict[str, List[int]]  # consumer_id -> partition_ids
    state: str = "stable"


class OffsetCommitRequest(BaseModel):
    """Request to commit consumer offset."""
    group_id: str
    topic: str
    partition: int
    offset: int


class HealthStatus(BaseModel):
    """Health status response."""
    service: str
    status: ServiceStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = {}


class MetricPoint(BaseModel):
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = {}


class SystemMetrics(BaseModel):
    """System-wide metrics."""
    metrics: List[MetricPoint]
    timestamp: datetime = Field(default_factory=datetime.utcnow)