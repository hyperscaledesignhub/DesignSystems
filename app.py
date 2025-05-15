# app.py

import yaml
import redis
import sys
import os
import time
import logging
from typing import Dict, Any, Optional
from distributed_ratelimit.sliding_window_counter import SlidingWindowCounterRateLimiter
from distributed_ratelimit.sliding_window_log import SlidingWindowLogRateLimiter
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path of the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the current directory to Python path
sys.path.insert(0, current_dir)

# Import rate limiters
from distributed_ratelimit import (
    FixedWindowRateLimiter,
    TokenBucketRateLimiter,
    LeakyBucketRateLimiter
)

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = os.getenv('CONFIG_PATH', '/app/config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        raise

class RateLimiterFactory:
    @staticmethod
    def create_rate_limiter(algorithm: str, redis_client, max_requests: int, algorithm_config: dict):
        if algorithm == "fixed_window":
            return FixedWindowRateLimiter(
                redis_client=redis_client,
                max_requests=max_requests,
                window_size_ms=algorithm_config['window_size']
            )
        elif algorithm == "sliding_window_counter":
            return SlidingWindowCounterRateLimiter(
                redis_client=redis_client,
                key="ratelimit:sliding",
                max_requests=max_requests,
                window_size_ms=algorithm_config['window_size'],
                precision_ms=algorithm_config['precision'],
                cleanup_interval_ms=algorithm_config['cleanup_interval'],
                overlap_factor=algorithm_config['overlap_factor']
            )
        elif algorithm == "sliding_window_log":
            return SlidingWindowLogRateLimiter(
                max_requests=max_requests,
                window_size_ms=algorithm_config['window_size'],
                redis_client=redis_client,
                precision=algorithm_config['precision'],
                overlap_factor=algorithm_config['overlap_factor']
            )
        elif algorithm == "token_bucket":
            return TokenBucketRateLimiter(
                redis_client=redis_client,
                capacity=max_requests,
                refill_rate=algorithm_config['refill_rate']
            )
        elif algorithm == "leaky_bucket":
            return LeakyBucketRateLimiter(
                redis_client=redis_client,
                capacity=max_requests,
                leak_rate=algorithm_config['leak_rate']
            )
        else:
            raise ValueError(f"Unknown rate limiter algorithm: {algorithm}")

    @staticmethod
    def get_rate_limit_method(rate_limiter):
        return rate_limiter.is_allowed

    @staticmethod
    def create_redis_client():
        """Create a Redis client."""
        redis_hosts = [
            os.environ.get('REDIS_HOST', 'redis'),  # Primary host
            'redis-service',  # K8s service name
            'localhost'  # Fallback for local dev
        ]
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        
        for host in redis_hosts:
            try:
                logger.info(f"Attempting to connect to Redis at {host}:{redis_port}")
                pool = redis.ConnectionPool(
                    host=host,
                    port=redis_port,
                    db=0,
                    socket_timeout=2,
                    socket_connect_timeout=2,
                    max_connections=10,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                redis_client = redis.Redis(connection_pool=pool)
                redis_client.ping()  # Test connection
                logger.info(f"Successfully connected to Redis at {host}:{redis_port}")
                return redis_client
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Redis connection failed for host {host}: {e}")
                continue
        
        logger.error("All Redis connection attempts failed. Using in-memory storage.")
        return None

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)
    
    # Load configuration
    config = load_config()
    rate_limiter_config = config['rate_limiter']
    
    # Create Redis client with retries
    redis_client = None
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        redis_client = RateLimiterFactory.create_redis_client()
        if redis_client is not None:
            break
        if attempt < max_retries - 1:
            logger.warning(f"Retrying Redis connection in {retry_delay} seconds (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
    
    if redis_client is None:
        logger.error("Failed to connect to Redis after all retries. Application will not start.")
        sys.exit(1)
    
    # Create rate limiter with proper parameters
    rate_limiter = RateLimiterFactory.create_rate_limiter(
        algorithm=rate_limiter_config['algorithm'],
        redis_client=redis_client,
        max_requests=rate_limiter_config['max_requests'],
        algorithm_config=rate_limiter_config['algorithms'][rate_limiter_config['algorithm']]
    )
    
    # Reset metrics for the current algorithm
    rate_limiter.metrics.reset_metrics(rate_limiter_config['algorithm'])
    
    # Initialize window size metric (only for window-based algorithms)
    if rate_limiter_config['algorithm'] in ['fixed_window', 'sliding_window_counter', 'sliding_window_log']:
        window_size_ms = rate_limiter_config['algorithms'][rate_limiter_config['algorithm']]['window_size']
        rate_limiter.metrics.window_size.labels(algorithm=rate_limiter_config['algorithm']).set(window_size_ms / 1000.0)
    else:
        # For token bucket and leaky bucket, set window size to 0 as they don't use windows
        rate_limiter.metrics.window_size.labels(algorithm=rate_limiter_config['algorithm']).set(0)
    
    # Log rate limiter configuration
    logger.info(f"Rate limiter configuration: {rate_limiter_config}")
    logger.info(f"Algorithm: {rate_limiter_config['algorithm']}")
    logger.info(f"Max requests: {rate_limiter_config['max_requests']}")
    logger.info(f"Algorithm config: {rate_limiter_config['algorithms'][rate_limiter_config['algorithm']]}")
    
    # Add Prometheus metrics endpoint
    @app.route('/metrics')
    def metrics():
        return Response(generate_latest(rate_limiter.metrics.get_registry()), mimetype=CONTENT_TYPE_LATEST)
    
    # Register rate limited endpoint
    @app.route('/api/limited')
    def limited_endpoint():
        start_time = time.time()
        client_id = request.headers.get('X-Client-ID')
        if client_id:
            logger.info(f"Using X-Client-ID header: {client_id}")
        else:
            client_id = request.remote_addr
            if 'X-Forwarded-For' in request.headers:
                client_id = request.headers['X-Forwarded-For'].split(',')[0].strip()
            logger.info(f"Using IP address as client_id: {client_id}")
        
        logger.info(f"Headers: {dict(request.headers)}")
        
        is_allowed, remaining, reset_time = RateLimiterFactory.get_rate_limit_method(rate_limiter)(client_id)
        
        # Update metrics
        if is_allowed == 0:  # Rate limited
            rate_limiter.metrics.requests_total.labels(status='rate_limited', algorithm=rate_limiter_config['algorithm']).inc()
            rate_limiter.metrics.rate_limited_requests.labels(algorithm=rate_limiter_config['algorithm']).inc()
            rate_limiter.metrics.current_requests.labels(algorithm=rate_limiter_config['algorithm']).set(0)
            logger.warning(f"Rate limit exceeded for {client_id}")
            response = jsonify({
                'error': 'Rate limit exceeded',
                'remaining': remaining,
                'reset_time': reset_time
            }), 429
        else:  # Allowed
            rate_limiter.metrics.requests_total.labels(status='success', algorithm=rate_limiter_config['algorithm']).inc()
            rate_limiter.metrics.current_requests.labels(algorithm=rate_limiter_config['algorithm']).set(rate_limiter_config['max_requests'] - remaining)
            logger.info(f"Request allowed for {client_id}")
            response = jsonify({
                'message': 'Request processed successfully',
                'remaining': remaining,
                'reset_time': reset_time
            })
        
        # Record request duration
        rate_limiter.metrics.request_duration.labels(algorithm=rate_limiter_config['algorithm']).observe(time.time() - start_time)
        
        return response
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
