from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, REGISTRY
import time
import logging

logger = logging.getLogger(__name__)

# Token Bucket specific metrics
TOKEN_BUCKET_TOKENS = Gauge(
    'token_bucket_tokens',
    'Current number of tokens in the bucket',
    ['client_id']
)

TOKEN_BUCKET_CAPACITY = Gauge(
    'token_bucket_capacity',
    'Maximum capacity of the token bucket',
    ['client_id']
)

TOKEN_BUCKET_REFILL_RATE = Gauge(
    'token_bucket_refill_rate',
    'Token refill rate per second',
    ['client_id']
)

TOKEN_BUCKET_REQUESTS_TOTAL = Counter(
    'token_bucket_requests_total',
    'Total number of requests processed',
    ['client_id', 'status']
)

TOKEN_BUCKET_WAIT_TIME = Histogram(
    'token_bucket_wait_time_seconds',
    'Time until next token availability',
    ['client_id'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

# Fixed Window specific metrics
FIXED_WINDOW_RESETS = Gauge(
    'fixed_window_resets_total',
    'Total number of window resets in fixed window rate limiter',
    ['client_id']
)

FIXED_WINDOW_REJECTIONS = Gauge(
    'fixed_window_rejections_total',
    'Total number of rejected requests in fixed window rate limiter',
    ['client_id']
)

FIXED_WINDOW_TIME_UNTIL_RESET = Gauge(
    'fixed_window_time_until_reset_seconds',
    'Time remaining until window reset in fixed window rate limiter',
    ['client_id']
)

# New Fixed Window metrics
WINDOW_UTILIZATION = Gauge(
    'fixed_window_utilization_percent',
    'Percentage of window capacity being used',
    ['client_id']
)

WINDOW_BURST_SIZE = Gauge(
    'fixed_window_burst_size',
    'Maximum number of requests in a single burst',
    ['client_id']
)

CONSECUTIVE_REJECTIONS = Counter(
    'fixed_window_consecutive_rejections',
    'Number of consecutive rejections for a client',
    ['client_id']
)

ERROR_COUNTER = Counter(
    'fixed_window_errors_total',
    'Total number of errors in fixed window rate limiter',
    ['client_id', 'error_type']
)

WINDOW_TRANSITION_TIME = Histogram(
    'fixed_window_transition_time_seconds',
    'Time taken for window transitions',
    ['client_id']
)

# Global metrics instance
_metrics_instance = None
_metrics_registry = None

class RateLimiterMetrics:
    """Metrics for rate limiter implementations."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RateLimiterMetrics, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize metrics for rate limiter.
        Uses singleton pattern to ensure metrics are only created once.
        """
        if RateLimiterMetrics._initialized:
            return
            
        logger.info("Initializing rate limiter metrics")
        
        # Counter for total requests by status and algorithm
        self.requests_total = Counter(
            'rate_limiter_requests_total',
            'Total number of requests',
            ['status', 'algorithm']  # status can be: success, rate_limited, error
        )
        
        # Counter specifically for rate-limited requests
        self.rate_limited_requests = Counter(
            'rate_limiter_rate_limited_total',
            'Total number of rate-limited requests',
            ['algorithm']
        )
        
        # Counter for cleanup operations
        self.sliding_window_counter_cleanup_operations = Counter(
            'sliding_window_counter_cleanup_operations_total',
            'Total number of cleanup operations performed',
            ['algorithm']
        )
        
        # Counter for requests removed during cleanup
        self.sliding_window_counter_requests_removed = Counter(
            'sliding_window_counter_requests_removed_total',
            'Total number of requests removed during cleanup',
            ['algorithm']
        )
        
        # Gauge for window utilization
        self.sliding_window_counter_utilization = Gauge(
            'sliding_window_counter_utilization',
            'Current window utilization as a ratio',
            ['algorithm']
        )
        
        # Gauge for current number of requests in the window
        self.current_requests = Gauge(
            'rate_limiter_current_requests',
            'Current number of requests in the window',
            ['algorithm']
        )
        
        # Gauge for window size in seconds
        self.window_size = Gauge(
            'rate_limiter_window_size_seconds',
            'Size of the rate limiting window in seconds',
            ['algorithm']
        )
        
        # Gauge for precision in milliseconds
        self.precision = Gauge(
            'rate_limiter_precision_ms',
            'Precision of the rate limiting window in milliseconds',
            ['algorithm']
        )
        
        # Gauge for window overlap
        self.window_overlap = Gauge(
            'rate_limiter_window_overlap',
            'Overlap factor between consecutive windows',
            ['algorithm']
        )
        
        # Token Bucket specific metrics
        self.token_bucket_accepted_requests = Counter(
            'token_bucket_accepted_requests_total',
            'Total number of accepted requests in token bucket',
            ['algorithm']
        )
        
        self.token_bucket_rejected_requests = Counter(
            'token_bucket_rejected_requests_total',
            'Total number of rejected requests in token bucket',
            ['algorithm']
        )
        
        self.token_bucket_tokens_consumed = Counter(
            'token_bucket_tokens_consumed_total',
            'Total number of tokens consumed in token bucket',
            ['algorithm']
        )
        
        self.token_bucket_acceptance_rate = Gauge(
            'token_bucket_acceptance_rate',
            'Rate of accepted requests in token bucket',
            ['algorithm']
        )
        
        self.token_bucket_fill_level = Gauge(
            'token_bucket_fill_level',
            'Current fill level of the token bucket',
            ['algorithm']
        )
        
        self.token_bucket_rejection_rate = Gauge(
            'token_bucket_rejection_rate',
            'Rate of rejected requests in token bucket',
            ['algorithm']
        )
        
        self.token_bucket_avg_tokens_per_request = Gauge(
            'token_bucket_avg_tokens_per_request',
            'Average number of tokens consumed per request in token bucket',
            ['algorithm']
        )

        # Leaky Bucket specific metrics
        self.leaky_bucket_leak_rate = Gauge(
            'leaky_bucket_leak_rate',
            'Current leak rate of the bucket (requests per second)',
            ['algorithm']
        )

        self.leaky_bucket_actual_leak_rate = Gauge(
            'leaky_bucket_actual_leak_rate',
            'Actual observed leak rate (requests leaked per second)',
            ['algorithm']
        )

        self.leaky_bucket_queue_size = Gauge(
            'leaky_bucket_queue_size',
            'Current number of requests in the queue',
            ['algorithm']
        )

        self.leaky_bucket_queue_utilization = Gauge(
            'leaky_bucket_queue_utilization',
            'Percentage of queue capacity being used',
            ['algorithm']
        )

        self.leaky_bucket_time_since_last_leak = Gauge(
            'leaky_bucket_time_since_last_leak_seconds',
            'Time elapsed since last leak operation',
            ['algorithm']
        )

        self.leaky_bucket_time_until_next_leak = Gauge(
            'leaky_bucket_time_until_next_leak_seconds',
            'Estimated time until next leak operation',
            ['algorithm']
        )

        self.leaky_bucket_burst_size = Gauge(
            'leaky_bucket_burst_size',
            'Size of the current request burst',
            ['algorithm']
        )

        self.leaky_bucket_consecutive_rejections = Counter(
            'leaky_bucket_consecutive_rejections_total',
            'Number of consecutive rejections',
            ['algorithm']
        )

        self.leaky_bucket_leaks_total = Counter(
            'leaky_bucket_leaks_total',
            'Total number of leak operations performed',
            ['algorithm']
        )

        self.leaky_bucket_requests_leaked = Counter(
            'leaky_bucket_requests_leaked_total',
            'Total number of requests leaked',
            ['algorithm']
        )

        self.leaky_bucket_queue_availability = Gauge(
            'leaky_bucket_queue_availability',
            'Percentage of time queue was available for new requests',
            ['algorithm']
        )

        self.leaky_bucket_queue_blocked_time = Counter(
            'leaky_bucket_queue_blocked_time_seconds',
            'Total time queue was blocked (full)',
            ['algorithm']
        )
        
        # Histogram for request processing duration
        self.request_duration = Histogram(
            'rate_limiter_request_duration_seconds',
            'Time taken to process rate limit requests',
            ['algorithm'],
            buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
        )
        
        # Sliding Window Log specific metrics
        self.sliding_window_utilization = Gauge(
            'sliding_window_log_utilization',
            'Current utilization of the sliding window',
            ['algorithm']
        )
        
        self.window_cleanup_operations = Counter(
            'sliding_window_log_cleanup_operations',
            'Number of window cleanup operations performed',
            ['algorithm']
        )
        
        self.requests_removed = Counter(
            'sliding_window_log_requests_removed',
            'Number of requests removed during cleanup',
            ['algorithm']
        )
        
        self.request_distribution = Histogram(
            'sliding_window_log_request_distribution',
            'Distribution of requests across the window',
            ['algorithm'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # Sliding Window Counter specific metrics
        self.sliding_window_counter_overlap = Gauge(
            'sliding_window_counter_overlap',
            'Current overlap between consecutive windows',
            ['algorithm']
        )
        
        self.sliding_window_counter_precision = Gauge(
            'sliding_window_counter_precision_ms',
            'Precision of the rate limiting window in milliseconds',
            ['algorithm']
        )
        
        self.sliding_window_counter_request_distribution = Histogram(
            'sliding_window_counter_request_distribution',
            'Distribution of requests across the window',
            ['algorithm'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        RateLimiterMetrics._initialized = True
        logger.info("Rate limiter metrics initialized successfully")
    
    def reset_metrics(self, algorithm: str):
        """Reset all metrics for a given algorithm."""
        logger.info(f"Resetting metrics for {algorithm}")
        
        # Reset request counters
        self.requests_total.labels(status='success', algorithm=algorithm)._value.set(0)
        self.requests_total.labels(status='rate_limited', algorithm=algorithm)._value.set(0)
        self.requests_total.labels(status='error', algorithm=algorithm)._value.set(0)
        
        # Reset rate limited requests
        self.rate_limited_requests.labels(algorithm=algorithm)._value.set(0)
        
        # Reset current requests
        self.current_requests.labels(algorithm=algorithm).set(0)
        
        # Reset window utilization
        self.sliding_window_counter_utilization.labels(algorithm=algorithm).set(0)
        
        # Reset cleanup operations
        self.sliding_window_counter_cleanup_operations.labels(algorithm=algorithm)._value.set(0)
        
        # Reset requests removed
        self.sliding_window_counter_requests_removed.labels(algorithm=algorithm)._value.set(0)
        
        # Reset window overlap
        self.sliding_window_counter_overlap.labels(algorithm=algorithm).set(0)
        
        # Reset request duration histogram
        self._reset_request_duration_histogram(algorithm)
        
        logger.info(f"Metrics reset complete for {algorithm}")
    
    def _reset_request_duration_histogram(self, algorithm: str):
        """Reset request duration histogram metrics for a given algorithm."""
        # Reset the sum of the histogram
        self.request_duration.labels(algorithm=algorithm)._sum.set(0)
        
        # Reset all buckets
        for bucket in self.request_duration.labels(algorithm=algorithm)._buckets:
            if isinstance(bucket, (int, float)):
                self.request_duration.labels(algorithm=algorithm)._buckets[bucket].set(0)
    
    def get_registry(self):
        """Get the Prometheus registry containing all metrics."""
        return REGISTRY

def update_fixed_window_metrics(client_id: str, resets: int, rejections: int, time_until_reset: float,
                              burst_size: int = 0, consecutive_rejections: int = 0, utilization: float = 0):
    """Update fixed window specific metrics for a client."""
    # Initialize metrics if they don't exist
    if client_id not in FIXED_WINDOW_RESETS._metrics:
        FIXED_WINDOW_RESETS.labels(client_id=client_id).set(0)
    if client_id not in FIXED_WINDOW_REJECTIONS._metrics:
        FIXED_WINDOW_REJECTIONS.labels(client_id=client_id).set(0)
    if client_id not in FIXED_WINDOW_TIME_UNTIL_RESET._metrics:
        FIXED_WINDOW_TIME_UNTIL_RESET.labels(client_id=client_id).set(0)
    if client_id not in WINDOW_UTILIZATION._metrics:
        WINDOW_UTILIZATION.labels(client_id=client_id).set(0)
    if client_id not in WINDOW_BURST_SIZE._metrics:
        WINDOW_BURST_SIZE.labels(client_id=client_id).set(0)
    if client_id not in CONSECUTIVE_REJECTIONS._metrics:
        CONSECUTIVE_REJECTIONS.labels(client_id=client_id)._value.set(0)
    
    # Update metrics
    FIXED_WINDOW_RESETS.labels(client_id=client_id).set(resets)
    FIXED_WINDOW_REJECTIONS.labels(client_id=client_id).set(rejections)
    FIXED_WINDOW_TIME_UNTIL_RESET.labels(client_id=client_id).set(time_until_reset)
    WINDOW_UTILIZATION.labels(client_id=client_id).set(utilization)
    WINDOW_BURST_SIZE.labels(client_id=client_id).set(burst_size)
    CONSECUTIVE_REJECTIONS.labels(client_id=client_id)._value.set(consecutive_rejections)
    
    logger.info(f"Updated fixed window metrics for {client_id}: "
                f"resets={resets}, rejections={rejections}, time_until_reset={time_until_reset}s, "
                f"burst_size={burst_size}, consecutive_rejections={consecutive_rejections}, "
                f"utilization={utilization}%")

def update_token_metrics(client_id: str, current_tokens: float, capacity: int, refill_rate: float):
    """Update token bucket metrics for a client."""
    TOKEN_BUCKET_TOKENS.labels(client_id=client_id).set(current_tokens)
    TOKEN_BUCKET_CAPACITY.labels(client_id=client_id).set(capacity)
    TOKEN_BUCKET_REFILL_RATE.labels(client_id=client_id).set(refill_rate)

def record_request(client_id: str, allowed: bool):
    """Record request outcome."""
    status = 'allowed' if allowed else 'rejected'
    TOKEN_BUCKET_REQUESTS_TOTAL.labels(client_id=client_id, status=status).inc()

def record_wait_time(client_id: str, wait_time: float):
    """Record wait time until next token."""
    TOKEN_BUCKET_WAIT_TIME.labels(client_id=client_id).observe(wait_time) 