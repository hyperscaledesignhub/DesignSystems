#!/Users/vijayabhaskarv/python-projects/venv/bin/python

import unittest
import time
import redis
from distributed_ratelimit.token_bucket import TokenBucketRateLimiter

class TestTokenBucketRateLimiterReal(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures with real Redis connection."""
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)  # Using localhost since Redis is port-forwarded
        self.capacity = 5
        self.refill_rate = 5  # 5 tokens per second
        self.limiter = TokenBucketRateLimiter(
            self.redis_client,
            capacity=self.capacity,
            refill_rate=self.refill_rate
        )
        self.identifier = "test_user_real"
        
        # Clear any existing state
        self.redis_client.delete(f"ratelimit:tokenbucket:{self.identifier}")
    
    def tearDown(self):
        """Clean up after tests."""
        self.redis_client.delete(f"ratelimit:tokenbucket:{self.identifier}")
    
    def test_initialization(self):
        """Test rate limiter initialization."""
        self.assertEqual(self.limiter.capacity, self.capacity)
        self.assertEqual(self.limiter.refill_rate, self.refill_rate)
    
    def test_allow_request_with_tokens(self):
        """Test allowing requests when tokens are available."""
        # First request should be allowed
        allowed, remaining, reset_time = self.limiter.is_allowed(self.identifier)
        self.assertTrue(allowed)
        self.assertEqual(remaining, self.capacity - 1)
        self.assertGreater(reset_time, int(time.time() * 1000))
    
    def test_allow_request_no_tokens(self):
        """Test rejecting requests when no tokens are available."""
        # Exhaust all tokens
        for _ in range(self.capacity):
            self.limiter.is_allowed(self.identifier)
        
        # Next request should be rejected
        allowed, remaining, reset_time = self.limiter.is_allowed(self.identifier)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(reset_time, int(time.time() * 1000))
    
    def test_token_refill(self):
        """Test that tokens are refilled at the correct rate."""
        # Exhaust all tokens
        for _ in range(self.capacity):
            self.limiter.is_allowed(self.identifier)
        
        # Wait for tokens to refill (1 second)
        time.sleep(1)
        
        # Should be able to make requests again
        allowed, remaining, _ = self.limiter.is_allowed(self.identifier)
        self.assertTrue(allowed)
        self.assertGreater(remaining, 0)
    
    def test_different_identifiers(self):
        """Test that different identifiers have independent limits."""
        identifier1 = "user1_real"
        identifier2 = "user2_real"
        
        # First identifier uses tokens
        for _ in range(self.capacity):
            self.limiter.is_allowed(identifier1)
        
        # Second identifier should have full capacity
        allowed, remaining, _ = self.limiter.is_allowed(identifier2)
        self.assertTrue(allowed)
        self.assertEqual(remaining, self.capacity - 1)
        
        # Clean up
        self.redis_client.delete(f"ratelimit:tokenbucket:{identifier1}")
        self.redis_client.delete(f"ratelimit:tokenbucket:{identifier2}")
    
    def test_concurrent_access(self):
        """Test concurrent access from multiple instances."""
        limiter2 = TokenBucketRateLimiter(
            self.redis_client,
            capacity=self.capacity,
            refill_rate=self.refill_rate
        )
        
        # First limiter uses tokens
        for _ in range(self.capacity - 1):
            self.limiter.is_allowed(self.identifier)
        
        # Second limiter should see the same state
        allowed, remaining, _ = limiter2.is_allowed(self.identifier)
        self.assertTrue(allowed)
        self.assertEqual(remaining, 0)

if __name__ == '__main__':
    unittest.main() 