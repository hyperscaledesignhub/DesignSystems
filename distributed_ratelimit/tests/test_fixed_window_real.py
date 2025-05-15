#!/Users/vijayabhaskarv/python-projects/venv/bin/python

import unittest
import time
import redis
import logging
from distributed_ratelimit.fixed_window import FixedWindowRateLimiter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestFixedWindowRateLimiterReal(unittest.TestCase):
    def setUp(self):
        """Set up test environment with real Redis connection."""
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.redis.flushall()  # Clean up Redis before tests
        
        # Initialize rate limiter with 5 requests per second
        self.limiter = FixedWindowRateLimiter(
            max_requests=5,
            window_size_ms=1000,  # 1 second window
            redis_client=self.redis
        )
        logger.info("Initialized FixedWindowRateLimiter with real Redis connection")
    
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
        """Test allowing requests within the window limit."""
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
        """Test rejecting requests when window limit is exceeded."""
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
    
    def test_window_reset(self):
        """Test that window resets after window_size duration."""
        identifier = "test_client"
        logger.info(f"Testing window reset for {identifier}")
        
        # Make 5 requests
        for _ in range(5):
            self.limiter.is_allowed(identifier)
        
        # Wait for window to reset (1 second)
        time.sleep(1.1)
        
        # Should be able to make 5 more requests
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(identifier)
            logger.info(f"Request {i+1} after reset: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        logger.info("Window reset test passed")
    
    def test_different_identifiers(self):
        """Test that different identifiers have independent windows."""
        client1 = "client_1"
        client2 = "client_2"
        logger.info(f"Testing independent limits for {client1} and {client2}")
        
        # Make 5 requests for client1
        for _ in range(5):
            self.limiter.is_allowed(client1)
        
        # Client2 should still be able to make requests
        for i in range(5):
            allowed, remaining, reset_time = self.limiter.is_allowed(client2)
            logger.info(f"Client2 request {i+1}: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        logger.info("Independent limits test passed")
    
    def test_concurrent_access(self):
        """Test concurrent access from multiple instances."""
        identifier = "test_client"
        logger.info(f"Testing concurrent access for {identifier}")
        
        # Create another rate limiter instance
        limiter2 = FixedWindowRateLimiter(
            max_requests=5,
            window_size_ms=1000,
            redis_client=self.redis
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
        logger.info(f"First limiter check: allowed={allowed1}, remaining={remaining1}")
        logger.info(f"Second limiter check: allowed={allowed2}, remaining={remaining2}")
        
        self.assertFalse(allowed1)
        self.assertFalse(allowed2)
        self.assertEqual(remaining1, 0)
        self.assertEqual(remaining2, 0)
        logger.info("Concurrent access test passed")
    
    def test_window_boundary(self):
        """Test requests at window boundaries."""
        identifier = "test_client"
        logger.info(f"Testing window boundary for {identifier}")
        
        # Make 5 requests in current window
        for i in range(5):
            allowed, remaining, _ = self.limiter.is_allowed(identifier)
            logger.info(f"Request {i+1}: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        
        # Next request should be rejected
        allowed, remaining, _ = self.limiter.is_allowed(identifier)
        logger.info(f"Extra request: allowed={allowed}, remaining={remaining}")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be able to make 5 new requests
        for i in range(5):
            allowed, remaining, _ = self.limiter.is_allowed(identifier)
            logger.info(f"Request {i+1} after reset: allowed={allowed}, remaining={remaining}")
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5 - (i + 1))
        logger.info("Window boundary test passed")

if __name__ == '__main__':
    unittest.main() 