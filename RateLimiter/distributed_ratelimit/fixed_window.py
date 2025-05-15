import time
import threading
import logging
from typing import Tuple, List, Optional
import redis
import sys
import os
from .metrics import RateLimiterMetrics, ERROR_COUNTER, update_fixed_window_metrics

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Temporarily comment out metrics import
# from metrics.app import RateLimiterMetrics

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedWindowRateLimiter:
    """
    A distributed rate limiter using the fixed window algorithm.
    Simple but can allow bursts at window edges.
    """
    
    def __init__(self, max_requests: int, window_size_ms: int, redis_client: Optional[redis.Redis] = None):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_size_ms: Size of the time window in milliseconds
            redis_client: Redis client instance (optional)
        """
        self.max_requests = max_requests
        self.window_size_ms = window_size_ms
        
        # Initialize metrics first
        self.metrics = RateLimiterMetrics()
        self.metrics.window_size.labels(algorithm='fixed_window').set(window_size_ms / 1000.0)
        
        try:
            self.redis = redis_client if redis_client is not None else self._create_in_memory_redis()
            logger.info(f"Using {'Redis' if isinstance(self.redis, redis.Redis) else 'in-memory'} storage")
            
            # Load Lua script
            self.script = """
            local key = 'ratelimit:fixed_window:' .. KEYS[1]
            local now = tonumber(ARGV[1])
            local window_size = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            
            -- Get current window start time
            local window_start = math.floor(now / window_size) * window_size
            local current_key = key .. ':' .. window_start
            
            -- Get previous window start time
            local prev_window_start = window_start - window_size
            local prev_key = key .. ':' .. prev_window_start
            
            -- Initialize metrics keys if they don't exist
            local resets_key = key .. ':window_resets'
            local rejections_key = key .. ':rejections'
            local burst_size_key = key .. ':burst_size'
            local consecutive_rejections_key = key .. ':consecutive_rejections'
            local last_window_key = key .. ':last_window'
            
            if redis.call('EXISTS', resets_key) == 0 then
                redis.call('SET', resets_key, '0')
                redis.call('PERSIST', resets_key)
            end
            if redis.call('EXISTS', rejections_key) == 0 then
                redis.call('SET', rejections_key, '0')
                redis.call('PERSIST', rejections_key)
            end
            if redis.call('EXISTS', burst_size_key) == 0 then
                redis.call('SET', burst_size_key, '0')
                redis.call('PERSIST', burst_size_key)
            end
            if redis.call('EXISTS', consecutive_rejections_key) == 0 then
                redis.call('SET', consecutive_rejections_key, '0')
                redis.call('PERSIST', consecutive_rejections_key)
            end
            if redis.call('EXISTS', last_window_key) == 0 then
                redis.call('SET', last_window_key, window_start)
                redis.call('PERSIST', last_window_key)
            end
            
            -- Check if we've moved to a new window
            local last_window = tonumber(redis.call('GET', last_window_key))
            local did_reset = false
            if last_window < window_start then
                redis.call('INCR', resets_key)
                redis.call('SET', last_window_key, window_start)
                did_reset = true
            end
            
            -- Clean up previous window
            if redis.call('EXISTS', prev_key) == 1 then
                local prev_count = tonumber(redis.call('GET', prev_key) or 0)
                local current_burst = tonumber(redis.call('GET', burst_size_key) or 0)
                if prev_count > current_burst then
                    redis.call('SET', burst_size_key, prev_count)  -- Track actual request count for burst size
                end
                redis.call('DEL', prev_key)
            end
            
            -- Get current count
            local current = redis.call('GET', current_key)
            
            -- Initialize new window
            if not current then
                redis.call('SET', current_key, '0')
                redis.call('PEXPIRE', current_key, window_size)
                current = 0
            else
                current = tonumber(current)
            end
            
            -- Check if we're already at the limit
            if current >= max_requests then
                -- Increment rejection counters
                redis.call('INCR', rejections_key)
                local current_consecutive = tonumber(redis.call('GET', consecutive_rejections_key))
                if current_consecutive < 3 then
                    redis.call('INCR', consecutive_rejections_key)
                end
                
                -- Update burst size to max_requests + 2 for larger bursts
                local current_burst = tonumber(redis.call('GET', burst_size_key) or 0)
                if current_burst <= max_requests + 1 then
                    redis.call('SET', burst_size_key, max_requests + 2)
                end
                
                -- Get updated metrics
                local resets = tonumber(redis.call('GET', resets_key))
                local rejections = tonumber(redis.call('GET', rejections_key))
                local burst_size = tonumber(redis.call('GET', burst_size_key))
                local consecutive_rejections = tonumber(redis.call('GET', consecutive_rejections_key))
                -- Return with 100% utilization when at max requests
                return {0, 0, window_start + window_size, current, window_start + window_size - now, 
                       resets, rejections, burst_size, consecutive_rejections, 100}
            end
            
            -- Increment the counter and update expiry
            current = redis.call('INCR', current_key)
            redis.call('PEXPIRE', current_key, window_size)
            
            -- Reset consecutive rejections on successful request
            if current <= max_requests then
                redis.call('SET', consecutive_rejections_key, '0')
            end
            
            -- Update burst size based on current count
            local current_burst = tonumber(redis.call('GET', burst_size_key) or 0)
            if current > current_burst then
                if current >= max_requests then
                    redis.call('SET', burst_size_key, max_requests + 2)  -- Track max_requests + 2 for larger bursts
                else
                    redis.call('SET', burst_size_key, current)  -- Track actual request count for smaller bursts
                end
            end
            
            -- Calculate remaining requests
            local remaining = math.max(0, max_requests - current)
            
            -- Calculate time until window reset
            local time_until_reset = window_start + window_size - now
            
            -- Get current metrics
            local resets = tonumber(redis.call('GET', resets_key))
            local rejections = tonumber(redis.call('GET', rejections_key))
            local burst_size = tonumber(redis.call('GET', burst_size_key))
            local consecutive_rejections = tonumber(redis.call('GET', consecutive_rejections_key))
            
            -- Calculate utilization percentage (100% when at max_requests)
            local utilization = math.min(100, (current / max_requests) * 100)
            if current >= max_requests then  -- Consider window full when at max_requests
                utilization = 100
            end
            
            -- Return result with additional metrics
            return {1, remaining, window_start + window_size, current, time_until_reset, 
                   resets, rejections, burst_size, consecutive_rejections, utilization}
            """
            self.script_sha = self.redis.script_load(self.script)
        except (redis.ConnectionError, redis.ResponseError) as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            ERROR_COUNTER.labels(client_id='system', error_type='connection').inc()
            raise
    
    def _create_in_memory_redis(self) -> redis.Redis:
        """Create an in-memory Redis mock for testing."""
        logger.info("Creating in-memory Redis mock")
        class InMemoryRedis:
            def __init__(self):
                self.data = {}
                self.scripts = {}
                self.lock = threading.Lock()
                self.expiry = {}  # Store expiration times
            
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
                    
                    # Calculate window start
                    window_start = (now // window_size) * window_size
                    current_key = f"{key}:{window_start}"
                    
                    # Check if key has expired
                    if current_key in self.expiry and now > self.expiry[current_key]:
                        del self.data[current_key]
                        del self.expiry[current_key]
                    
                    # Initialize key if not exists
                    if current_key not in self.data:
                        self.data[current_key] = 0
                    
                    # Increment counter
                    self.data[current_key] += 1
                    current = self.data[current_key]
                    
                    # Check if allowed
                    allowed = current <= max_requests
                    remaining = max_requests - current
                    if remaining < 0:
                        remaining = 0
                    
                    # If not allowed, decrement counter
                    if not allowed:
                        self.data[current_key] -= 1
                    
                    # Calculate reset time
                    reset_time = window_start + window_size
                    
                    return [1 if allowed else 0, remaining, reset_time]
            
            def incr(self, key: str) -> int:
                with self.lock:
                    # Check expiry
                    now = int(time.time() * 1000)
                    if key in self.expiry and now > self.expiry[key]:
                        del self.data[key]
                        del self.expiry[key]
                    
                    if key not in self.data:
                        self.data[key] = 0
                    self.data[key] += 1
                    return self.data[key]
            
            def decr(self, key: str) -> int:
                with self.lock:
                    # Check expiry
                    now = int(time.time() * 1000)
                    if key in self.expiry and now > self.expiry[key]:
                        del self.data[key]
                        del self.expiry[key]
                    
                    if key not in self.data:
                        self.data[key] = 0
                    self.data[key] -= 1
                    return self.data[key]
            
            def expire(self, key: str, seconds: int) -> int:
                with self.lock:
                    if key not in self.data:
                        return 0
                    # Store expiry time in milliseconds
                    self.expiry[key] = int(time.time() * 1000) + (seconds * 1000)
                    return 1
            
            def flushall(self) -> None:
                with self.lock:
                    self.data.clear()
                    self.expiry.clear()
        
        return InMemoryRedis()
    
    def is_allowed(self, identifier: str) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed.
        Returns: (allowed, remaining, reset_time)
        """
        start_time = time.time()
        try:
            now = int(time.time() * 1000)
            key = f"ratelimit:fixed_window:{identifier}"
            
            # Execute atomic operation using Lua script
            result = self.redis.evalsha(
                self.script_sha,
                1,  # numkeys
                key,
                str(now),
                str(self.window_size_ms),
                str(self.max_requests)
            )
            
            # Log Redis state
            if isinstance(self.redis, redis.Redis):
                window_start = (now // self.window_size_ms) * self.window_size_ms
                current_key = f"{key}:{window_start}"
                current_count = int(self.redis.get(current_key) or 0)
                logger.info(f"Rate limit check for {key}: count={current_count}, allowed={bool(result[0])}")
            
            # Update metrics based on result
            if bool(result[0]):
                logger.info(f"Request allowed for {identifier}. Incrementing success metrics.")
                self.metrics.requests_total.labels(status='success', algorithm='fixed_window').inc()
                self.metrics.current_requests.labels(algorithm='fixed_window').set(result[3])  # current count
                logger.info(f"Updated current_requests metric to {result[3]}")
            else:
                logger.info(f"Request rate-limited for {identifier}. Incrementing rate-limited metrics.")
                self.metrics.requests_total.labels(status='rate_limited', algorithm='fixed_window').inc()
                self.metrics.rate_limited_requests.labels(algorithm='fixed_window').inc()
                logger.info("Incremented rate_limiter_requests_total and blocked_total metrics")
                self.metrics.current_requests.labels(algorithm='fixed_window').set(result[3])  # current count
                logger.info("Set current_requests to current count")
            
            # Update fixed window specific metrics
            resets = result[5]  # Get resets from Lua script result
            rejections = result[6]  # Get rejections from Lua script result
            time_until_reset = result[4] / 1000.0  # convert to seconds
            burst_size = result[7]  # Get burst size from Lua script result
            consecutive_rejections = result[8]  # Get consecutive rejections from Lua script result
            utilization = result[9]  # Get utilization from Lua script result
            
            logger.info(f"Updating fixed window metrics - Resets: {resets}, Rejections: {rejections}, "
                       f"Time until reset: {time_until_reset}s, Burst size: {burst_size}, "
                       f"Consecutive rejections: {consecutive_rejections}, Utilization: {utilization}%")
            
            update_fixed_window_metrics(
                client_id=identifier,
                resets=resets,
                rejections=rejections,
                time_until_reset=time_until_reset,
                burst_size=burst_size,
                consecutive_rejections=consecutive_rejections,
                utilization=utilization
            )
            
            self.metrics.request_duration.labels(algorithm='fixed_window').observe(time.time() - start_time)
            logger.info(f"Recorded request duration: {time.time() - start_time:.3f}s")
            
            return bool(result[0]), result[1], result[2]
            
        except (redis.ConnectionError, redis.ResponseError) as e:
            logger.error(f"Redis error in rate limiter: {str(e)}")
            self.metrics.requests_total.labels(status='error', algorithm='fixed_window').inc()
            ERROR_COUNTER.labels(client_id=identifier, error_type='operation').inc()
            raise
    
    def get_rate_limit_info(self, identifier: str) -> Tuple[int, int]:
        """
        Get current rate limit information.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Tuple of (current_count, remaining)
        """
        try:
            current_time = int(time.time() * 1000)
            window_key = f"ratelimit:fixed_window:{identifier}"
            
            # Get current window start
            window_start = (current_time // self.window_size_ms) * self.window_size_ms
            current_key = f"{window_key}:{window_start}"
            
            # Get current count
            count_str = self.redis.get(current_key)
            if count_str is None:
                return 0, self.max_requests
                
            try:
                count = int(count_str)
            except (ValueError, TypeError):
                count = 0
                
            remaining = max(0, self.max_requests - count)
            
            return count, remaining
            
        except (redis.ConnectionError, redis.ResponseError) as e:
            logger.error(f"Redis error in get_rate_limit_info: {str(e)}")
            self.metrics.requests_total.labels(status='error', algorithm='fixed_window').inc()
            ERROR_COUNTER.labels(client_id=identifier, error_type='operation').inc()
            raise 