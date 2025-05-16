#!/usr/bin/env python3

import aiohttp
import asyncio
import logging
import time
from typing import Dict, List, Tuple
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
MAX_REQUESTS = 5  # Maximum requests per window
WINDOW_SIZE = 1.0  # Window size in seconds
BASE_URL = 'http://localhost:8080'

async def make_request(session: aiohttp.ClientSession, client_id: str) -> Tuple[int, Dict]:
    """Make a request to the rate limiter API."""
    try:
        headers = {"X-Client-ID": client_id}
        async with session.get(f"{BASE_URL}/api/limited", headers=headers) as response:
            data = await response.json()
            return response.status, data
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return 500, {"error": str(e)}

async def test_rate_limiter_429():
    """Test basic rate limiting behavior."""
    print(f"\nTesting Fixed Window Rate Limiter")
    print(f"Configuration: {MAX_REQUESTS} requests per {WINDOW_SIZE}s window")
    print(f"Endpoint: {BASE_URL}\n")

    client_id = "test_client_1"
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        print("Testing burst of requests...")
        # Make concurrent requests
        tasks = [make_request(session, client_id) for _ in range(MAX_REQUESTS + 1)]
        responses = await asyncio.gather(*tasks)
        
        # Check responses
        success_count = sum(1 for status, _ in responses if status == 200)
        rate_limited_count = sum(1 for status, _ in responses if status == 429)
        
        print(f"\nResults:")
        print(f"Successful requests: {success_count}")
        print(f"Rate limited requests: {rate_limited_count}")
        
        assert success_count == MAX_REQUESTS, f"Expected {MAX_REQUESTS} successful requests, got {success_count}"
        assert rate_limited_count > 0, "Expected at least one rate-limited request"

        # Test window reset
        print("\nTesting window reset...")
        wait_time = WINDOW_SIZE + 5.0  # Further increased waiting time for window reset
        print(f"Waiting {wait_time:.1f}s for window reset...")
        await asyncio.sleep(wait_time)
        
        # Try another request after reset
        status, data = await make_request(session, client_id)
        elapsed = time.time() - start_time
        print(f"Request after window reset at {elapsed:.3f}s: Status {status}, Response: {data}")
        assert status == 200, f"Expected 200 after reset, got {status}"

async def test_window_reset():
    """Test window reset behavior."""
    print(f"\nTesting window reset")
    client_id = "test_client_2"
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        # Make MAX_REQUESTS requests
        print("Making initial burst of requests...")
        for i in range(MAX_REQUESTS):
            status, data = await make_request(session, client_id)
            elapsed = time.time() - start_time
            print(f"Request {i+1} at {elapsed:.3f}s: Status {status}, Response: {data}")
            assert status == 200, f"Expected 200, got {status}"
            await asyncio.sleep(0.1)

        # Wait for window reset
        wait_time = WINDOW_SIZE + 5.0  # Further increased waiting time for window reset
        print(f"\nWaiting {wait_time:.1f}s for window reset...")
        await asyncio.sleep(wait_time)

        # Should be able to make requests again
        print("\nTesting requests after window reset...")
        for i in range(MAX_REQUESTS):
            status, data = await make_request(session, client_id)
            elapsed = time.time() - start_time
            print(f"Post-reset request {i+1} at {elapsed:.3f}s: Status {status}, Response: {data}")
            assert status == 200, f"Expected 200 after reset, got {status}"
            await asyncio.sleep(0.1)

async def test_concurrent_requests():
    """Test concurrent request handling."""
    print(f"\nTesting concurrent requests")
    client_id = "test_client_3"
    
    async with aiohttp.ClientSession() as session:
        # Make concurrent requests
        tasks = [make_request(session, client_id) for _ in range(MAX_REQUESTS + 2)]
        results = await asyncio.gather(*tasks)
        
        # Count results
        success_count = sum(1 for status, _ in results if status == 200)
        rate_limited_count = sum(1 for status, _ in results if status == 429)
        
        print(f"\nConcurrent requests results:")
        print(f"Successful requests: {success_count}")
        print(f"Rate limited requests: {rate_limited_count}")
        
        # Verify results
        assert success_count <= MAX_REQUESTS, f"Too many successful requests: {success_count}"
        assert rate_limited_count > 0, "Expected some requests to be rate limited"

async def test_multiple_clients():
    """Test rate limiting for multiple clients."""
    print("\nTesting multiple clients")
    clients = ["client_A", "client_B"]

    async with aiohttp.ClientSession() as session:
        for client_id in clients:
            print(f"\nTesting {client_id}:")
            # Make concurrent requests
            tasks = [make_request(session, client_id) for _ in range(MAX_REQUESTS + 1)]
            responses = await asyncio.gather(*tasks)
            
            # Check responses
            success_count = sum(1 for status, _ in responses if status == 200)
            rate_limited_count = sum(1 for status, _ in responses if status == 429)
            
            print(f"Results for {client_id}:")
            print(f"Successful requests: {success_count}")
            print(f"Rate limited requests: {rate_limited_count}")
            
            assert success_count == MAX_REQUESTS, f"Expected {MAX_REQUESTS} successful requests, got {success_count}"
            assert rate_limited_count > 0, "Expected at least one rate-limited request"
            
            # Wait before testing next client
            await asyncio.sleep(WINDOW_SIZE + 0.1)

if __name__ == "__main__":
    print("Starting Fixed Window Rate Limiter Tests...")
    
    # Run all tests
    asyncio.run(test_rate_limiter_429())
    asyncio.run(test_window_reset())
    asyncio.run(test_concurrent_requests())
    asyncio.run(test_multiple_clients())
    
    print("\nAll tests completed successfully!") 