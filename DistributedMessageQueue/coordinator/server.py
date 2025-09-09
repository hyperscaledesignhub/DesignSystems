"""Coordinator service implementation."""
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import structlog

from ..shared.models import (
    BrokerInfo, PartitionInfo, ConsumerGroupInfo, TopicConfig,
    HealthStatus, ServiceStatus
)
from ..shared.config import Config
from .cluster_manager import ClusterManager, ConsumerGroupManager

logger = structlog.get_logger()


class CoordinatorService:
    """Main coordinator service."""
    
    def __init__(self):
        self.cluster_manager = ClusterManager()
        self.consumer_group_manager = ConsumerGroupManager(self.cluster_manager)
        self.startup_time = datetime.utcnow()
    
    async def startup(self):
        """Service startup."""
        logger.info("Starting coordinator service")
        await self.cluster_manager.start()
        await self.consumer_group_manager.start()
    
    async def shutdown(self):
        """Service shutdown."""
        logger.info("Shutting down coordinator service")
        await self.cluster_manager.stop()
        await self.consumer_group_manager.stop()


# Global service instance
coordinator_service = CoordinatorService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await coordinator_service.startup()
    yield
    await coordinator_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Message Queue Coordinator Service",
    description="Cluster coordination and service discovery",
    version="1.0.0",
    lifespan=lifespan
)


# Broker management endpoints
@app.post("/brokers/register", response_model=dict)
async def register_broker(broker_info: BrokerInfo):
    """Register a new broker."""
    try:
        success = await coordinator_service.cluster_manager.register_broker(broker_info)
        if success:
            return {"status": "registered", "broker_id": broker_info.broker_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to register broker")
    
    except Exception as e:
        logger.error("Failed to register broker", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/brokers/{broker_id}", response_model=dict)
async def unregister_broker(broker_id: str):
    """Unregister a broker."""
    try:
        success = await coordinator_service.cluster_manager.unregister_broker(broker_id)
        if success:
            return {"status": "unregistered", "broker_id": broker_id}
        else:
            raise HTTPException(status_code=404, detail="Broker not found")
    
    except Exception as e:
        logger.error("Failed to unregister broker", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brokers/{broker_id}/heartbeat", response_model=dict)
async def broker_heartbeat(broker_id: str, heartbeat_data: dict):
    """Update broker heartbeat."""
    try:
        success = await coordinator_service.cluster_manager.update_broker_heartbeat(broker_id)
        if success:
            return {"status": "received", "timestamp": datetime.utcnow().isoformat()}
        else:
            raise HTTPException(status_code=404, detail="Broker not found")
    
    except Exception as e:
        logger.error("Failed to update broker heartbeat", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/brokers", response_model=dict)
async def list_brokers():
    """List all registered brokers."""
    try:
        brokers = coordinator_service.cluster_manager.get_brokers()
        return {
            "brokers": [
                {
                    "broker_id": broker.broker_id,
                    "host": broker.host,
                    "port": broker.port,
                    "status": broker.status.value,
                    "last_heartbeat": broker.last_heartbeat.isoformat()
                }
                for broker in brokers
            ]
        }
    
    except Exception as e:
        logger.error("Failed to list brokers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Partition management endpoints
@app.post("/topics/{topic}/partitions", response_model=dict)
async def create_topic_partitions(topic: str, config: dict):
    """Create partitions for a topic."""
    try:
        partition_count = config.get("partitions", 3)
        replication_factor = config.get("replication_factor", 3)
        
        success = await coordinator_service.cluster_manager.create_topic_partitions(
            topic, partition_count, replication_factor
        )
        
        if success:
            return {
                "status": "created",
                "topic": topic,
                "partitions": partition_count,
                "replication_factor": replication_factor
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to create topic partitions"
            )
    
    except Exception as e:
        logger.error("Failed to create topic partitions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/partitions", response_model=dict)
async def list_partitions():
    """List all partition assignments."""
    try:
        partitions = coordinator_service.cluster_manager.get_partitions()
        return {
            "partitions": [
                {
                    "topic": partition.topic,
                    "partition": partition.partition,
                    "leader": partition.leader,
                    "replicas": partition.replicas,
                    "in_sync_replicas": partition.in_sync_replicas
                }
                for partition in partitions
            ]
        }
    
    except Exception as e:
        logger.error("Failed to list partitions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics/{topic}/partitions", response_model=dict)
async def get_topic_partitions(topic: str):
    """Get partitions for a specific topic."""
    try:
        partitions = coordinator_service.cluster_manager.get_topic_partitions(topic)
        return {
            "topic": topic,
            "partitions": [
                {
                    "partition": partition.partition,
                    "leader": partition.leader,
                    "replicas": partition.replicas,
                    "in_sync_replicas": partition.in_sync_replicas
                }
                for partition in partitions
            ]
        }
    
    except Exception as e:
        logger.error("Failed to get topic partitions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Leader election endpoint
@app.post("/leader-election", response_model=dict)
async def elect_leader(election_request: dict):
    """Elect a new leader for a partition."""
    try:
        topic = election_request["topic"]
        partition = election_request["partition"]
        candidate_broker = election_request.get("candidate_broker")
        
        new_leader = await coordinator_service.cluster_manager.elect_leader(
            topic, partition, candidate_broker
        )
        
        if new_leader:
            return {
                "status": "elected",
                "topic": topic,
                "partition": partition,
                "leader": new_leader
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to elect leader"
            )
    
    except Exception as e:
        logger.error("Failed to elect leader", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Consumer group management endpoints
@app.post("/consumer-groups/{group_id}/join", response_model=dict)
async def join_consumer_group(group_id: str, request: dict):
    """Join a consumer group."""
    try:
        consumer_id = request["consumer_id"]
        success = await coordinator_service.consumer_group_manager.join_group(
            group_id, consumer_id
        )
        
        if success:
            return {"status": "joined", "group_id": group_id, "consumer_id": consumer_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to join group")
    
    except Exception as e:
        logger.error("Failed to join consumer group", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/consumer-groups/{group_id}/members/{consumer_id}", response_model=dict)
async def leave_consumer_group(group_id: str, consumer_id: str):
    """Leave a consumer group."""
    try:
        success = await coordinator_service.consumer_group_manager.leave_group(
            group_id, consumer_id
        )
        
        if success:
            return {"status": "left", "group_id": group_id, "consumer_id": consumer_id}
        else:
            raise HTTPException(status_code=404, detail="Consumer not found in group")
    
    except Exception as e:
        logger.error("Failed to leave consumer group", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/consumer-groups/{group_id}/heartbeat", response_model=dict)
async def consumer_heartbeat(group_id: str, request: dict):
    """Update consumer heartbeat."""
    try:
        consumer_id = request["consumer_id"]
        success = await coordinator_service.consumer_group_manager.update_consumer_heartbeat(
            consumer_id
        )
        
        if success:
            return {"status": "received", "timestamp": datetime.utcnow().isoformat()}
        else:
            raise HTTPException(status_code=404, detail="Consumer not found")
    
    except Exception as e:
        logger.error("Failed to update consumer heartbeat", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/consumer-groups/{group_id}/assignment", response_model=dict)
async def get_group_assignment(group_id: str):
    """Get partition assignment for a consumer group."""
    try:
        assignment = coordinator_service.consumer_group_manager.get_group_assignment(group_id)
        
        if assignment is not None:
            return {
                "group_id": group_id,
                "assignments": assignment
            }
        else:
            raise HTTPException(status_code=404, detail="Consumer group not found")
    
    except Exception as e:
        logger.error("Failed to get group assignment", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/consumer-groups", response_model=dict)
async def list_consumer_groups():
    """List all consumer groups."""
    try:
        groups = coordinator_service.consumer_group_manager.get_consumer_groups()
        return {
            "groups": [
                {
                    "group_id": group.group_id,
                    "members": group.members,
                    "assignments": group.assignments,
                    "state": group.state
                }
                for group in groups
            ]
        }
    
    except Exception as e:
        logger.error("Failed to list consumer groups", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    try:
        brokers = coordinator_service.cluster_manager.get_brokers()
        healthy_brokers = coordinator_service.cluster_manager.get_healthy_brokers()
        consumer_groups = coordinator_service.consumer_group_manager.get_consumer_groups()
        
        details = {
            "total_brokers": len(brokers),
            "healthy_brokers": len(healthy_brokers),
            "consumer_groups": len(consumer_groups),
            "uptime_seconds": (datetime.utcnow() - coordinator_service.startup_time).total_seconds()
        }
        
        return HealthStatus(
            service="coordinator",
            status=ServiceStatus.HEALTHY,
            details=details
        )
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthStatus(
            service="coordinator",
            status=ServiceStatus.UNHEALTHY,
            details={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.coordinator.server:app",
        host="0.0.0.0",
        port=Config.COORDINATOR_PORT,
        log_level=Config.LOG_LEVEL.lower()
    )