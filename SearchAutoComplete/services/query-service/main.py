"""
Query Service - Search Autocomplete System
Serves autocomplete suggestions with <100ms response time
"""

import asyncio
import json
import re
import time
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

import redis.asyncio as redis
import asyncpg
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configuration
REDIS_HOST = "redis-cache"
REDIS_PORT = 6379
DB_HOST = "postgres" 
DB_PORT = 5432
DB_NAME = "autocomplete_test"
DB_USER = "testuser"
DB_PASSWORD = "testpass"

MAX_PREFIX_LENGTH = 50
SUGGESTIONS_COUNT = 5
CACHE_TTL = 3600  # 1 hour

# Data Models
class Suggestion(BaseModel):
    query: str
    score: int

class AutocompleteResponse(BaseModel):
    suggestions: List[Suggestion]
    latency_ms: float

# Global connections
redis_client = None
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global redis_client, db_pool
    
    # Startup
    try:
        # Redis connection
        redis_client = redis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        await redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        
        # Database connection pool
        db_pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=2,
            max_size=10,
            command_timeout=5
        )
        print(f"✅ Connected to Database at {DB_HOST}:{DB_PORT}")
        
    except Exception as e:
        print(f"❌ Failed to connect to services: {e}")
        raise
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()
    if db_pool:
        await db_pool.close()

app = FastAPI(
    title="Query Service",
    description="Search Autocomplete Query Service",
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

# Input validation
def validate_query_prefix(prefix: str) -> str:
    """Validate query prefix according to system rules"""
    if not prefix:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if len(prefix) > MAX_PREFIX_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail=f"Query too long. Maximum length is {MAX_PREFIX_LENGTH} characters"
        )
    
    if not re.match(r'^[a-z ]+$', prefix):
        raise HTTPException(
            status_code=400,
            detail="Only lowercase alphabetic characters and spaces allowed"
        )
    
    return prefix.strip()

async def get_suggestions_from_cache(prefix: str) -> Optional[List[Dict]]:
    """Get suggestions from Redis cache"""
    try:
        cache_key = f"trie:prefix:{prefix}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            data = json.loads(cached_data)
            return data.get("suggestions", [])
            
    except Exception as e:
        print(f"Cache lookup error for '{prefix}': {e}")
    
    return None

async def get_suggestions_from_db(prefix: str) -> List[Dict]:
    """Get suggestions from database as fallback"""
    try:
        async with db_pool.acquire() as conn:
            # Query trie_data table for prefix
            query = """
                SELECT suggestions 
                FROM trie_data 
                WHERE prefix = $1 
                ORDER BY version DESC 
                LIMIT 1
            """
            
            row = await conn.fetchrow(query, prefix)
            
            if row and row['suggestions']:
                # PostgreSQL JSONB is already parsed
                suggestions = row['suggestions']
                print(f"DEBUG: Type of suggestions: {type(suggestions)}, Value: {suggestions[:100] if isinstance(suggestions, (str, list)) else suggestions}")
                if isinstance(suggestions, str):
                    suggestions = json.loads(suggestions)
                return suggestions
            
            # Fallback: direct query frequency lookup
            fallback_query = """
                SELECT query, frequency as score
                FROM query_frequencies 
                WHERE query LIKE $1
                ORDER BY frequency DESC 
                LIMIT $2
            """
            
            rows = await conn.fetch(fallback_query, f"{prefix}%", SUGGESTIONS_COUNT)
            return [{"query": row['query'], "score": row['score']} for row in rows]
            
    except Exception as e:
        print(f"Database lookup error for '{prefix}': {e}")
    
    return []

async def cache_suggestions(prefix: str, suggestions: List[Dict]):
    """Cache suggestions in Redis"""
    try:
        cache_key = f"trie:prefix:{prefix}"
        # Ensure suggestions is a list, not a JSON string
        if isinstance(suggestions, str):
            suggestions = json.loads(suggestions)
        
        cache_data = {
            "prefix": prefix,
            "suggestions": suggestions,
            "updated_at": time.time()
        }
        
        await redis_client.setex(
            cache_key, 
            CACHE_TTL, 
            json.dumps(cache_data)
        )
        
    except Exception as e:
        print(f"Cache write error for '{prefix}': {e}")

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

@app.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    q: str = Query(..., description="Query prefix to autocomplete", min_length=1, max_length=MAX_PREFIX_LENGTH)
):
    """Get autocomplete suggestions for a query prefix"""
    start_time = time.time()
    
    try:
        # Validate input
        prefix = validate_query_prefix(q)
        
        # Try cache first
        suggestions = await get_suggestions_from_cache(prefix)
        cache_hit = suggestions is not None
        
        # Fallback to database
        if suggestions is None:
            suggestions = await get_suggestions_from_db(prefix)
            
            # Cache the results for next time
            if suggestions:
                asyncio.create_task(cache_suggestions(prefix, suggestions))
        
        # Format response
        suggestion_objects = []
        for s in suggestions[:SUGGESTIONS_COUNT]:
            if isinstance(s, dict):
                query = s.get("query", "")
                # Handle both 'score' and 'frequency' field names
                score = s.get("score") or s.get("frequency") or 0
                suggestion_objects.append(Suggestion(query=query, score=int(score)))
            else:
                print(f"Invalid suggestion format: {s}")
        
        
        latency_ms = (time.time() - start_time) * 1000
        
        response = AutocompleteResponse(
            suggestions=suggestion_objects,
            latency_ms=round(latency_ms, 2)
        )
        
        # Add cache headers
        headers = {
            "Cache-Control": "public, max-age=3600",
            "X-Cache": "HIT" if cache_hit else "MISS",
            "X-Response-Time": f"{latency_ms:.2f}ms"
        }
        
        return JSONResponse(
            content=response.model_dump(),
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Autocomplete error for '{q}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    try:
        # Basic metrics (in production, use proper Prometheus client)
        async with db_pool.acquire() as conn:
            total_queries = await conn.fetchval("SELECT COUNT(*) FROM query_frequencies")
        
        cache_info = await redis_client.info("memory")
        used_memory = cache_info.get("used_memory", 0)
        
        metrics_text = f"""# HELP query_service_db_total_queries Total queries in database
# TYPE query_service_db_total_queries counter
query_service_db_total_queries {total_queries}

# HELP query_service_cache_memory_bytes Cache memory usage in bytes  
# TYPE query_service_cache_memory_bytes gauge
query_service_cache_memory_bytes {used_memory}
"""
        
        return Response(content=metrics_text, media_type="text/plain")
        
    except Exception as e:
        return Response(content=f"# Error collecting metrics: {e}", media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=17893,
        reload=False,
        access_log=True
    )