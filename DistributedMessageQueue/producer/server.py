"""Producer service implementation."""
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import structlog

from ..shared.models import (
    ProduceRequest, ProduceResponse, HealthStatus, ServiceStatus,
    TopicConfig
)
from ..shared.config import Config
from ..shared.utils import make_http_request
from .batch_manager import BatchManager, RetryManager

logger = structlog.get_logger()


class ProducerService:
    """Main producer service."""
    
    def __init__(self):
        self.batch_manager = BatchManager(Config.get_broker_endpoints())
        self.retry_manager = RetryManager()
        self.startup_time = datetime.utcnow()
        self.message_count = 0
        self.error_count = 0
    
    async def startup(self):
        """Service startup."""
        logger.info("Starting producer service")
        await self.batch_manager.start()
        await self.retry_manager.start()
    
    async def shutdown(self):
        """Service shutdown."""
        logger.info("Shutting down producer service")
        await self.batch_manager.stop()
        await self.retry_manager.stop()


# Global service instance
producer_service = ProducerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await producer_service.startup()
    yield
    await producer_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Message Queue Producer Service",
    description="Message publishing service with batching and routing",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/produce", response_model=dict)
async def produce_message(request: ProduceRequest):
    """Produce a single message."""
    try:
        # Validate request
        if not request.topic or not request.value:
            raise HTTPException(status_code=400, detail="Topic and value are required")
        
        # Add message to batch
        result = await producer_service.batch_manager.add_message(request)
        
        producer_service.message_count += 1
        
        logger.info(
            "Message queued for production",
            topic=request.topic,
            key=request.key,
            partition=result.get("partition"),
            status=result.get("status")
        )
        
        return {
            "status": "accepted",
            "topic": request.topic,
            "partition": result.get("partition"),
            "message_id": producer_service.message_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        producer_service.error_count += 1
        logger.error("Failed to produce message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/produce/batch", response_model=dict)
async def produce_batch(requests: List[ProduceRequest]):
    """Produce multiple messages in batch."""
    try:
        if not requests:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        results = []
        for request in requests:
            try:
                result = await producer_service.batch_manager.add_message(request)
                results.append({
                    "topic": request.topic,
                    "key": request.key,
                    "status": result.get("status"),
                    "partition": result.get("partition")
                })
                producer_service.message_count += 1
            except Exception as e:
                producer_service.error_count += 1
                results.append({
                    "topic": request.topic,
                    "key": request.key,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(
            "Batch of messages queued",
            total_messages=len(requests),
            successful=len([r for r in results if r["status"] != "failed"]),
            failed=len([r for r in results if r["status"] == "failed"])
        )
        
        return {
            "status": "processed",
            "total_messages": len(requests),
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to produce batch", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/topics", response_model=dict)
async def create_topic(topic_config: TopicConfig):
    """Create a new topic (proxy to coordinator and brokers)."""
    try:
        # First, create topic partitions in coordinator
        coordinator_endpoint = Config.get_coordinator_endpoint()
        partitions_url = f"{coordinator_endpoint}/topics/{topic_config.name}/partitions"
        
        partition_config = {
            "partitions": topic_config.partitions,
            "replication_factor": topic_config.replication_factor
        }
        
        coordinator_response = await make_http_request("POST", partitions_url, partition_config)
        
        if not coordinator_response:
            raise HTTPException(status_code=500, detail="Failed to create topic in coordinator")
        
        # Then, create topic in brokers
        broker_endpoints = Config.get_broker_endpoints()
        topic_data = {
            "name": topic_config.name,
            "partitions": topic_config.partitions,
            "replication_factor": topic_config.replication_factor,
            "retention_ms": topic_config.retention_ms,
            "max_segment_size": topic_config.max_segment_size
        }
        
        broker_responses = []
        for endpoint in broker_endpoints:
            try:
                url = f"{endpoint}/topics"
                response = await make_http_request("POST", url, topic_data)
                if response:
                    broker_responses.append(response)
            except Exception as e:
                logger.warning("Failed to create topic on broker", endpoint=endpoint, error=str(e))
        
        if not broker_responses:
            raise HTTPException(status_code=500, detail="Failed to create topic on any broker")
        
        logger.info("Topic created successfully", topic=topic_config.name)
        
        return {
            "status": "created",
            "topic": topic_config.name,
            "coordinator_response": coordinator_response,
            "broker_responses": len(broker_responses)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create topic", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics", response_model=dict)
async def list_topics():
    """List all topics (proxy to broker)."""
    try:
        # Query first available broker
        broker_endpoints = Config.get_broker_endpoints()
        
        for endpoint in broker_endpoints:
            try:
                url = f"{endpoint}/topics"
                response = await make_http_request("GET", url)
                if response:
                    return response
            except Exception as e:
                logger.warning("Failed to get topics from broker", endpoint=endpoint, error=str(e))
                continue
        
        raise HTTPException(status_code=503, detail="No brokers available")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list topics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=dict)
async def get_status():
    """Get producer service status and metrics."""
    try:
        uptime_seconds = (datetime.utcnow() - producer_service.startup_time).total_seconds()
        
        # Get batch statistics
        batch_stats = {
            "active_batches": len(producer_service.batch_manager.batches),
            "topic_partitions_cached": len(producer_service.batch_manager.topic_partitions)
        }
        
        # Get retry statistics  
        retry_stats = {
            "retry_queues": len(producer_service.retry_manager.retry_queues),
            "total_retries": sum(
                len(messages) for messages in producer_service.retry_manager.retry_queues.values()
            )
        }
        
        return {
            "service": "producer",
            "status": "healthy",
            "uptime_seconds": uptime_seconds,
            "metrics": {
                "total_messages": producer_service.message_count,
                "total_errors": producer_service.error_count,
                "error_rate": producer_service.error_count / max(producer_service.message_count, 1),
                "batch_stats": batch_stats,
                "retry_stats": retry_stats
            },
            "config": {
                "batch_size": Config.BATCH_SIZE,
                "batch_timeout_ms": Config.BATCH_TIMEOUT_MS,
                "retry_attempts": Config.RETRY_ATTEMPTS,
                "broker_endpoints": Config.BROKER_HOSTS
            }
        }
    
    except Exception as e:
        logger.error("Failed to get status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flush", response_model=dict)
async def flush_batches():
    """Force flush all pending batches."""
    try:
        await producer_service.batch_manager._flush_all_batches()
        
        logger.info("All batches flushed")
        
        return {
            "status": "flushed",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Failed to flush batches", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    try:
        # Check connectivity to brokers
        healthy_brokers = 0
        broker_endpoints = Config.get_broker_endpoints()
        
        for endpoint in broker_endpoints:
            try:
                url = f"{endpoint}/health"
                response = await make_http_request("GET", url, timeout=5)
                if response and response.get("status") == "healthy":
                    healthy_brokers += 1
            except:
                pass
        
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
            "total_messages": producer_service.message_count,
            "error_count": producer_service.error_count,
            "active_batches": len(producer_service.batch_manager.batches),
            "healthy_brokers": healthy_brokers,
            "total_brokers": len(broker_endpoints),
            "coordinator_healthy": coordinator_healthy,
            "uptime_seconds": (datetime.utcnow() - producer_service.startup_time).total_seconds()
        }
        
        # Determine overall health
        if healthy_brokers == 0 or not coordinator_healthy:
            status = ServiceStatus.UNHEALTHY
        elif healthy_brokers < len(broker_endpoints):
            status = ServiceStatus.UNHEALTHY  # Could be degraded in a more sophisticated system
        else:
            status = ServiceStatus.HEALTHY
        
        return HealthStatus(
            service="producer",
            status=status,
            details=details
        )
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthStatus(
            service="producer",
            status=ServiceStatus.UNHEALTHY,
            details={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.producer.server:app",
        host="0.0.0.0",
        port=Config.PRODUCER_PORT,
        log_level=Config.LOG_LEVEL.lower()
    )