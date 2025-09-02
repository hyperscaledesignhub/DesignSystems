"""
Data Collection Service - Search Autocomplete System
Collects search queries in real-time and streams to analytics pipeline
Modified for local testing
"""

import asyncio
import json
import time
import random
import re
import os
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# Configuration - use environment variables or defaults for local testing
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
KAFKA_BROKERS = [os.getenv("KAFKA_BROKERS", "localhost:9092")]
KAFKA_TOPIC = "search-queries"
SAMPLING_RATE = 0.01  # 1% sampling
MAX_QUERY_LENGTH = 200
BATCH_SIZE = 100
BUFFER_TTL = 3600

# Data Models
class QueryLogRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    timestamp: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    client_ip_hash: Optional[str] = None

    @validator('query')
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        if not re.match(r'^[a-z ]+$', v):
            raise ValueError("Only lowercase alphabetic characters and spaces allowed")
        return v

    @validator('timestamp')
    def validate_timestamp(cls, v):
        if v is not None:
            try:
                # Validate ISO format timestamp
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Invalid timestamp format. Use ISO 8601 format")
        return v

class QueryLogResponse(BaseModel):
    status: str
    sampled: bool = False

# Global connections
redis_client = None
kafka_producer = None
query_buffer = []
buffer_lock = asyncio.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global redis_client, kafka_producer
    
    # Startup
    try:
        # Redis connection for buffering
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        await redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        
        # Kafka producer
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BROKERS,
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            compression_type="gzip"
        )
        await kafka_producer.start()
        print(f"✅ Connected to Kafka at {KAFKA_BROKERS}")
        
        # Start background buffer flush task
        asyncio.create_task(periodic_buffer_flush())
        
    except Exception as e:
        print(f"❌ Failed to connect to services: {e}")
        raise
    
    yield
    
    # Shutdown
    if kafka_producer:
        await kafka_producer.stop()
    if redis_client:
        await redis_client.close()

app = FastAPI(
    title="Data Collection Service",
    description="Search Query Collection and Streaming Service", 
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def should_sample() -> bool:
    """Determine if query should be sampled"""
    return random.random() < SAMPLING_RATE

async def add_to_buffer(query_data: dict):
    """Add query to local buffer"""
    global query_buffer
    
    async with buffer_lock:
        query_buffer.append(query_data)
        
        # Flush if buffer is full
        if len(query_buffer) >= BATCH_SIZE:
            await flush_buffer()

async def flush_buffer():
    """Flush query buffer to Kafka"""
    global query_buffer
    
    if not query_buffer:
        return
    
    try:
        # Send batch to Kafka
        for query_data in query_buffer:
            await kafka_producer.send(KAFKA_TOPIC, query_data)
        
        await kafka_producer.flush()
        print(f"✅ Flushed {len(query_buffer)} queries to Kafka")
        
        # Clear buffer
        query_buffer = []
        
    except Exception as e:
        print(f"❌ Failed to flush buffer to Kafka: {e}")
        
        # Fallback: store in Redis as backup
        try:
            backup_key = f"query_backup:{int(time.time())}"
            await redis_client.setex(
                backup_key,
                BUFFER_TTL,
                json.dumps(query_buffer)
            )
            query_buffer = []  # Clear buffer even if backup fails
            print(f"⚠️  Stored queries in Redis backup: {backup_key}")
            
        except Exception as redis_error:
            print(f"❌ Failed to backup to Redis: {redis_error}")
            query_buffer = []  # Clear buffer to prevent memory leak

async def periodic_buffer_flush():
    """Periodically flush buffer every 10 seconds"""
    while True:
        try:
            await asyncio.sleep(10)
            async with buffer_lock:
                if query_buffer:
                    await flush_buffer()
                    
        except Exception as e:
            print(f"❌ Error in periodic flush: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis
        await redis_client.ping()
        
        # Check Kafka (basic connectivity)
        # Kafka producer health is implicit if it started successfully
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "redis": "connected",
                "kafka": "connected",
                "buffer_size": len(query_buffer)
            },
            "sampling_rate": SAMPLING_RATE
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/log-query", response_model=QueryLogResponse)
async def log_query(
    request: QueryLogRequest,
    background_tasks: BackgroundTasks
):
    """Log a search query for analytics processing"""
    
    try:
        # Prepare query data
        timestamp = request.timestamp or datetime.now(timezone.utc).isoformat()
        
        query_data = {
            "query": request.query,
            "timestamp": timestamp,
            "user_id": request.user_id or "anonymous",
            "session_id": request.session_id,
            "client_ip_hash": request.client_ip_hash,
            "service_timestamp": time.time()
        }
        
        # Apply sampling
        sampled = await should_sample()
        
        if sampled:
            # Add to buffer for processing
            background_tasks.add_task(add_to_buffer, query_data)
        
        # Always return accepted (fire-and-forget pattern)
        return QueryLogResponse(
            status="accepted",
            sampled=sampled
        )
        
    except Exception as e:
        print(f"❌ Error logging query '{request.query}': {e}")
        # Still return accepted to maintain fire-and-forget behavior
        return QueryLogResponse(status="accepted", sampled=False)

@app.get("/buffer-status")
async def buffer_status():
    """Get current buffer status (for debugging)"""
    return {
        "buffer_size": len(query_buffer),
        "sampling_rate": SAMPLING_RATE,
        "max_buffer_size": BATCH_SIZE
    }

@app.post("/flush-buffer")
async def manual_flush_buffer():
    """Manually flush buffer (for debugging/admin)"""
    async with buffer_lock:
        buffer_size = len(query_buffer)
        await flush_buffer()
        
    return {
        "status": "flushed",
        "queries_sent": buffer_size
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics"""
    try:
        # Get Redis backup count
        backup_keys = await redis_client.keys("query_backup:*")
        backup_count = len(backup_keys) if backup_keys else 0
        
        metrics_text = f"""# HELP data_collection_buffer_size Current buffer size
# TYPE data_collection_buffer_size gauge
data_collection_buffer_size {len(query_buffer)}

# HELP data_collection_sampling_rate Query sampling rate
# TYPE data_collection_sampling_rate gauge
data_collection_sampling_rate {SAMPLING_RATE}

# HELP data_collection_redis_backups Number of Redis backup entries
# TYPE data_collection_redis_backups gauge
data_collection_redis_backups {backup_count}
"""
        
        return Response(content=metrics_text, media_type="text/plain")
        
    except Exception as e:
        return Response(content=f"# Error collecting metrics: {e}", media_type="text/plain")

if __name__ == "__main__":
    print(f"Starting Data Collection Service...")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"Kafka: {KAFKA_BROKERS}")
    uvicorn.run(
        "main_test:app",
        host="0.0.0.0", 
        port=18761,
        reload=False,
        access_log=True
    )