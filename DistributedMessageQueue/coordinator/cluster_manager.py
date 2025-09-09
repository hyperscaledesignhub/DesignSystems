"""Cluster management for the coordinator service."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import structlog

from ..shared.models import BrokerInfo, PartitionInfo, ConsumerGroupInfo, ServiceStatus
from ..shared.config import Config

logger = structlog.get_logger()


class ClusterManager:
    """Manages broker cluster membership and partition assignments."""
    
    def __init__(self):
        self.brokers: Dict[str, BrokerInfo] = {}
        self.partitions: Dict[str, PartitionInfo] = {}  # topic:partition -> info
        self.topic_configs: Dict[str, dict] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the cluster manager."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_dead_brokers())
        logger.info("Cluster manager started")
    
    async def stop(self):
        """Stop the cluster manager."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Cluster manager stopped")
    
    async def register_broker(self, broker_info: BrokerInfo) -> bool:
        """Register a new broker in the cluster."""
        self.brokers[broker_info.broker_id] = broker_info
        logger.info(
            "Broker registered",
            broker_id=broker_info.broker_id,
            host=broker_info.host,
            port=broker_info.port
        )
        
        # Trigger partition rebalancing if needed
        await self._rebalance_partitions()
        return True
    
    async def unregister_broker(self, broker_id: str) -> bool:
        """Unregister a broker from the cluster."""
        if broker_id in self.brokers:
            del self.brokers[broker_id]
            logger.info("Broker unregistered", broker_id=broker_id)
            
            # Trigger partition rebalancing
            await self._rebalance_partitions()
            return True
        return False
    
    async def update_broker_heartbeat(self, broker_id: str) -> bool:
        """Update broker heartbeat timestamp."""
        if broker_id in self.brokers:
            self.brokers[broker_id].last_heartbeat = datetime.utcnow()
            self.brokers[broker_id].status = ServiceStatus.HEALTHY
            return True
        return False
    
    def get_brokers(self) -> List[BrokerInfo]:
        """Get list of all registered brokers."""
        return list(self.brokers.values())
    
    def get_healthy_brokers(self) -> List[BrokerInfo]:
        """Get list of healthy brokers."""
        return [
            broker for broker in self.brokers.values()
            if broker.status == ServiceStatus.HEALTHY
        ]
    
    async def create_topic_partitions(
        self, 
        topic: str, 
        partition_count: int, 
        replication_factor: int
    ) -> bool:
        """Create partition assignments for a new topic."""
        healthy_brokers = self.get_healthy_brokers()
        
        if len(healthy_brokers) < replication_factor:
            logger.error(
                "Not enough healthy brokers for replication",
                required=replication_factor,
                available=len(healthy_brokers)
            )
            return False
        
        self.topic_configs[topic] = {
            "partitions": partition_count,
            "replication_factor": replication_factor
        }
        
        # Create partition assignments
        for partition_id in range(partition_count):
            # Simple round-robin assignment
            leader_index = partition_id % len(healthy_brokers)
            leader_broker = healthy_brokers[leader_index]
            
            # Select replicas (including leader)
            replicas = []
            for i in range(replication_factor):
                replica_index = (leader_index + i) % len(healthy_brokers)
                replicas.append(healthy_brokers[replica_index].broker_id)
            
            partition_info = PartitionInfo(
                topic=topic,
                partition=partition_id,
                leader=leader_broker.broker_id,
                replicas=replicas,
                in_sync_replicas=replicas.copy()  # Initially all replicas are in sync
            )
            
            key = f"{topic}:{partition_id}"
            self.partitions[key] = partition_info
        
        logger.info(
            "Created topic partitions",
            topic=topic,
            partitions=partition_count,
            replication_factor=replication_factor
        )
        
        return True
    
    def get_partitions(self) -> List[PartitionInfo]:
        """Get all partition information."""
        return list(self.partitions.values())
    
    def get_topic_partitions(self, topic: str) -> List[PartitionInfo]:
        """Get partitions for a specific topic."""
        return [
            partition for partition in self.partitions.values()
            if partition.topic == topic
        ]
    
    async def elect_leader(self, topic: str, partition: int, candidate_broker: str = None) -> Optional[str]:
        """Elect a new leader for a partition."""
        key = f"{topic}:{partition}"
        partition_info = self.partitions.get(key)
        
        if not partition_info:
            return None
        
        healthy_brokers = self.get_healthy_brokers()
        healthy_broker_ids = {broker.broker_id for broker in healthy_brokers}
        
        # Find available replicas that are healthy
        available_replicas = [
            replica for replica in partition_info.replicas
            if replica in healthy_broker_ids
        ]
        
        if not available_replicas:
            logger.error("No healthy replicas available for leader election")
            return None
        
        # Choose new leader
        new_leader = None
        if candidate_broker and candidate_broker in available_replicas:
            new_leader = candidate_broker
        else:
            # Choose first available healthy replica
            new_leader = available_replicas[0]
        
        # Update partition info
        partition_info.leader = new_leader
        partition_info.in_sync_replicas = available_replicas
        
        logger.info(
            "Leader elected",
            topic=topic,
            partition=partition,
            new_leader=new_leader,
            available_replicas=len(available_replicas)
        )
        
        return new_leader
    
    async def _rebalance_partitions(self):
        """Rebalance partitions when cluster membership changes."""
        healthy_brokers = self.get_healthy_brokers()
        
        if not healthy_brokers:
            logger.warning("No healthy brokers available for rebalancing")
            return
        
        # For each partition, ensure leader is healthy
        for key, partition_info in self.partitions.items():
            current_leader = partition_info.leader
            
            # Check if current leader is still healthy
            leader_healthy = any(
                broker.broker_id == current_leader and broker.status == ServiceStatus.HEALTHY
                for broker in healthy_brokers
            )
            
            if not leader_healthy:
                # Elect new leader
                await self.elect_leader(partition_info.topic, partition_info.partition)
        
        logger.info("Partition rebalancing completed")
    
    async def _cleanup_dead_brokers(self):
        """Periodically clean up dead brokers."""
        while self._running:
            try:
                cutoff_time = datetime.utcnow() - timedelta(
                    milliseconds=Config.SESSION_TIMEOUT_MS
                )
                
                dead_brokers = []
                for broker_id, broker in self.brokers.items():
                    if broker.last_heartbeat < cutoff_time:
                        broker.status = ServiceStatus.UNHEALTHY
                        dead_brokers.append(broker_id)
                
                for broker_id in dead_brokers:
                    logger.warning("Marking broker as dead", broker_id=broker_id)
                    await self.unregister_broker(broker_id)
                
                await asyncio.sleep(Config.HEARTBEAT_INTERVAL_MS / 1000)
                
            except Exception as e:
                logger.error("Error in cleanup task", error=str(e))
                await asyncio.sleep(5)


class ConsumerGroupManager:
    """Manages consumer group memberships and assignments."""
    
    def __init__(self, cluster_manager: ClusterManager):
        self.cluster_manager = cluster_manager
        self.consumer_groups: Dict[str, ConsumerGroupInfo] = {}
        self.consumer_heartbeats: Dict[str, datetime] = {}  # consumer_id -> last_heartbeat
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the consumer group manager."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_dead_consumers())
        logger.info("Consumer group manager started")
    
    async def stop(self):
        """Stop the consumer group manager."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Consumer group manager stopped")
    
    async def join_group(self, group_id: str, consumer_id: str) -> bool:
        """Add consumer to a group."""
        if group_id not in self.consumer_groups:
            self.consumer_groups[group_id] = ConsumerGroupInfo(
                group_id=group_id,
                members=[],
                assignments={}
            )
        
        group = self.consumer_groups[group_id]
        if consumer_id not in group.members:
            group.members.append(consumer_id)
            self.consumer_heartbeats[consumer_id] = datetime.utcnow()
            
            # Trigger rebalancing
            await self._rebalance_group(group_id)
            
            logger.info("Consumer joined group", group_id=group_id, consumer_id=consumer_id)
            return True
        
        return False
    
    async def leave_group(self, group_id: str, consumer_id: str) -> bool:
        """Remove consumer from a group."""
        if group_id not in self.consumer_groups:
            return False
        
        group = self.consumer_groups[group_id]
        if consumer_id in group.members:
            group.members.remove(consumer_id)
            if consumer_id in group.assignments:
                del group.assignments[consumer_id]
            
            if consumer_id in self.consumer_heartbeats:
                del self.consumer_heartbeats[consumer_id]
            
            # Trigger rebalancing
            await self._rebalance_group(group_id)
            
            logger.info("Consumer left group", group_id=group_id, consumer_id=consumer_id)
            return True
        
        return False
    
    async def update_consumer_heartbeat(self, consumer_id: str) -> bool:
        """Update consumer heartbeat."""
        self.consumer_heartbeats[consumer_id] = datetime.utcnow()
        return True
    
    def get_group_assignment(self, group_id: str) -> Optional[Dict[str, List[int]]]:
        """Get partition assignments for a consumer group."""
        if group_id not in self.consumer_groups:
            return None
        return self.consumer_groups[group_id].assignments.copy()
    
    def get_consumer_groups(self) -> List[ConsumerGroupInfo]:
        """Get all consumer groups."""
        return list(self.consumer_groups.values())
    
    async def _rebalance_group(self, group_id: str):
        """Rebalance partition assignments for a consumer group."""
        if group_id not in self.consumer_groups:
            return
        
        group = self.consumer_groups[group_id]
        if not group.members:
            group.assignments = {}
            return
        
        # Get all partitions (for simplicity, we'll assign all partitions)
        # In a real system, consumers would subscribe to specific topics
        all_partitions = self.cluster_manager.get_partitions()
        
        # Simple round-robin assignment
        assignments = {member: [] for member in group.members}
        
        for i, partition in enumerate(all_partitions):
            consumer_index = i % len(group.members)
            consumer_id = group.members[consumer_index]
            assignments[consumer_id].append(partition.partition)
        
        group.assignments = assignments
        group.state = "rebalancing"
        
        # In a real system, we would wait for consumers to acknowledge
        # For simplicity, we'll mark as stable immediately
        await asyncio.sleep(0.1)
        group.state = "stable"
        
        logger.info(
            "Consumer group rebalanced",
            group_id=group_id,
            members=len(group.members),
            assignments=len(assignments)
        )
    
    async def _cleanup_dead_consumers(self):
        """Periodically clean up dead consumers."""
        while self._running:
            try:
                cutoff_time = datetime.utcnow() - timedelta(
                    milliseconds=Config.SESSION_TIMEOUT_MS
                )
                
                dead_consumers = []
                for consumer_id, last_heartbeat in self.consumer_heartbeats.items():
                    if last_heartbeat < cutoff_time:
                        dead_consumers.append(consumer_id)
                
                # Remove dead consumers from groups
                for consumer_id in dead_consumers:
                    for group_id, group in self.consumer_groups.items():
                        if consumer_id in group.members:
                            await self.leave_group(group_id, consumer_id)
                
                await asyncio.sleep(Config.HEARTBEAT_INTERVAL_MS / 1000)
                
            except Exception as e:
                logger.error("Error in consumer cleanup task", error=str(e))
                await asyncio.sleep(5)