"""
Query Service - Search Autocomplete System (Docker Version)
Fast autocomplete suggestions with Redis caching and PostgreSQL fallback
"""

import asyncio
import json
import time
import re
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configuration - Docker hostnames
REDIS_HOST = os.getenv("REDIS_HOST", "autocomplete-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DB_HOST = os.getenv("DB_HOST", "autocomplete-postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "autocomplete_test")
DB_USER = os.getenv("DB_USER", "testuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "testpass")

CACHE_TTL = 3600  # 1 hour
MAX_SUGGESTIONS = 5

# Global connections
redis_client = None
db_pool = None

app = FastAPI(
    title="Query Service",
    description="Fast Autocomplete Suggestions Service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def initialize_redis():
    """Initialize Redis connection"""
    global redis_client
    
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=5
        )
        await redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        raise

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
        print(f"✅ Connected to Database at {DB_HOST}:{DB_PORT}")
        
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        raise

def validate_query(query: str) -> bool:
    """Validate query format"""
    if not query or len(query) > 50:
        return False
    return bool(re.match(r'^[a-z ]+$', query.strip()))

async def get_suggestions_from_cache(query: str) -> tuple[List[Dict], bool]:
    """Get suggestions from Redis cache"""
    try:
        cache_key = f"autocomplete:{query}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            suggestions = json.loads(cached_data)
            return suggestions, True
        
        return [], False
        
    except Exception as e:
        print(f"Cache error for query '{query}': {e}")
        return [], False

async def get_suggestions_from_db(query: str) -> List[Dict]:
    """Get suggestions from database"""
    try:
        async with db_pool.acquire() as conn:
            # Try trie_data table first
            row = await conn.fetchrow("""
                SELECT suggestions 
                FROM trie_data 
                WHERE prefix = $1 
                ORDER BY version DESC 
                LIMIT 1
            """, query)
            
            if row and row['suggestions']:
                suggestions = row['suggestions']
                if isinstance(suggestions, str):
                    suggestions = json.loads(suggestions)
                return suggestions
            
            # Fallback to frequency table
            rows = await conn.fetch("""
                SELECT query, frequency
                FROM query_frequencies 
                WHERE query LIKE $1
                ORDER BY frequency DESC 
                LIMIT $2
            """, f"{query}%", MAX_SUGGESTIONS)
            
            suggestions = []
            for row in rows:
                suggestions.append({
                    "query": row['query'],
                    "frequency": row['frequency']
                })
            
            return suggestions
            
    except Exception as e:
        print(f"Database error for query '{query}': {e}")
        return []

async def cache_suggestions(query: str, suggestions: List[Dict]):
    """Cache suggestions in Redis"""
    try:
        cache_key = f"autocomplete:{query}"
        cached_data = json.dumps(suggestions)
        await redis_client.setex(cache_key, CACHE_TTL, cached_data)
        
    except Exception as e:
        print(f"Cache write error for query '{query}': {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    await initialize_redis()
    await initialize_database()
    print("🚀 Query Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global redis_client, db_pool
    
    if redis_client:
        await redis_client.close()
    
    if db_pool:
        await db_pool.close()
    
    print("👋 Query Service stopped")

@app.get("/autocomplete")
async def get_autocomplete_suggestions(q: str):
    """Get autocomplete suggestions for a query"""
    start_time = time.time()
    
    # Validate query
    query = q.strip().lower()
    if not validate_query(query):
        raise HTTPException(status_code=400, detail="Invalid query format")
    
    try:
        # Try cache first
        suggestions, cache_hit = await get_suggestions_from_cache(query)
        
        # Fallback to database
        if not cache_hit:
            suggestions = await get_suggestions_from_db(query)
            
            # Cache the results
            if suggestions:
                asyncio.create_task(cache_suggestions(query, suggestions))
        
        # Limit results
        suggestions = suggestions[:MAX_SUGGESTIONS]
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Create response with headers
        response_data = {
            "suggestions": suggestions,
            "latency_ms": round(latency_ms, 2)
        }
        
        # Add cache headers
        response = Response(
            content=json.dumps(response_data),
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Cache": "HIT" if cache_hit else "MISS",
                "X-Response-Time": f"{latency_ms:.2f}ms"
            }
        )
        
        return response
        
    except Exception as e:
        print(f"Error processing query '{query}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis
        await redis_client.ping()
        
        # Check Database
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "redis": "connected",
                "database": "connected"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics"""
    try:
        # Get database stats
        async with db_pool.acquire() as conn:
            total_queries = await conn.fetchval("SELECT COUNT(*) FROM query_frequencies") or 0
            trie_entries = await conn.fetchval("SELECT COUNT(*) FROM trie_data") or 0
        
        metrics_text = f"""# HELP query_service_total_queries Total queries in database
# TYPE query_service_total_queries counter
query_service_total_queries {total_queries}

# HELP query_service_trie_entries Total trie entries
# TYPE query_service_trie_entries gauge
query_service_trie_entries {trie_entries}
"""
        
        return Response(content=metrics_text, media_type="text/plain")
        
    except Exception as e:
        return Response(content=f"# Error collecting metrics: {e}", media_type="text/plain")

if __name__ == "__main__":
    print("Starting Query Service for Docker...")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"Database: {DB_HOST}:{DB_PORT}")
    uvicorn.run(
        "main_docker:app",
        host="0.0.0.0",
        port=17893,
        reload=False,
        access_log=True
    )