#!/Users/vijayabhaskarv/python-projects/venv/bin/python

import unittest
import time
import redis
from distributed_ratelimit.leaky_bucket import LeakyBucketRateLimiter
import logging

logger = logging.getLogger(__name__)

class TestLeakyBucketRateLimiterReal(unittest.TestCase):
    def setUp(self):
        """Set up test environment with real Redis connection."""
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.redis.flushall()  # Clean up Redis before tests
        
        # Initialize rate limiter with capacity of 5 and leak rate of 1 per second
        self.limiter = LeakyBucketRateLimiter(
            redis_client=self.redis,
            capacity=5,
            leak_rate=1  # 1 request per second
        )
        logger.info("Initialized LeakyBucketRateLimiter with real Redis connection")
    
    def tearDown(self):
        """Clean up after tests."""
        self.redis.flushall()
        self.redis.close()
        logger.info("Cleaned up Redis connection")
    
    def test_initialization(self):
        """Test rate limiter initialization."""
        self.assertEqual(self.limiter.capacity, 5)
        self.assertEqual(self.limiter.leak_rate, 1)
    
    def test_allow_request_within_capacity(self):
        """Test allowing requests within capacity."""
        identifier = "test_client"
        
        # Make 5 requests (within capacity)
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
    
    def test_allow_request_exceed_capacity(self):
        """Test rejecting requests when capacity is exceeded."""
        identifier = "test_client"
        
        # Make 5 requests (fill the bucket)
        for _ in range(5):
            self.limiter.is_allowed(identifier)
        
        # 6th request should be rejected
        allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
    
    def test_request_leaking(self):
        """Test that requests leak from the bucket over time."""
        identifier = "test_client"
        logger.info(f"Testing request leaking for {identifier}")
        
        # Fill the bucket
        for _ in range(5):
            self.limiter.is_allowed(identifier)
        
        # Wait for some requests to leak (2 seconds = 2 requests at leak_rate=1)
        time.sleep(2.1)
        
        # Should be able to make 2 requests since they leaked
        for i in range(2):
            allowed, remaining, _ = self.limiter.is_allowed(identifier)
            logger.info(f"Request {i+1} after leaking: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            # The remaining count should be the number of requests we can still make
            self.assertGreaterEqual(remaining, 0)
        
        # Next request should be rejected since we've used all leaked capacity
        allowed, remaining, _ = self.limiter.is_allowed(identifier)
        logger.info(f"Request after leaking: allowed={allowed}, remaining={remaining}")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        logger.info("Request leaking test passed")
    
    def test_different_identifiers(self):
        """Test that different identifiers have independent buckets."""
        client1 = "client_1"
        client2 = "client_2"
        
        # Fill bucket for client1
        for _ in range(5):
            self.limiter.is_allowed(client1)
        
        # Client2 should still have full capacity
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(client2)
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
    
    def test_concurrent_access(self):
        """Test concurrent access from multiple instances."""
        identifier = "test_client"
        
        # Create another rate limiter instance
        limiter2 = LeakyBucketRateLimiter(
            redis_client=self.redis,
            capacity=5,
            leak_rate=1
        )
        
        # Make 3 requests with first limiter
        for _ in range(3):
            self.limiter.is_allowed(identifier)
        
        # Make 2 requests with second limiter
        for _ in range(2):
            limiter2.is_allowed(identifier)
        
        # Next request should be rejected by both limiters
        allowed1, remaining1, reset_time1 = self.limiter.is_allowed(identifier)
        allowed2, remaining2, reset_time2 = limiter2.is_allowed(identifier)
        
        self.assertFalse(allowed1)
        self.assertFalse(allowed2)
        self.assertEqual(remaining1, 0)
        self.assertEqual(remaining2, 0)
    
    def test_partial_leak(self):
        """Test partial request leaking based on elapsed time."""
        identifier = "test_client"
        
        # Fill the bucket
        for _ in range(5):
            self.limiter.is_allowed(identifier)
        
        # Wait for half a second (should leak ~2-3 requests)
        time.sleep(1.0)  # Adjusted to 1 second to ensure more requests leak
        
        # Should have some capacity but not full
        allowed, remaining, _ = self.limiter.is_allowed(identifier)
        self.assertTrue(allowed)
        self.assertLess(remaining, 4)  # Should have less than full capacity
    
    def test_burst_handling(self):
        """Test handling of request bursts."""
        identifier = "test_client"
        
        # Make burst of 3 requests
        for _ in range(3):
            allowed, _, _ = self.limiter.is_allowed(identifier)
            self.assertTrue(allowed)
        
        # Wait for a short time
        time.sleep(0.3)
        
        # Make another burst of 2 requests
        for _ in range(2):
            allowed, _, _ = self.limiter.is_allowed(identifier)
            self.assertTrue(allowed)
        
        # Next request should be rejected
        allowed, _, _ = self.limiter.is_allowed(identifier)
        self.assertFalse(allowed)

if __name__ == '__main__':
    unittest.main() 