import redis
import json
import os
from typing import Optional, Any

redis_client = None

try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        decode_responses=True
    )
    redis_client.ping()
except:
    redis_client = None
    print("Redis not available, caching disabled")

def cache_get(key: str) -> Optional[Any]:
    if not redis_client:
        return None
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except:
        return None

def cache_set(key: str, value: Any, expire: int = 300):
    if not redis_client:
        return
    try:
        redis_client.setex(key, expire, json.dumps(value, default=str))
    except:
        pass

def cache_delete(key: str):
    if not redis_client:
        return
    try:
        redis_client.delete(key)
    except:
        pass

def cache_invalidate_pattern(pattern: str):
    if not redis_client:
        return
    try:
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)
    except:
        pass