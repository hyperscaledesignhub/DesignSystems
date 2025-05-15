import time
import threading
import logging
from typing import Tuple, List, Optional
import redis
from .metrics import RateLimiterMetrics

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlidingWindowLogRateLimiter:
    """
    A distributed rate limiter using the sliding window log algorithm.
    This maintains a log of all request timestamps and counts requests within the window.
    """
    
    def __init__(self, max_requests: int, window_size_ms: int, redis_client: Optional[redis.Redis] = None, precision=1000, overlap_factor=0.6):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_size_ms: Size of the time window in milliseconds
            redis_client: Redis client instance (optional)
            precision: Precision for the sliding window
            overlap_factor: Overlap factor for the sliding window
        """
        self.max_requests = max_requests
        self.window_size_ms = window_size_ms
        self.redis = redis_client or self._create_in_memory_redis()
        logger.info(f"Using {'Redis' if isinstance(self.redis, redis.Redis) else 'in-memory'} storage")
        
        self.precision = precision
        self.overlap_factor = overlap_factor
        
        # Initialize metrics
        self.metrics = RateLimiterMetrics()
        self.metrics.window_size.labels(algorithm='sliding_window_log').set(window_size_ms / 1000.0)
        self.metrics.window_overlap.labels(algorithm='sliding_window_log').set(overlap_factor)
        
        # The metrics are already defined in the RateLimiterMetrics class
        # We don't need to create them again here
        
        self.script = self._get_lua_script()
        self.script_sha = self.redis.script_load(self.script)
    
    def _create_in_memory_redis(self) -> redis.Redis:
        """Create an in-memory Redis mock for testing."""
        logger.info("Creating in-memory Redis mock")
        class InMemoryRedis:
            def __init__(self):
                self.data = {}
                self.scripts = {}
                self.lock = threading.Lock()
            
            def script_load(self, script: str) -> str:
                script_hash = str(hash(script))
                self.scripts[script_hash] = script
                return script_hash
            
            def evalsha(self, script_hash: str, numkeys: int, *args) -> List[int]:
                if script_hash not in self.scripts:
                    raise redis.ResponseError("NOSCRIPT No matching script")
                
                # Use lock to make the operation atomic
                with self.lock:
                    key = args[0]
                    now = int(args[1])
                    window_size = int(args[2])
                    max_requests = int(args[3])
                    precision = int(args[4])
                    overlap_factor = float(args[5])
                    
                    # Initialize key if not exists
                    if key not in self.data:
                        self.data[key] = []
                    
                    # Remove old requests
                    old_count = len(self.data[key])
                    self.data[key] = [t for t in self.data[key] if t > now - window_size]
                    removed = old_count - len(self.data[key])
                    
                    # Get current count
                    current = len(self.data[key])
                    
                    # Check if allowed
                    allowed = current < max_requests
                    
                    if not allowed:
                        utilization = current / max_requests
                        remaining = 0
                        return [0, remaining, now + window_size, current, utilization, removed]
                    
                    # Add new request if allowed
                    self.data[key].append(now)
                    current = len(self.data[key])
                    utilization = current / max_requests
                    
                    # Calculate remaining requests
                    remaining = max_requests - current
                    if remaining < 0:
                        remaining = 0
                    
                    # Calculate reset time
                    reset_time = now + window_size
                    
                    return [1, remaining, reset_time, current, utilization, removed]
            
            def zadd(self, key: str, *args) -> int:
                with self.lock:
                    if key not in self.data:
                        self.data[key] = []
                    self.data[key].append(args[0])
                    return 1
            
            def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
                with self.lock:
                    if key not in self.data:
                        return 0
                    count = len(self.data[key])
                    self.data[key] = [t for t in self.data[key] if t < min_score or t > max_score]
                    return count - len(self.data[key])
            
            def zcard(self, key: str) -> int:
                with self.lock:
                    return len(self.data.get(key, []))
            
            def expire(self, key: str, seconds: int) -> int:
                return 1
            
            def flushall(self) -> None:
                with self.lock:
                    self.data.clear()
        
        return InMemoryRedis()
    
    def _get_lua_script(self) -> str:
        return """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_size = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        
        -- Helper function to get reset time
        local function get_reset_time()
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local reset = now + window_size
            if oldest and #oldest > 0 then
                reset = tonumber(oldest[2]) + window_size
            end
            return reset
        end
        
        -- Remove old requests first (older than window_size)
        local removed = redis.call('ZREMRANGEBYSCORE', key, 0, now - window_size)
        
        -- Get current count after cleanup
        local count = redis.call('ZCARD', key)
        
        -- If we've already hit the limit, don't add the request
        if count >= max_requests then
            local utilization = count / max_requests
            return {0, 0, get_reset_time(), count, utilization, removed}  -- not allowed, remaining=0, reset time, count, utilization, removed
        end
        
        -- Create a unique member ID for this request
        local member = string.format("%d-%d", now, count + 1)
        redis.call('ZADD', key, now, member)
        
        -- Set expiration
        redis.call('EXPIRE', key, math.ceil(window_size/1000) + 1)
        
        -- Get final count for accurate remaining calculation
        count = redis.call('ZCARD', key)
        
        -- Calculate window utilization after adding the request
        local utilization = count / max_requests
        
        -- Handle race condition
        if count > max_requests then
            redis.call('ZREM', key, member)
            return {0, 0, get_reset_time(), count, utilization, removed}  -- not allowed, remaining=0, reset time, count, utilization, removed
        end
        
        -- Calculate remaining requests
        local remaining = max_requests - count
        if remaining < 0 then
            remaining = 0
        end
        
        return {1, remaining, now + window_size, count, utilization, removed}  -- allowed, remaining, reset time, count, utilization, removed
        """
    
    def is_allowed(self, key: str) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed.
        Returns: (allowed, remaining, reset_time)
        """
        start_time = time.time()
        now = int(time.time() * 1000)
        try:
            result = self.redis.evalsha(
                self.script_sha,
                1,  # numkeys
                key,
                str(now),
                str(self.window_size_ms),
                str(self.max_requests),
                str(self.precision),
                str(self.overlap_factor)
            )
            
            is_allowed = bool(result[0])
            remaining = result[1]
            reset_time = result[2]
            current_count = result[3]
            utilization = result[4]
            removed_count = result[5]
            
            # Update metrics
            if is_allowed:
                self.metrics.requests_total.labels(status='success', algorithm='sliding_window_log').inc()
                self.metrics.current_requests.labels(algorithm='sliding_window_log').set(current_count)
            else:
                self.metrics.requests_total.labels(status='rate_limited', algorithm='sliding_window_log').inc()
                self.metrics.rate_limited_requests.labels(algorithm='sliding_window_log').inc()
                self.metrics.current_requests.labels(algorithm='sliding_window_log').set(current_count)
            
            # Update sliding window specific metrics
            self.metrics.sliding_window_utilization.labels(algorithm='sliding_window_log').set(utilization)
            self.metrics.window_cleanup_operations.labels(algorithm='sliding_window_log').inc()
            self.metrics.requests_removed.labels(algorithm='sliding_window_log').inc(removed_count)
            self.metrics.window_overlap.labels(algorithm='sliding_window_log').set(self.overlap_factor)
            self.metrics.request_distribution.labels(algorithm='sliding_window_log').observe(utilization)
            
            # Record request duration
            self.metrics.request_duration.labels(algorithm='sliding_window_log').observe(time.time() - start_time)
            
            return is_allowed, remaining, reset_time
            
        except redis.ResponseError as e:
            if "NOSCRIPT" in str(e):
                # Reload script if it was evicted
                self.script_sha = self.redis.script_load(self.script)
                return self.is_allowed(key)
            self.metrics.requests_total.labels(status='error', algorithm='sliding_window_log').inc()
            raise
    
    def get_rate_limit_info(self, identifier: str) -> Tuple[int, int]:
        """Get current rate limit information."""
        current_time = int(time.time() * 1000)
        key = f"ratelimit:log:{identifier}"
        
        try:
            # Remove old requests
            removed = self.redis.zremrangebyscore(key, 0, current_time - self.window_size_ms)
            
            # Get current count
            current_count = self.redis.zcard(key)
            
            # Update cleanup metrics
            self.metrics.window_cleanup_operations.labels(algorithm='sliding_window_log').inc()
            self.metrics.requests_removed.labels(algorithm='sliding_window_log').inc(removed)
            
            remaining = max(0, self.max_requests - current_count)
            return current_count, remaining
            
        except Exception as e:
            print(f"Error getting rate limit info: {e}")
            return 0, self.max_requests 