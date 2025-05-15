#!/Users/vijayabhaskarv/python-projects/venv/bin/python

import unittest
import time
import redis
from distributed_ratelimit.sliding_window_counter import SlidingWindowCounterRateLimiter
import logging

logger = logging.getLogger(__name__)

class TestSlidingWindowCounterRateLimiter(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.redis_client.flushall()  # Clear Redis before each test
        
        # Create rate limiter with small window for testing
        self.rate_limiter = SlidingWindowCounterRateLimiter(
            redis_client=self.redis_client,
            key="test:ratelimit",
            max_requests=5,
            window_size_ms=1000,  # 1 second window
            precision_ms=100,
            cleanup_interval_ms=1000,
            overlap_factor=0.6
        )

    def test_allow_request_within_limit(self):
        """Test that requests within the limit are allowed."""
        for i in range(4):
            allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
            self.assertTrue(allowed)
            time.sleep(0.1)

    def test_allow_request_exceed_limit(self):
        """Test that requests exceeding the limit are not allowed (allowing for sliding window approximation)."""
        allowed_results = []
        for i in range(6):  # Allow up to 6 requests
            allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
            allowed_results.append(allowed)
            time.sleep(0.1)
        # At least the 7th request must be denied
        allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
        self.assertFalse(allowed)
        # At least 5 of the first 6 must be allowed
        self.assertGreaterEqual(sum(allowed_results), 5)

    def test_reset_after_window(self):
        """Test that the rate limit resets after the window expires."""
        for i in range(5):
            self.rate_limiter.is_allowed("test_client")
            time.sleep(0.1)
        time.sleep(1.1)
        allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
        self.assertTrue(allowed)

    def test_different_identifiers(self):
        """Test that different identifiers have separate rate limits."""
        for i in range(5):
            allowed, remaining, reset_time = self.rate_limiter.is_allowed("client1")
            self.assertTrue(allowed)
            time.sleep(0.1)
        allowed, remaining, reset_time = self.rate_limiter.is_allowed("client2")
        self.assertTrue(allowed)

    def test_concurrent_access(self):
        """Test concurrent access from multiple clients."""
        import threading

        def make_requests(client_id):
            for _ in range(3):
                allowed, remaining, reset_time = self.rate_limiter.is_allowed(f"client_{client_id}")
                time.sleep(0.1)

        # Create 3 threads making requests
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_requests, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check final state
        allowed, remaining, reset_time = self.rate_limiter.is_allowed("client_0")
        self.assertTrue(allowed)  # Should still have some requests left
        self.assertGreater(remaining, 0)

    def test_partial_window(self):
        """Test rate limiting with partial window overlap (allowing for sliding window approximation)."""
        allowed_results = []
        for i in range(4):
            allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
            allowed_results.append(allowed)
            time.sleep(0.1)
        time.sleep(0.5)
        allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
        allowed_results.append(allowed)
        allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
        # Allow for one extra request before denying
        if allowed:
            allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
            self.assertFalse(allowed)
        else:
            self.assertFalse(allowed)
        time.sleep(1.0)
        allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
        self.assertTrue(allowed)

    def test_cleanup(self):
        """Test that old requests are cleaned up."""
        for i in range(3):
            self.rate_limiter.is_allowed("test_client")
            time.sleep(0.1)
        time.sleep(1.1)
        for i in range(3):
            allowed, remaining, reset_time = self.rate_limiter.is_allowed("test_client")
            self.assertTrue(allowed)
            time.sleep(0.1)

if __name__ == '__main__':
    unittest.main() 