"""
Analytics Aggregator Service - Search Autocomplete System
Processes Kafka streams to aggregate query frequencies and build trie structures
Modified for local testing
"""

import json
import time
import re
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter

import asyncpg
from kafka import KafkaConsumer, KafkaProducer
from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import logging

# Configuration - use environment variables for local testing
KAFKA_BROKERS = [os.getenv("KAFKA_BROKERS", "localhost:9092")]
KAFKA_TOPIC = "search-queries"
KAFKA_GROUP_ID = "analytics-consumer"
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "autocomplete_test")
DB_USER = os.getenv("DB_USER", "testuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "testpass")

AGGREGATION_WINDOW_HOURS = 1  # Process data every hour
MIN_FREQUENCY_THRESHOLD = 5   # Minimum frequency to include in trie
MAX_SUGGESTIONS_PER_PREFIX = 5
WEEKLY_REBUILD_ENABLED = True

# Global state
consumer = None
db_pool = None
aggregation_buffer = defaultdict(int)
last_aggregation_time = None
is_processing = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Analytics Aggregator Service",
    description="Query Analytics Processing and Trie Building Service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrieNode:
    """Simple trie node for building trie structure"""
    def __init__(self):
        self.children = {}
        self.suggestions = []
        self.is_end = False

class TrieBuilder:
    """Build and manage trie data structure"""
    
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, query: str, frequency: int):
        """Insert a query with frequency into trie"""
        node = self.root
        
        # Build path for each prefix
        for i in range(len(query)):
            prefix = query[:i+1]
            
            if prefix not in node.children:
                node.children[prefix] = TrieNode()
            
            node = node.children[prefix]
            
            # Add suggestion to this prefix node
            suggestion = {"query": query, "frequency": frequency}
            node.suggestions.append(suggestion)
            
            # Keep only top suggestions, sorted by frequency
            node.suggestions.sort(key=lambda x: x["frequency"], reverse=True)
            node.suggestions = node.suggestions[:MAX_SUGGESTIONS_PER_PREFIX]
    
    def get_prefix_suggestions(self, prefix: str) -> List[Dict]:
        """Get suggestions for a prefix"""
        node = self.root
        
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        
        return node.suggestions

async def initialize_database():
    """Initialize database connection pool"""
    global db_pool
    
    try:
        db_pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=2,
            max_size=10,
            command_timeout=30
        )
        logger.info(f"✅ Connected to Database at {DB_HOST}:{DB_PORT}")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise

def initialize_kafka_consumer():
    """Initialize Kafka consumer"""
    global consumer
    
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BROKERS,
            group_id=KAFKA_GROUP_ID,
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=5000,  # 5 second timeout
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000
        )
        logger.info(f"✅ Connected to Kafka at {KAFKA_BROKERS}")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to Kafka: {e}")
        raise

def validate_query(query: str) -> bool:
    """Validate query format"""
    if not query or len(query) > 200:
        return False
    
    # Only lowercase alphabetic and spaces
    return bool(re.match(r'^[a-z ]+$', query.strip()))

async def consume_kafka_messages():
    """Consume messages from Kafka and aggregate"""
    global aggregation_buffer, last_aggregation_time
    
    if not consumer:
        return
    
    try:
        # Poll for messages
        message_batch = consumer.poll(timeout_ms=1000)
        
        processed_count = 0
        for topic_partition, messages in message_batch.items():
            for message in messages:
                try:
                    query_data = message.value
                    query = query_data.get('query', '').strip().lower()
                    
                    if validate_query(query):
                        aggregation_buffer[query] += 1
                        processed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        if processed_count > 0:
            logger.info(f"Processed {processed_count} messages")
        
        # For testing, aggregate more frequently (every 30 seconds instead of 1 hour)
        now = datetime.now(timezone.utc)
        if (last_aggregation_time is None or 
            now - last_aggregation_time > timedelta(seconds=30)):
            
            if aggregation_buffer:
                await aggregate_and_update_trie()
                last_aggregation_time = now
                
    except Exception as e:
        logger.error(f"Error in Kafka consumer: {e}")

async def aggregate_and_update_trie():
    """Aggregate buffered data and update trie"""
    global aggregation_buffer, is_processing
    
    if is_processing or not aggregation_buffer:
        return
    
    is_processing = True
    start_time = time.time()
    
    try:
        logger.info(f"Starting aggregation of {len(aggregation_buffer)} unique queries")
        
        # Get current week start
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with db_pool.acquire() as conn:
            # Update query frequencies
            for query, count in aggregation_buffer.items():
                await conn.execute("""
                    INSERT INTO query_frequencies (query, frequency, week_start)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (query, week_start)
                    DO UPDATE SET frequency = query_frequencies.frequency + $2
                """, query, count, week_start.date())
            
            # Build trie from current data
            await build_and_store_trie(conn, week_start)
        
        # Clear buffer
        processed_queries = len(aggregation_buffer)
        aggregation_buffer.clear()
        
        duration = time.time() - start_time
        logger.info(f"✅ Aggregated {processed_queries} queries in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"❌ Error in aggregation: {e}")
        
    finally:
        is_processing = False

async def build_and_store_trie(conn, week_start):
    """Build trie from query frequencies and store in database"""
    
    try:
        logger.info("Building trie structure...")
        
        # Get all queries above threshold
        rows = await conn.fetch("""
            SELECT query, SUM(frequency) as total_frequency
            FROM query_frequencies
            WHERE week_start >= $1::date - INTERVAL '4 weeks'
            GROUP BY query
            HAVING SUM(frequency) >= $2
            ORDER BY total_frequency DESC
        """, week_start.date(), MIN_FREQUENCY_THRESHOLD)
        
        if not rows:
            logger.warning("No queries found above threshold")
            return
        
        # Build trie
        trie = TrieBuilder()
        for row in rows:
            query = row['query']
            frequency = row['total_frequency']
            trie.insert(query, frequency)
        
        logger.info(f"Built trie with {len(rows)} queries")
        
        # Generate all prefixes and store trie data
        prefixes_stored = 0
        version = int(time.time())  # Use timestamp as version
        
        # Clear old trie data first
        await conn.execute("DELETE FROM trie_data WHERE version < $1", version - 3600)
        
        # Store trie data for each prefix length
        for row in rows:
            query = row['query']
            
            # Generate prefixes for this query
            for i in range(1, min(len(query) + 1, 21)):  # Up to 20 char prefixes
                prefix = query[:i]
                suggestions = trie.get_prefix_suggestions(prefix)
                
                if suggestions:
                    await conn.execute("""
                        INSERT INTO trie_data (prefix, suggestions, version)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (prefix, version) DO NOTHING
                    """, prefix, json.dumps(suggestions), version)
                    
                    prefixes_stored += 1
        
        logger.info(f"✅ Stored {prefixes_stored} trie entries with version {version}")
        
    except Exception as e:
        logger.error(f"❌ Error building trie: {e}")

async def get_aggregation_stats():
    """Get current aggregation statistics"""
    global db_pool
    
    try:
        async with db_pool.acquire() as conn:
            # Get total unique queries
            total_queries = await conn.fetchval(
                "SELECT COUNT(DISTINCT query) FROM query_frequencies"
            )
            
            # Get recent activity
            recent_queries = await conn.fetchval("""
                SELECT COUNT(*) FROM query_frequencies 
                WHERE week_start >= NOW() - INTERVAL '1 week'
            """)
            
            # Get latest trie version
            latest_version = await conn.fetchval(
                "SELECT MAX(version) FROM trie_data"
            ) or 0
            
            # Get trie entries count
            trie_entries = await conn.fetchval(
                "SELECT COUNT(*) FROM trie_data WHERE version = $1", latest_version
            ) or 0
            
            return {
                "total_unique_queries": total_queries or 0,
                "recent_queries": recent_queries or 0,
                "latest_trie_version": latest_version,
                "trie_entries": trie_entries,
                "buffer_size": len(aggregation_buffer),
                "is_processing": is_processing
            }
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "error": str(e),
            "buffer_size": len(aggregation_buffer),
            "is_processing": is_processing
        }

# Background task to process Kafka messages
async def kafka_processing_loop():
    """Background loop to process Kafka messages"""
    global last_aggregation_time
    
    last_aggregation_time = datetime.now(timezone.utc)
    
    while True:
        try:
            await consume_kafka_messages()
            await asyncio.sleep(5)  # Process every 5 seconds
            
        except Exception as e:
            logger.error(f"Error in Kafka processing loop: {e}")
            await asyncio.sleep(10)

# API Endpoints

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    await initialize_database()
    initialize_kafka_consumer()
    
    # Start background processing
    asyncio.create_task(kafka_processing_loop())
    logger.info("🚀 Analytics Aggregator Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global consumer, db_pool
    
    if consumer:
        consumer.close()
    
    if db_pool:
        await db_pool.close()
    
    logger.info("👋 Analytics Aggregator Service stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Check Kafka consumer
        kafka_healthy = consumer is not None
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "database": "connected",
                "kafka": "connected" if kafka_healthy else "disconnected",
            },
            "processing": {
                "buffer_size": len(aggregation_buffer),
                "is_processing": is_processing,
                "last_aggregation": last_aggregation_time.isoformat() if last_aggregation_time else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get aggregation statistics"""
    return await get_aggregation_stats()

@app.post("/force-aggregation")
async def force_aggregation(background_tasks: BackgroundTasks):
    """Force immediate aggregation (for testing/admin)"""
    if is_processing:
        return {"status": "already_processing"}
    
    background_tasks.add_task(aggregate_and_update_trie)
    
    return {
        "status": "aggregation_started",
        "buffer_size": len(aggregation_buffer)
    }

@app.get("/buffer-status")
async def get_buffer_status():
    """Get current buffer status"""
    return {
        "buffer_size": len(aggregation_buffer),
        "is_processing": is_processing,
        "top_queries": dict(Counter(aggregation_buffer).most_common(10)) if aggregation_buffer else {}
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics"""
    try:
        stats = await get_aggregation_stats()
        
        metrics_text = f"""# HELP analytics_aggregator_buffer_size Current buffer size
# TYPE analytics_aggregator_buffer_size gauge
analytics_aggregator_buffer_size {stats.get('buffer_size', 0)}

# HELP analytics_aggregator_total_queries Total unique queries processed
# TYPE analytics_aggregator_total_queries counter  
analytics_aggregator_total_queries {stats.get('total_unique_queries', 0)}

# HELP analytics_aggregator_trie_entries Current trie entries
# TYPE analytics_aggregator_trie_entries gauge
analytics_aggregator_trie_entries {stats.get('trie_entries', 0)}

# HELP analytics_aggregator_is_processing Currently processing flag
# TYPE analytics_aggregator_is_processing gauge
analytics_aggregator_is_processing {1 if stats.get('is_processing', False) else 0}
"""
        
        return Response(content=metrics_text, media_type="text/plain")
        
    except Exception as e:
        return Response(content=f"# Error collecting metrics: {e}", media_type="text/plain")

if __name__ == "__main__":
    print(f"Starting Analytics Aggregator Service...")
    print(f"Kafka: {KAFKA_BROKERS}")
    print(f"Database: {DB_HOST}:{DB_PORT}")
    uvicorn.run(
        "main_test:app",
        host="0.0.0.0",
        port=16742,
        reload=False,
        access_log=True
    )