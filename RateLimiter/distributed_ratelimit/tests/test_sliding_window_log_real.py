#!/Users/vijayabhaskarv/python-projects/venv/bin/python

import unittest
import time
import redis
import logging
from distributed_ratelimit.sliding_window_log import SlidingWindowLogRateLimiter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSlidingWindowLogRateLimiterReal(unittest.TestCase):
    def setUp(self):
        """Set up test environment with real Redis connection."""
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.redis.flushall()  # Clean up Redis before tests
        
        # Initialize rate limiter with 5 requests per second
        self.limiter = SlidingWindowLogRateLimiter(
            max_requests=5,
            window_size_ms=1000,  # 1 second window
            redis_client=self.redis
        )
        logger.info("Initialized SlidingWindowLogRateLimiter with real Redis connection")
    
    def tearDown(self):
        """Clean up after tests."""
        self.redis.flushall()
        self.redis.close()
        logger.info("Cleaned up Redis connection")
    
    def test_initialization(self):
        """Test rate limiter initialization."""
        logger.info("Testing rate limiter initialization")
        self.assertEqual(self.limiter.max_requests, 5)
        self.assertEqual(self.limiter.window_size_ms, 1000)
        logger.info("Initialization test passed")
    
    def test_allow_request_within_limit(self):
        """Test allowing requests within the limit."""
        identifier = "test_client"
        logger.info(f"Testing requests within limit for {identifier}")
        
        # Make 5 requests (within limit)
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
            logger.info(f"Request {i+1}: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        logger.info("Within limit test passed")
    
    def test_allow_request_exceed_limit(self):
        """Test rejecting requests when limit is exceeded."""
        identifier = "test_client"
        logger.info(f"Testing request limit exceeded for {identifier}")
        
        # Make 5 requests (within limit)
        for _ in range(5):
            self.limiter.is_allowed(identifier)
        
        # 6th request should be rejected
        allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
        logger.info(f"Exceeded limit request: allowed={allowed}, remaining={remaining}")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        logger.info("Exceed limit test passed")
    
    def test_window_sliding(self):
        """Test that old requests are removed from the window."""
        identifier = "test_client"
        logger.info(f"Testing window sliding for {identifier}")
        
        # Make 5 requests
        for _ in range(5):
            self.limiter.is_allowed(identifier)
        
        # Check Redis state before sliding
        current_count = self.redis.zcard(f"ratelimit:log:{identifier}")
        logger.info(f"Current request count before sliding: {current_count}")
        
        # Wait for window to slide (1 second)
        time.sleep(1.1)
        
        # Check Redis state after sliding
        new_count = self.redis.zcard(f"ratelimit:log:{identifier}")
        logger.info(f"Request count after sliding: {new_count}")
        
        # Should be able to make 5 more requests
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
            logger.info(f"Request {i+1} after sliding: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        logger.info("Window sliding test passed")
    
    def test_different_identifiers(self):
        """Test that different identifiers have independent limits."""
        client1 = "client_1"
        client2 = "client_2"
        logger.info(f"Testing independent limits for {client1} and {client2}")
        
        # Make 5 requests for client1
        for _ in range(5):
            self.limiter.is_allowed(client1)
        
        # Check Redis state for client1
        client1_count = self.redis.zcard(f"ratelimit:log:{client1}")
        logger.info(f"Client1 request count: {client1_count}")
        
        # Client2 should still be able to make requests
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(client2)
            logger.info(f"Client2 request {i+1}: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        
        # Check Redis state for client2
        client2_count = self.redis.zcard(f"ratelimit:log:{client2}")
        logger.info(f"Client2 request count: {client2_count}")
        logger.info("Independent limits test passed")
    
    def test_concurrent_access(self):
        """Test concurrent access from multiple instances."""
        identifier = "test_client"
        logger.info(f"Testing concurrent access for {identifier}")
        
        # Create another rate limiter instance
        limiter2 = SlidingWindowLogRateLimiter(
            max_requests=5,
            window_size_ms=1000,
            redis_client=self.redis
        )
        
        # Make 3 requests with first limiter
        for _ in range(3):
            self.limiter.is_allowed(identifier)
        
        # Check Redis state after first limiter
        count_after_first = self.redis.zcard(f"ratelimit:log:{identifier}")
        logger.info(f"Request count after first limiter: {count_after_first}")
        
        # Make 2 requests with second limiter
        for _ in range(2):
            limiter2.is_allowed(identifier)
        
        # Check Redis state after second limiter
        count_after_second = self.redis.zcard(f"ratelimit:log:{identifier}")
        logger.info(f"Request count after second limiter: {count_after_second}")
        
        # Next request should be rejected by both limiters
        allowed1, remaining1, reset_time1 = self.limiter.is_allowed(identifier)
        allowed2, remaining2, reset_time2 = limiter2.is_allowed(identifier)
        logger.info(f"First limiter check: allowed={allowed1}, remaining={remaining1}")
        logger.info(f"Second limiter check: allowed={allowed2}, remaining={remaining2}")
        
        self.assertFalse(allowed1)
        self.assertFalse(allowed2)
        self.assertEqual(remaining1, 0)
        self.assertEqual(remaining2, 0)
        logger.info("Concurrent access test passed")
    
    def test_partial_window(self):
        """Test requests in a partially filled window."""
        identifier = "test_client"
        logger.info(f"Testing partial window for {identifier}")
        
        # Make 3 requests
        for _ in range(3):
            self.limiter.is_allowed(identifier)
        
        # Check Redis state after initial requests
        initial_count = self.redis.zcard(f"ratelimit:log:{identifier}")
        logger.info(f"Request count after initial requests: {initial_count}")
        
        # Wait for half a window
        time.sleep(0.5)
        
        # Should be able to make 2 more requests
        for _ in range(2):
            allowed, remaining, _ = self.limiter.is_allowed(identifier)
            logger.info(f"Request in partial window: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
        
        # Check Redis state after partial window
        partial_count = self.redis.zcard(f"ratelimit:log:{identifier}")
        logger.info(f"Request count in partial window: {partial_count}")
        
        # Next request should be rejected
        allowed, remaining, _ = self.limiter.is_allowed(identifier)
        logger.info(f"Request after partial window: allowed={allowed}, remaining={remaining}")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        logger.info("Partial window test passed")
    
    def test_token_refill(self):
        """Test token refill behavior similar to EKS test."""
        identifier = "test_client"
        logger.info(f"Testing token refill for {identifier}")
        
        # Make 5 requests to exhaust the limit
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
            logger.info(f"Initial request {i+1}: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        
        # Verify rate limit is exceeded
        allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
        logger.info(f"Rate limited request: allowed={allowed}, remaining={remaining}")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        
        # Wait for 0.5 seconds (half window)
        logger.info("Waiting for 0.5 seconds...")
        time.sleep(0.5)
        
        # Try another request - should still be rate limited
        allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
        logger.info(f"Request after 0.5s: allowed={allowed}, remaining={remaining}")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        
        # Wait for full window reset
        logger.info("Waiting for another 0.6 seconds...")
        time.sleep(0.6)
        
        # Should be able to make requests again
        allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
        logger.info(f"Request after full window: allowed={allowed}, remaining={remaining}")
        self.assertTrue(allowed)
        self.assertEqual(remaining, 4)
        logger.info("Token refill test passed")

    async def _make_concurrent_request(self, identifier):
        """Helper method for making concurrent requests."""
        allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
        logger.info(f"Concurrent request: allowed={allowed}, remaining={remaining}")
        return allowed, remaining, reset_time

    def test_true_concurrent_access(self):
        """Test true concurrent access using asyncio."""
        import asyncio
        
        identifier = "test_concurrent_client"
        logger.info(f"Testing true concurrent access for {identifier}")
        
        # Create a list of concurrent requests
        async def run_concurrent_test():
            # Make 7 concurrent requests (5 should succeed, 2 should fail)
            tasks = [self._make_concurrent_request(identifier) for _ in range(7)]
            results = await asyncio.gather(*tasks)
            return results
            
        # Run the concurrent test
        results = asyncio.run(run_concurrent_test())
        
        # Count successes and failures
        success_count = sum(1 for allowed, _, _ in results if allowed)
        failure_count = sum(1 for allowed, _, _ in results if not allowed)
        
        logger.info(f"Concurrent test results:")
        logger.info(f"Successful requests: {success_count}")
        logger.info(f"Failed requests: {failure_count}")
        
        # Verify exactly 5 requests succeeded and 2 failed
        self.assertEqual(success_count, 5, "Expected exactly 5 successful requests")
        self.assertEqual(failure_count, 2, "Expected exactly 2 failed requests")
        
        # Verify all remaining counts are correct
        for i, (allowed, remaining, _) in enumerate(results):
            if allowed:
                expected_remaining = 4 - i if i < 5 else 0
                self.assertEqual(remaining, expected_remaining, 
                               f"Request {i+1} had incorrect remaining count")
            else:
                self.assertEqual(remaining, 0, 
                               f"Failed request {i+1} should have 0 remaining")
        
        logger.info("True concurrent access test passed")

if __name__ == '__main__':
    unittest.main() 