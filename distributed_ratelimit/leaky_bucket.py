import time
from typing import Tuple, Dict
import redis
import logging
import threading
from .metrics import RateLimiterMetrics

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LeakyBucketRateLimiter:
    """
    A distributed rate limiter using the leaky bucket algorithm.
    Good for maintaining a constant output rate.
    """
    
    def __init__(self, redis_client, capacity: int = 5, leak_rate: float = 5, metrics=None):
        """
        Initialize the rate limiter.
        
        Args:
            redis_client: Redis client instance
            capacity: Maximum number of requests in the bucket
            leak_rate: Number of requests leaked per second
            metrics: Optional RateLimiterMetrics instance
        """
        self.redis = redis_client
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.leak_script_sha = None
        self.metrics = metrics or RateLimiterMetrics()
        
        # Fallback in-memory storage when Redis is not available
        self.local_storage: Dict[str, Dict] = {}
        self.local_lock = threading.Lock()
        
        # Try to load the script if Redis is available
        if self.redis is not None:
            try:
                self.leak_script_sha = self._load_leak_script()
            except redis.RedisError:
                logger.warning("Failed to load Lua script into Redis")

    def _load_leak_script(self) -> str:
        """
        Load the Lua script for atomic leak operations.
        Returns the SHA of the loaded script.
        """
        script = """
        local key = KEYS[1]
        local current_time = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local leak_rate = tonumber(ARGV[3])
        
        -- Get current state atomically
        local state = redis.call('HMGET', key, 'requests', 'last_leak')
        local requests = tonumber(state[1])
        local last_leak = tonumber(state[2])
        
        -- Initialize if not exists
        if not requests or not last_leak then
            requests = 0
            last_leak = current_time
            redis.call('HMSET', key, 'requests', requests, 'last_leak', last_leak)
            redis.call('EXPIRE', key, 3600)  -- Set expiration to 1 hour
        end
        
        -- Calculate time passed (in seconds) and leaked requests
        local time_passed = (current_time - last_leak) / 1000.0
        local leaked_requests = math.floor(time_passed * leak_rate)
        
        -- Update requests (don't go below 0) and store the new count
        local original_requests = requests
        requests = math.max(0, requests - leaked_requests)
        leaked_requests = original_requests - requests  -- Actual number of requests leaked
        
        -- Update last_leak time based on actual leaks
        if leaked_requests > 0 then
            -- Only update last_leak based on actual leaks
            last_leak = last_leak + math.floor((leaked_requests / leak_rate) * 1000)
        end
        
        -- Check if we can add a new request
        if requests >= capacity then
            -- Calculate time until next leak (in ms)
            local time_until_next = math.ceil(1000.0 / leak_rate)
            redis.call('HMSET', key, 'requests', requests, 'last_leak', last_leak)
            redis.call('EXPIRE', key, 3600)  -- Refresh expiration
            return {0, 0, current_time + time_until_next, leaked_requests, time_passed}
        end
        
        -- Increment requests atomically
        requests = requests + 1
        redis.call('HMSET', key, 'requests', requests, 'last_leak', last_leak)
        redis.call('EXPIRE', key, 3600)  -- Refresh expiration
        
        -- Calculate remaining and reset time
        local remaining = math.max(0, capacity - requests)
        -- Calculate time until bucket is empty (in ms)
        local time_until_empty = math.ceil((requests * 1000.0) / leak_rate)
        
        -- Return result with proper remaining count and additional metrics
        return {1, remaining, current_time + time_until_empty, leaked_requests, time_passed}
        """
        return self.redis.script_load(script)
    
    def _get_bucket_key(self, identifier: str) -> str:
        """
        Get the Redis key for the leaky bucket.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Redis key for the leaky bucket
        """
        return f"ratelimit:leakybucket:{identifier}"
    
    def _process_local(self, identifier: str) -> Tuple[bool, int, int]:
        """
        Process rate limiting locally when Redis is not available.
        """
        start_time = time.time()
        current_time = int(time.time() * 1000)
        
        with self.local_lock:
            if identifier not in self.local_storage:
                self.local_storage[identifier] = {
                    'requests': 0,
                    'last_leak': current_time
                }
            
            state = self.local_storage[identifier]
            requests = state['requests']
            last_leak = state['last_leak']
            
            # Calculate time passed and leaked requests
            time_passed = (current_time - last_leak) / 1000.0
            leaked_requests = int(time_passed * self.leak_rate)
            
            # Update requests count after leaking
            original_requests = requests
            requests = max(0, requests - leaked_requests)
            leaked_requests = original_requests - requests  # Actual number of requests leaked
            
            # Update last_leak time based on actual leaks
            if leaked_requests > 0:
                # Only update last_leak based on actual leaks
                last_leak += int((leaked_requests / self.leak_rate) * 1000)
            
            # Update metrics
            self.metrics.leaky_bucket_leak_rate.labels(algorithm='leaky_bucket').set(self.leak_rate)
            self.metrics.leaky_bucket_queue_size.labels(algorithm='leaky_bucket').set(requests)
            self.metrics.leaky_bucket_queue_utilization.labels(algorithm='leaky_bucket').set(requests / self.capacity)
            self.metrics.leaky_bucket_time_since_last_leak.labels(algorithm='leaky_bucket').set(time_passed)
            
            if time_passed > 0:
                actual_leak_rate = leaked_requests / time_passed
                self.metrics.leaky_bucket_actual_leak_rate.labels(algorithm='leaky_bucket').set(actual_leak_rate)
                
                if leaked_requests > 0:
                    self.metrics.leaky_bucket_leaks_total.labels(algorithm='leaky_bucket').inc()
                    self.metrics.leaky_bucket_requests_leaked.labels(algorithm='leaky_bucket').inc(leaked_requests)
            
            # Try to increment requests
            new_requests = requests + 1
            
            # Check if we exceeded capacity
            if new_requests > self.capacity:
                # Calculate time until next leak (in ms)
                time_until_next = int(1000.0 / self.leak_rate)
                state['requests'] = requests
                state['last_leak'] = last_leak
                
                # Update rejection metrics
                self.metrics.leaky_bucket_consecutive_rejections.labels(algorithm='leaky_bucket').inc()
                self.metrics.leaky_bucket_queue_blocked_time.labels(algorithm='leaky_bucket').inc(time_until_next / 1000.0)
                self.metrics.leaky_bucket_time_until_next_leak.labels(algorithm='leaky_bucket').set(time_until_next / 1000.0)
                
                # Update request duration
                self.metrics.request_duration.labels(algorithm='leaky_bucket').observe(time.time() - start_time)
                
                return False, 0, current_time + time_until_next
            
            # Update state with new request count
            state['requests'] = new_requests
            state['last_leak'] = last_leak
            
            # Calculate remaining and reset time
            remaining = self.capacity - new_requests
            time_until_empty = int((new_requests * 1000.0) / self.leak_rate)
            
            # Update success metrics
            self.metrics.leaky_bucket_consecutive_rejections.labels(algorithm='leaky_bucket')._value.set(0)
            self.metrics.leaky_bucket_queue_availability.labels(algorithm='leaky_bucket').set(1.0)
            
            # Update request duration
            self.metrics.request_duration.labels(algorithm='leaky_bucket').observe(time.time() - start_time)
            
            return True, remaining, current_time + time_until_empty
    
    def is_allowed(self, identifier: str) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed based on leaky bucket.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        start_time = time.time()
        
        # Use local processing if Redis is not available
        if self.redis is None or self.leak_script_sha is None:
            return self._process_local(identifier)
        
        current_time = int(time.time() * 1000)
        bucket_key = self._get_bucket_key(identifier)
        
        max_retries = 3
        for _ in range(max_retries):
            try:
                # Execute atomic operation
                results = self.redis.evalsha(
                    self.leak_script_sha,
                    1,  # Number of keys
                    bucket_key,
                    str(current_time),
                    str(self.capacity),
                    str(self.leak_rate)
                )
                
                allowed = bool(results[0])
                remaining = int(results[1])
                reset_time = int(results[2])
                leaked_requests = int(results[3])
                time_passed = float(results[4])
                
                if reset_time == current_time:
                    # Transaction failed, retry
                    continue
                
                # Update time since last leak metric
                self.metrics.leaky_bucket_time_since_last_leak.labels(algorithm='leaky_bucket').set(time_passed)
                
                # Update basic metrics
                self.metrics.leaky_bucket_leak_rate.labels(algorithm='leaky_bucket').set(self.leak_rate)
                
                # Get current state for metrics
                state = self.redis.hmget(bucket_key, 'requests')
                requests = float(state[0]) if state[0] else 0
                
                self.metrics.leaky_bucket_queue_size.labels(algorithm='leaky_bucket').set(requests)
                self.metrics.leaky_bucket_queue_utilization.labels(algorithm='leaky_bucket').set(requests / self.capacity)
                
                # Update actual leak rate if time has passed
                if time_passed > 0:
                    actual_leak_rate = leaked_requests / time_passed
                    self.metrics.leaky_bucket_actual_leak_rate.labels(algorithm='leaky_bucket').set(actual_leak_rate)
                    
                    # Update leaked requests counter
                    if leaked_requests > 0:
                        self.metrics.leaky_bucket_leaks_total.labels(algorithm='leaky_bucket').inc()
                        self.metrics.leaky_bucket_requests_leaked.labels(algorithm='leaky_bucket').inc(leaked_requests)
                
                if not allowed:
                    self.metrics.leaky_bucket_consecutive_rejections.labels(algorithm='leaky_bucket').inc()
                    time_until_next = (reset_time - current_time) / 1000.0
                    self.metrics.leaky_bucket_queue_blocked_time.labels(algorithm='leaky_bucket').inc(time_until_next)
                    self.metrics.leaky_bucket_time_until_next_leak.labels(algorithm='leaky_bucket').set(time_until_next)
                else:
                    self.metrics.leaky_bucket_consecutive_rejections.labels(algorithm='leaky_bucket')._value.set(0)
                    self.metrics.leaky_bucket_queue_availability.labels(algorithm='leaky_bucket').set(1.0)
                
                # Update request duration
                self.metrics.request_duration.labels(algorithm='leaky_bucket').observe(time.time() - start_time)
                
                return allowed, remaining, reset_time
                
            except redis.exceptions.NoScriptError:
                # Reload script if it was evicted
                self.leak_script_sha = self._load_leak_script()
            except redis.exceptions.WatchError:
                # Key was modified, retry
                continue
        
        # If all retries failed, use local processing
        logger.warning("Redis transactions failed, falling back to local storage")
        return self._process_local(identifier)
    
    def get_rate_limit_info(self, identifier: str) -> Tuple[int, int]:
        """
        Get current rate limit information.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Tuple of (current_requests, remaining)
        """
        if self.redis is None:
            with self.local_lock:
                if identifier not in self.local_storage:
                    return 0, self.capacity
                state = self.local_storage[identifier]
                requests = state['requests']
                return requests, self.capacity - requests
        
        current_time = int(time.time() * 1000)
        bucket_key = self._get_bucket_key(identifier)
        
        try:
            # Get current state
            state = self.redis.hmget(bucket_key, 'requests', 'last_leak')
            if not state[0] or not state[1]:
                return 0, self.capacity
            
            requests = float(state[0])
            last_leak = int(state[1])
            
            # Calculate time passed and leaked requests
            time_passed = current_time - last_leak
            leaked_requests = (time_passed * self.leak_rate) / 1000.0
            
            # Update requests (don't go below 0)
            requests = max(0, requests - leaked_requests)
            
            return int(requests), self.capacity - int(requests)
        except redis.RedisError:
            logger.warning("Redis operation failed, falling back to local storage")
            return self._process_local(identifier)[1:3] 