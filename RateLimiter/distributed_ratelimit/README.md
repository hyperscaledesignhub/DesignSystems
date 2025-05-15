# Distributed Rate Limiter

A comprehensive collection of distributed rate limiter implementations using Redis. Includes multiple algorithms for different use cases.

## Features

- Multiple rate limiting algorithms:
  - Sliding Window Counter (Recommended for most use cases)
  - Sliding Window Log
  - Fixed Window
  - Token Bucket
  - Leaky Bucket
- Distributed rate limiting using Redis
- Thread-safe and atomic operations
- Configurable window sizes and request limits
- Support for multiple rate limiters with different configurations

## Installation

```bash
pip install -r requirements.txt
```

## Available Algorithms

### 1. Sliding Window Counter (Recommended)
Best for: General purpose rate limiting with smooth limits
```python
from distributed_ratelimit import SlidingWindowCounterRateLimiter

limiter = SlidingWindowCounterRateLimiter(
    redis_client,
    window_size=60000,  # 1 minute
    max_requests=100
)
```

### 2. Sliding Window Log
Best for: Precise rate limiting with exact timestamps
```python
from distributed_ratelimit import SlidingWindowLogRateLimiter

limiter = SlidingWindowLogRateLimiter(
    redis_client,
    window_size=60000,
    max_requests=100
)
```

### 3. Fixed Window
Best for: Simple, predictable rate limiting
```python
from distributed_ratelimit import FixedWindowRateLimiter

limiter = FixedWindowRateLimiter(
    redis_client,
    window_size=60000,
    max_requests=100
)
```

### 4. Token Bucket
Best for: Burst handling with smooth rate limiting
```python
from distributed_ratelimit import TokenBucketRateLimiter

limiter = TokenBucketRateLimiter(
    redis_client,
    capacity=100,
    refill_rate=10  # tokens per second
)
```

### 5. Leaky Bucket
Best for: Smooth, constant-rate limiting
```python
from distributed_ratelimit import LeakyBucketRateLimiter

limiter = LeakyBucketRateLimiter(
    redis_client,
    capacity=100,
    leak_rate=10  # requests per second
)
```

## Usage Example

```python
import redis
from distributed_ratelimit import SlidingWindowCounterRateLimiter

# Create Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Create rate limiter
limiter = SlidingWindowCounterRateLimiter(
    redis_client,
    window_size=60000,  # 1 minute
    max_requests=100
)

# Check if request is allowed
allowed, remaining, reset_time = limiter.allow_request("user123")
if allowed:
    # Process request
    print(f"Request allowed. {remaining} requests remaining.")
else:
    # Rate limit exceeded
    print(f"Rate limit exceeded. Try again in {reset_time}ms")
```

## Algorithm Comparison

| Algorithm | Pros | Cons | Best For |
|-----------|------|------|----------|
| Sliding Window Counter | Smooth limits, memory efficient | Slightly more complex | General purpose |
| Sliding Window Log | Precise, accurate | Higher memory usage | Precise timing needed |
| Fixed Window | Simple, predictable | Burst at window edges | Simple use cases |
| Token Bucket | Handles bursts well | More complex | Burst handling |
| Leaky Bucket | Smooth output rate | No burst handling | Constant rate needed |

## Redis Configuration

```python
redis_client = redis.Redis(
    host='your-redis-host',
    port=6379,
    db=0,
    password='your-password',
    decode_responses=True
)
```

## Error Handling

```python
try:
    allowed, remaining, reset_time = limiter.allow_request("user123")
except redis.ConnectionError:
    # Handle Redis connection error
    print("Redis connection error")
```

## Performance Considerations

- All algorithms use Redis Lua scripts for atomic operations
- Minimal network calls (one Redis call per request)
- Memory usage varies by algorithm
- Suitable for high-throughput applications

## License

MIT License 