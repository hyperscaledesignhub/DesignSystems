"""Replication manager for broker clustering."""
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Set
import structlog

from ..shared.models import Message, BrokerInfo, PartitionInfo, ReplicaRole
from ..shared.utils import make_http_request, generate_broker_id
from ..shared.config import Config

logger = structlog.get_logger()


class ReplicationManager:
    """Manages replication between broker instances."""
    
    def __init__(self, broker_id: str, storage, coordinator_endpoint: str):
        self.broker_id = broker_id
        self.storage = storage
        self.coordinator_endpoint = coordinator_endpoint
        self.cluster_brokers: Dict[str, BrokerInfo] = {}
        self.partition_assignments: Dict[str, PartitionInfo] = {}  # topic:partition -> info
        self.replica_roles: Dict[str, ReplicaRole] = {}  # topic:partition -> role
        self.replication_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
    
    async def start(self):
        """Start the replication manager."""
        self._running = True
        
        # Register with coordinator
        await self._register_with_coordinator()
        
        # Start periodic tasks
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._sync_cluster_state())
        
        logger.info("Replication manager started", broker_id=self.broker_id)
    
    async def stop(self):
        """Stop the replication manager."""
        self._running = False
        
        # Cancel replication tasks
        for task in self.replication_tasks.values():
            task.cancel()
        
        # Unregister from coordinator
        await self._unregister_from_coordinator()
        
        logger.info("Replication manager stopped", broker_id=self.broker_id)
    
    async def _register_with_coordinator(self):
        """Register this broker with the coordinator."""
        broker_info = {
            "broker_id": self.broker_id,
            "host": "localhost",  # In real deployment, this would be the actual host
            "port": Config.BROKER_PORT,
            "status": "healthy"
        }
        
        url = f"{self.coordinator_endpoint}/brokers/register"
        result = await make_http_request("POST", url, broker_info)
        
        if result:
            logger.info("Registered with coordinator", broker_id=self.broker_id)
        else:
            logger.error("Failed to register with coordinator")
    
    async def _unregister_from_coordinator(self):
        """Unregister this broker from the coordinator."""
        url = f"{self.coordinator_endpoint}/brokers/{self.broker_id}"
        await make_http_request("DELETE", url)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to coordinator."""
        while self._running:
            try:
                heartbeat_data = {
                    "broker_id": self.broker_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "healthy"
                }
                
                url = f"{self.coordinator_endpoint}/brokers/{self.broker_id}/heartbeat"
                await make_http_request("POST", url, heartbeat_data)
                
                await asyncio.sleep(Config.HEARTBEAT_INTERVAL_MS / 1000)
            except Exception as e:
                logger.error("Heartbeat failed", error=str(e))
                await asyncio.sleep(5)
    
    async def _sync_cluster_state(self):
        """Sync cluster state from coordinator."""
        while self._running:
            try:
                # Get cluster brokers
                url = f"{self.coordinator_endpoint}/brokers"
                brokers_data = await make_http_request("GET", url)
                
                if brokers_data:
                    self.cluster_brokers = {
                        broker["broker_id"]: BrokerInfo(**broker)
                        for broker in brokers_data.get("brokers", [])
                    }
                
                # Get partition assignments
                url = f"{self.coordinator_endpoint}/partitions"
                partitions_data = await make_http_request("GET", url)
                
                if partitions_data:
                    for partition_data in partitions_data.get("partitions", []):
                        key = f"{partition_data['topic']}:{partition_data['partition']}"
                        self.partition_assignments[key] = PartitionInfo(**partition_data)
                        
                        # Determine our role for this partition
                        if self.broker_id == partition_data["leader"]:
                            self.replica_roles[key] = ReplicaRole.LEADER
                            await self._start_replication_for_partition(
                                partition_data["topic"], 
                                partition_data["partition"]
                            )
                        elif self.broker_id in partition_data["replicas"]:
                            self.replica_roles[key] = ReplicaRole.FOLLOWER
                
                await asyncio.sleep(10)  # Sync every 10 seconds
            except Exception as e:
                logger.error("Failed to sync cluster state", error=str(e))
                await asyncio.sleep(5)
    
    async def _start_replication_for_partition(self, topic: str, partition: int):
        """Start replication task for a partition where we are the leader."""
        key = f"{topic}:{partition}"
        
        if key in self.replication_tasks:
            return  # Already replicating
        
        task = asyncio.create_task(
            self._replicate_partition(topic, partition)
        )
        self.replication_tasks[key] = task
        
        logger.info(
            "Started replication for partition",
            topic=topic,
            partition=partition,
            broker_id=self.broker_id
        )
    
    async def _replicate_partition(self, topic: str, partition: int):
        """Replicate messages for a partition to follower replicas."""
        key = f"{topic}:{partition}"
        
        try:
            while self._running and key in self.replica_roles:
                if self.replica_roles[key] != ReplicaRole.LEADER:
                    break
                
                # Get partition info
                partition_info = self.partition_assignments.get(key)
                if not partition_info:
                    await asyncio.sleep(1)
                    continue
                
                # Get follower replicas
                followers = [
                    replica for replica in partition_info.replicas
                    if replica != self.broker_id and replica in self.cluster_brokers
                ]
                
                if not followers:
                    await asyncio.sleep(1)
                    continue
                
                # Get latest messages to replicate
                latest_offset = await self.storage.get_latest_offset(topic, partition)
                
                # For simplicity, we'll replicate in batches
                # In a real system, this would be more sophisticated
                for follower_id in followers:
                    await self._replicate_to_follower(
                        follower_id, topic, partition, latest_offset
                    )
                
                await asyncio.sleep(0.1)  # Replicate every 100ms
                
        except asyncio.CancelledError:
            logger.info("Replication task cancelled", topic=topic, partition=partition)
        except Exception as e:
            logger.error(
                "Replication task failed",
                topic=topic,
                partition=partition,
                error=str(e)
            )
    
    async def _replicate_to_follower(
        self, 
        follower_id: str, 
        topic: str, 
        partition: int,
        up_to_offset: int
    ):
        """Replicate messages to a specific follower."""
        try:
            follower_broker = self.cluster_brokers.get(follower_id)
            if not follower_broker:
                return
            
            # Get follower's last known offset
            follower_url = f"http://{follower_broker.host}:{follower_broker.port}"
            offset_url = f"{follower_url}/internal/replica/offset/{topic}/{partition}"
            
            offset_response = await make_http_request("GET", offset_url)
            follower_offset = 0
            if offset_response:
                follower_offset = offset_response.get("offset", 0)
            
            # If follower is behind, send missing messages
            if follower_offset < up_to_offset:
                messages, _ = await self.storage.read_messages(
                    topic, partition, follower_offset, min(100, up_to_offset - follower_offset)
                )
                
                if messages:
                    # Send messages to follower
                    replicate_url = f"{follower_url}/internal/replica/append"
                    replicate_data = {
                        "topic": topic,
                        "partition": partition,
                        "messages": [
                            {
                                "key": msg.key,
                                "value": msg.value,
                                "offset": msg.offset,
                                "timestamp": msg.timestamp.isoformat()
                            }
                            for msg in messages
                        ]
                    }
                    
                    await make_http_request("POST", replicate_url, replicate_data)
                    
        except Exception as e:
            logger.error(
                "Failed to replicate to follower",
                follower_id=follower_id,
                topic=topic,
                partition=partition,
                error=str(e)
            )
    
    def is_leader(self, topic: str, partition: int) -> bool:
        """Check if this broker is the leader for a partition."""
        key = f"{topic}:{partition}"
        return self.replica_roles.get(key) == ReplicaRole.LEADER
    
    def is_replica(self, topic: str, partition: int) -> bool:
        """Check if this broker is a replica for a partition."""
        key = f"{topic}:{partition}"
        return key in self.replica_roles
    
    async def handle_leader_election(self, topic: str, partition: int):
        """Handle leader election for a partition."""
        key = f"{topic}:{partition}"
        
        # Request leader election from coordinator
        election_data = {
            "topic": topic,
            "partition": partition,
            "candidate_broker": self.broker_id
        }
        
        url = f"{self.coordinator_endpoint}/leader-election"
        result = await make_http_request("POST", url, election_data)
        
        if result and result.get("leader") == self.broker_id:
            self.replica_roles[key] = ReplicaRole.LEADER
            await self._start_replication_for_partition(topic, partition)
            logger.info(
                "Elected as leader",
                topic=topic,
                partition=partition,
                broker_id=self.broker_id
            )
        
    def get_partition_info(self, topic: str, partition: int) -> Optional[PartitionInfo]:
        """Get partition information."""
        key = f"{topic}:{partition}"
        return self.partition_assignments.get(key)