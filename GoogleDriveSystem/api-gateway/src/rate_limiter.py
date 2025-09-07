import redis
import time
import os
from typing import Optional

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
    print("Redis not available, rate limiting disabled")

class RateLimiter:
    def __init__(self):
        self.requests_per_minute = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '60'))
    
    async def is_rate_limited(self, identifier: str) -> bool:
        """Check if request should be rate limited"""
        if not redis_client:
            return False
        
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - 60  # 1 minute window
            
            # Remove old entries
            redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            request_count = redis_client.zcard(key)
            
            if request_count >= self.requests_per_minute:
                return True
            
            # Add current request
            redis_client.zadd(key, {str(current_time): current_time})
            redis_client.expire(key, 60)
            
            return False
        except:
            # If Redis fails, don't rate limit
            return False
    
    async def get_rate_limit_info(self, identifier: str) -> dict:
        """Get rate limit information"""
        if not redis_client:
            return {"requests_remaining": self.requests_per_minute, "window_reset": 60}
        
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - 60
            
            # Clean old entries
            redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            request_count = redis_client.zcard(key)
            requests_remaining = max(0, self.requests_per_minute - request_count)
            
            # Calculate window reset time
            oldest_request = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                window_reset = int(60 - (current_time - oldest_request[0][1]))
            else:
                window_reset = 60
            
            return {
                "requests_remaining": requests_remaining,
                "window_reset": max(0, window_reset),
                "total_requests": request_count
            }
        except:
            return {"requests_remaining": self.requests_per_minute, "window_reset": 60}

rate_limiter = RateLimiter()