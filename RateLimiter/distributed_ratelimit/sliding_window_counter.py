import time
import logging
from typing import Tuple, Optional, Dict
import redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
import math
from .metrics import RateLimiterMetrics
import threading

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlidingWindowCounterRateLimiter:
    """
    A distributed rate limiter using the sliding window counter algorithm.
    This implementation uses Redis sorted sets to track requests and calculate rates.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key: str,
        max_requests: int,
        window_size_ms: int,
        precision_ms: int = 1000,
        cleanup_interval_ms: int = 1000,
        overlap_factor: float = 0.6
    ):
        """Initialize the sliding window counter rate limiter.

        Args:
            redis_client: Redis client instance
            key: Redis key prefix for storing rate limit data
            max_requests: Maximum number of requests allowed in the window
            window_size_ms: Window size in milliseconds
            precision_ms: Precision for rate limiting in milliseconds
            cleanup_interval_ms: Interval for cleaning up old requests in milliseconds
            overlap_factor: Factor for weighting requests in the previous window
        """
        self.redis = redis_client
        self.key = key
        self.max_requests = max_requests
        self.window_size_ms = window_size_ms
        self.precision_ms = precision_ms
        self.cleanup_interval_ms = cleanup_interval_ms
        self.overlap_factor = overlap_factor
        self._last_cleanup_time = 0

        # Initialize metrics
        self.metrics = RateLimiterMetrics()
        
        # Reset all metrics for this algorithm
        self.metrics.reset_metrics('sliding_window_counter')
        
        # Set configuration metrics after reset
        self.metrics.window_size.labels(algorithm='sliding_window_counter').set(window_size_ms / 1000.0)  # Convert to seconds
        self.metrics.sliding_window_counter_overlap.labels(algorithm='sliding_window_counter').set(overlap_factor)
        self.metrics.precision.labels(algorithm='sliding_window_counter').set(precision_ms)
        
        # Initialize other metrics to 0
        self.metrics.current_requests.labels(algorithm='sliding_window_counter').set(0)
        self.metrics.sliding_window_counter_utilization.labels(algorithm='sliding_window_counter').set(0)
        self.metrics.sliding_window_counter_cleanup_operations.labels(algorithm='sliding_window_counter')._value.set(0)
        self.metrics.sliding_window_counter_requests_removed.labels(algorithm='sliding_window_counter')._value.set(0)
        self.metrics.rate_limited_requests.labels(algorithm='sliding_window_counter')._value.set(0)
        
        # Load Lua script
        self.script = self._load_lua_script()
        logger.info("Successfully loaded Lua scripts for rate limiting")

        # Start background task for metric updates
        self._start_metric_update_task()

    def _load_lua_script(self) -> str:
        """Load the Lua script for rate limiting."""
        script = """
            local key = KEYS[1]
            local current_time = tonumber(ARGV[1])
            local window_size = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local precision = tonumber(ARGV[4])
            local cleanup_interval = tonumber(ARGV[5])

            -- Calculate window boundaries with precision
            local current_window_start = math.floor(current_time / precision) * precision
            local prev_window_start = current_window_start - window_size

            -- Remove expired entries (older than two windows)
            local removed_count = redis.call('ZREMRANGEBYSCORE', key, '-inf', prev_window_start)

            -- Always perform cleanup if there are expired entries
            if removed_count > 0 then
                redis.call('PEXPIRE', key, window_size * 2)  -- Keep data for 2 windows
            end

            -- Count requests in current window
            local current_window_count = redis.call('ZCOUNT', key, current_window_start, current_time)
            
            -- Count requests in previous window that overlap with current window
            local prev_window_count = redis.call('ZCOUNT', key, prev_window_start, current_window_start)

            -- Calculate overlap weight based on elapsed time in current window
            local elapsed_time = (current_time - current_window_start)
            local overlap_weight = elapsed_time / window_size
            
            -- Standard sliding window counter calculation
            local weighted_prev_count = prev_window_count * (1 - overlap_weight)
            local total_count = current_window_count + weighted_prev_count

            -- Get the actual number of requests in Redis
            local actual_count = redis.call('ZCARD', key)
            
            -- If there are no actual requests in Redis, ensure total_count is 0
            if actual_count == 0 then
                total_count = 0
                weighted_prev_count = 0
                current_window_count = 0
                prev_window_count = 0
            end

            -- Check if adding this request would exceed the limit
            local is_allowed = (total_count + 1) <= max_requests

            -- Add current request if allowed
            if is_allowed then
                -- Add current request with unique score to prevent collisions
                local score = string.format("%.6f", current_time + (math.random() * 0.000001))
                redis.call('ZADD', key, score, tostring(current_time))
                -- Set expiration time for the key
                redis.call('PEXPIRE', key, window_size * 2)  -- Keep data for 2 windows
                -- Update total count after adding request
                total_count = total_count + 1
                current_window_count = current_window_count + 1
            end
            -- Now calculate remaining after adding (or not adding)
            local remaining = 0
            if is_allowed then
                remaining = math.max(0, max_requests - total_count)
            end

            -- Calculate final utilization
            local utilization = total_count / max_requests

            -- Log debug information
            redis.log(redis.LOG_DEBUG, string.format("current_window_count=%d, prev_window_count=%d, weighted_prev_count=%d, total_count=%d, utilization=%.2f, remaining=%d",
                current_window_count, prev_window_count, weighted_prev_count, total_count, utilization, remaining))

            -- Return whether the request is allowed, remaining requests, reset time, and metrics
            return {
                is_allowed and 1 or 0,  -- is_allowed
                remaining,              -- remaining requests
                current_time + window_size,  -- reset time
                total_count,            -- current count
                utilization,            -- window utilization
                removed_count,          -- number of requests removed in cleanup
                overlap_weight,         -- current overlap weight
                current_window_count,   -- current window count
                prev_window_count,      -- previous window count
                weighted_prev_count     -- weighted previous window count
            }
        """
        return self.redis.script_load(script)

    def _start_metric_update_task(self):
        """Start background task to update metrics periodically."""
        def update_metrics():
            while True:
                try:
                    # Reset metrics every 5 minutes
                    reset_interval = 300  # Reset metrics every 5 minutes
                    current_time = time.time()
                    
                    if current_time - self._last_cleanup_time >= reset_interval:
                        logger.info("Resetting metrics for sliding window counter")
                        self.metrics.reset_metrics('sliding_window_counter')
                        self._last_cleanup_time = current_time
                    
                    time.sleep(1)  # Check every second
                except Exception as e:
                    logger.error(f"Error in metric update task: {str(e)}")
                    time.sleep(1)  # Wait before retrying
        
        # Start the background thread
        thread = threading.Thread(target=update_metrics, daemon=True)
        thread.start()
        logger.info("Started background metric update task")

    def is_allowed(self, identifier: str) -> Tuple[bool, int, int]:
        """Check if a request is allowed based on sliding window counter.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        start_time = time.time()
        current_time = int(start_time * 1000)
        
        # Calculate window boundaries
        current_window_start = (current_time // self.precision_ms) * self.precision_ms
        previous_window_start = current_window_start - self.window_size_ms
        
        # Get the Redis key
        key = f"{self.key}:{identifier}"
        
        try:
            # Execute atomic operation
            results = self.redis.evalsha(
                self.script,
                1,  # Number of keys
                key,
                str(current_time),
                str(self.window_size_ms),
                str(self.max_requests),
                str(self.precision_ms),
                str(self.cleanup_interval_ms)
            )
            
            allowed = bool(results[0])
            remaining = int(results[1])
            reset_time = int(results[2])
            current_count = int(results[3])
            utilization = float(results[4])
            removed_count = int(results[5])
            overlap_weight = float(results[6])
            current_window_count = int(results[7])
            prev_window_count = int(results[8])
            weighted_prev_count = int(results[9])
            
            # Update metrics
            if allowed:
                self.metrics.requests_total.labels(status='success', algorithm='sliding_window_counter').inc()
            else:
                self.metrics.requests_total.labels(status='rate_limited', algorithm='sliding_window_counter').inc()
                self.metrics.rate_limited_requests.labels(algorithm='sliding_window_counter').inc()
            
            # Update current requests with the total count from Lua script
            self.metrics.current_requests.labels(algorithm='sliding_window_counter').set(current_count)
            
            # Calculate and update window utilization
            utilization_value = float(current_count) / float(self.max_requests)
            logger.info(f"Setting utilization to {utilization_value} (current_count={current_count}, max_requests={self.max_requests})")
            self.metrics.sliding_window_counter_utilization.labels(algorithm='sliding_window_counter').set(utilization_value)
            
            # Update window overlap with the calculated weight
            self.metrics.sliding_window_counter_overlap.labels(algorithm='sliding_window_counter').set(overlap_weight)
            
            # Update cleanup operations and removed requests if cleanup occurred
            if removed_count > 0:
                self.metrics.sliding_window_counter_cleanup_operations.labels(algorithm='sliding_window_counter').inc()
                self.metrics.sliding_window_counter_requests_removed.labels(algorithm='sliding_window_counter').inc(removed_count)
            
            # Update request duration
            duration = time.time() - start_time
            self.metrics.request_duration.labels(algorithm='sliding_window_counter').observe(duration)
            
            # Log metrics for debugging
            logger.info(f"Metrics updated - allowed: {allowed}, current_count: {current_count}, "
                       f"utilization: {utilization_value}, removed_count: {removed_count}")
            
            return allowed, remaining, reset_time
            
        except redis.exceptions.NoScriptError:
            # Reload script if it was evicted
            self.script = self._load_lua_script()
            return self.is_allowed(identifier)

    def get_rate_limit_headers(self, key: str, remaining: int, reset_time: int) -> Dict[str, str]:
        """
        Get rate limit headers for a request.
        Returns: Dictionary of rate limit headers
        """
        reset_time_seconds = reset_time // 1000
        
        headers = {
            'X-RateLimit-Limit': str(self.max_requests),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_time_seconds),
            'X-RateLimit-Window': str(self.window_size_ms // 1000)
        }
        
        if remaining <= 0:
            # If rate limited, add Retry-After header
            headers['Retry-After'] = str(max(1, (reset_time_seconds - int(time.time()))))
        
        return headers
    
    def get_rate_limit_info(self, key: str) -> Tuple[int, int]:
        """Get the current count and remaining requests."""
        try:
            current_count = self.redis.zcount(key, '-inf', '+inf')
            remaining = max(0, self.max_requests - current_count)
            return current_count, remaining 
        except Exception as e:
            logger.error(f"Error getting rate limit info: {e}")
            return 0, self.max_requests 

    def get_current_time(self) -> Optional[int]:
        """Get current time in milliseconds from Redis.
        
        Returns:
            Current time in milliseconds or None if Redis fails
        """
        try:
            redis_time = self.redis.time()
            return int(redis_time[0] * 1000 + redis_time[1] / 1000)
        except redis.RedisError as e:
            logger.error(f"Failed to get Redis time: {e}")
            return None

    def _load_script(self) -> Optional[str]:
        """Load the Lua script into Redis.
        
        Returns:
            Script SHA or None if loading fails
        """
        try:
            return self.redis.script_load(SLIDING_WINDOW_SCRIPT)
        except redis.RedisError as e:
            logger.error(f"Failed to load Lua script: {e}")
            return None 