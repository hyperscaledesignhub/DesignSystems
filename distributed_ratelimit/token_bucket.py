import time
from typing import Tuple
import redis
from .metrics import RateLimiterMetrics

class TokenBucketRateLimiter:
    """
    A distributed rate limiter using the token bucket algorithm.
    Good for handling bursts while maintaining average rate.
    """
    
    def __init__(self, redis_client, capacity: int = 100, refill_rate: float = 10):
        """
        Initialize the rate limiter.
        
        Args:
            redis_client: Redis client instance
            capacity: Maximum number of tokens in the bucket
            refill_rate: Number of tokens added per second
        """
        self.redis = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.token_script_sha = self._load_token_script()
        self.metrics = RateLimiterMetrics()
    
    def _load_token_script(self) -> str:
        """
        Load the Lua script for atomic token operations.
        Returns the SHA of the loaded script.
        """
        script = """
        local key = KEYS[1]
        local current_time = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local refill_rate = tonumber(ARGV[3])
        
        -- Get current state
        local state = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(state[1])
        local last_refill = tonumber(state[2])
        
        -- Initialize if not exists
        if not tokens or not last_refill then
            tokens = capacity
            last_refill = current_time
        end
        
        -- Calculate time passed and new tokens
        local time_passed = current_time - last_refill
        local new_tokens = (time_passed * refill_rate) / 1000.0
        
        -- Update tokens (don't exceed capacity)
        tokens = math.min(capacity, tokens + new_tokens)
        
        -- Try to take a token
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
            -- Calculate time until next token
            local time_until_next = 1000.0 / refill_rate
            return {1, tokens, current_time + time_until_next}
        else
            -- Calculate time until next token
            local time_until_next = ((1 - tokens) * 1000.0) / refill_rate
            return {0, 0, current_time + time_until_next}
        end
        """
        return self.redis.script_load(script)
    
    def _get_bucket_key(self, identifier: str) -> str:
        """
        Get the Redis key for the token bucket.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Redis key for the token bucket
        """
        return f"ratelimit:tokenbucket:{identifier}"
    
    def is_allowed(self, identifier: str) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed based on token bucket.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        current_time = int(time.time() * 1000)
        bucket_key = self._get_bucket_key(identifier)
        
        try:
            # Execute atomic operation
            results = self.redis.evalsha(
                self.token_script_sha,
                1,  # Number of keys
                bucket_key,
                str(current_time),
                str(self.capacity),
                str(self.refill_rate)
            )
            
            allowed = bool(results[0])
            remaining = int(results[1])
            reset_time = int(results[2])
            
            # Update metrics
            if allowed:
                self.metrics.requests_total.labels(status='success', algorithm='token_bucket').inc()
                self.metrics.current_requests.labels(algorithm='token_bucket').set(self.capacity - remaining)
                self.metrics.token_bucket_accepted_requests.labels(algorithm='token_bucket').inc()
                self.metrics.token_bucket_tokens_consumed.labels(algorithm='token_bucket').inc()
            else:
                self.metrics.requests_total.labels(status='rate_limited', algorithm='token_bucket').inc()
                self.metrics.rate_limited_requests.labels(algorithm='token_bucket').inc()
                self.metrics.current_requests.labels(algorithm='token_bucket').set(0)
                self.metrics.token_bucket_rejected_requests.labels(algorithm='token_bucket').inc()
            
            # Calculate derived metrics
            total_requests = self.metrics.requests_total.labels(status='success', algorithm='token_bucket')._value.get() + \
                           self.metrics.requests_total.labels(status='rate_limited', algorithm='token_bucket')._value.get()
            
            if total_requests > 0:
                # Acceptance rate
                acceptance_rate = self.metrics.token_bucket_accepted_requests.labels(algorithm='token_bucket')._value.get() / total_requests
                self.metrics.token_bucket_acceptance_rate.labels(algorithm='token_bucket').set(acceptance_rate)
                
                # Fill level
                fill_level = remaining / self.capacity
                self.metrics.token_bucket_fill_level.labels(algorithm='token_bucket').set(fill_level)
                
                # Rejection rate
                rejection_rate = self.metrics.token_bucket_rejected_requests.labels(algorithm='token_bucket')._value.get() / total_requests
                self.metrics.token_bucket_rejection_rate.labels(algorithm='token_bucket').set(rejection_rate)
                
                # Average tokens per request
                if self.metrics.token_bucket_accepted_requests.labels(algorithm='token_bucket')._value.get() > 0:
                    avg_tokens = self.metrics.token_bucket_tokens_consumed.labels(algorithm='token_bucket')._value.get() / \
                                self.metrics.token_bucket_accepted_requests.labels(algorithm='token_bucket')._value.get()
                    self.metrics.token_bucket_avg_tokens_per_request.labels(algorithm='token_bucket').set(avg_tokens)
            
            return allowed, remaining, reset_time
            
        except redis.exceptions.NoScriptError:
            # Reload script if it was evicted
            self.token_script_sha = self._load_token_script()
            return self.is_allowed(identifier)
    
    def get_rate_limit_info(self, identifier: str) -> Tuple[int, int]:
        """
        Get current rate limit information.
        
        Args:
            identifier: Unique identifier for the rate limit
            
        Returns:
            Tuple of (current_tokens, remaining)
        """
        current_time = int(time.time() * 1000)
        bucket_key = self._get_bucket_key(identifier)
        
        # Get current state
        state = self.redis.hmget(bucket_key, 'tokens', 'last_refill')
        if not state[0] or not state[1]:
            return self.capacity, 0
            
        tokens = float(state[0])
        last_refill = int(state[1])
        
        # Calculate time passed and new tokens
        time_passed = current_time - last_refill
        new_tokens = (time_passed * self.refill_rate) / 1000.0
        
        # Update tokens (don't exceed capacity)
        tokens = min(self.capacity, tokens + new_tokens)
        
        return int(tokens), self.capacity - int(tokens) 