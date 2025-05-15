#!/usr/bin/env python3

import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Tuple
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = 'http://localhost:8080'
ENDPOINT = f"{BASE_URL}/api/limited"
MAX_REQUESTS = 5
WINDOW_SIZE = 1.0  # seconds

class Response:
    def __init__(self, status, data, timestamp):
        self.status = status
        self.data = data
        self.timestamp = timestamp
        self.remaining = data.get('remaining') if data else None
        self.reset_time = data.get('reset_time') if data else None

async def make_request(session, client_id):
    start_time = time.time()
    try:
        headers = {'X-Client-ID': client_id}
        async with session.get(ENDPOINT, headers=headers) as response:
            data = await response.json()
            return Response(response.status, data, start_time)
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None

async def test_sliding_window_log_basic():
    logger.info("Starting Sliding Window Log Rate Limiter Tests")
    logger.info(f"Configuration: {MAX_REQUESTS} requests per {WINDOW_SIZE}s window")
    logger.info(f"Testing against endpoint: {ENDPOINT}\n")

    client_id = f"test_client_{int(time.time() * 1000)}"
    responses = []

    async with aiohttp.ClientSession() as session:
        # Make initial requests concurrently
        initial_tasks = [make_request(session, client_id) for _ in range(MAX_REQUESTS)]
        initial_responses = await asyncio.gather(*initial_tasks)
        responses.extend([r for r in initial_responses if r])

        # Verify all initial requests were successful
        assert all(r.status == 200 for r in responses), \
            "All initial requests should be successful"
        assert len(responses) == MAX_REQUESTS, \
            f"Expected {MAX_REQUESTS} successful requests, got {len(responses)}"

        # Try one more request immediately (should be rate limited)
        extra_response = await make_request(session, client_id)
        if extra_response:
            responses.append(extra_response)
            assert extra_response.status == 429, "Request should be rate limited after limit reached"
            assert extra_response.remaining == 0, "Rate limited request should show 0 remaining"

        # Wait for window to reset
        await asyncio.sleep(WINDOW_SIZE + 5.0)  # Add extra buffer for safety

        # Try another request (should succeed)
        final_response = await make_request(session, client_id)
        if final_response:
            responses.append(final_response)
            assert final_response.status == 200, "Request after reset should succeed"
            assert final_response.remaining == MAX_REQUESTS - 1, \
                f"Expected {MAX_REQUESTS - 1} remaining after reset, got {final_response.remaining}"

    # Log all responses
    for resp in responses:
        time_offset = resp.timestamp - responses[0].timestamp
        logger.info(f"\nResponse received at {time_offset:.3f}s:")
        logger.info(f"  Client ID: {client_id}")
        logger.info(f"  Status Code: {resp.status}")
        logger.info(f"  Response Data: {resp.data}")
        logger.info(f"  Remaining Requests: {resp.remaining}")
        if resp.reset_time:
            reset_in = (resp.reset_time / 1000 - time.time())
            logger.info(f"  Reset Time: {resp.reset_time} (in {reset_in:.3f}s)")

    # Analyze results by time windows
    logger.info("\nAnalyzing results by time windows:")
    window_responses = {}
    first_timestamp = responses[0].timestamp

    for resp in responses:
        window_num = int((resp.timestamp - first_timestamp) / WINDOW_SIZE)
        if window_num not in window_responses:
            window_responses[window_num] = []
        window_responses[window_num].append(resp)

    for window_num, window_resps in window_responses.items():
        logger.info(f"\nWindow {window_num + 1}:")
        success_count = sum(1 for r in window_resps if r.status == 200)
        rate_limited_count = sum(1 for r in window_resps if r.status == 429)
        window_duration = max(r.timestamp for r in window_resps) - min(r.timestamp for r in window_resps)
        
        logger.info(f"  Requests in window: {len(window_resps)}")
        logger.info(f"  Successful requests: {success_count}")
        logger.info(f"  Rate limited requests: {rate_limited_count}")
        logger.info(f"  Window duration: {window_duration:.3f}s")
        
        # Verify rate limiting is working
        assert success_count <= MAX_REQUESTS, f"Window {window_num + 1} exceeded rate limit"
        if window_num == 0:
            assert success_count == MAX_REQUESTS, f"Initial window should allow exactly {MAX_REQUESTS} requests"
            assert rate_limited_count > 0, "Should have at least one rate-limited request after limit reached"

async def test_sliding_window_log_concurrent():
    """Test concurrent access with multiple clients"""
    logging.root.info("\nTesting concurrent access with multiple clients")
    
    async with aiohttp.ClientSession() as session:
        client_id = f"concurrent_client_0_{int(time.time() * 1000)}"
        
        # Make initial burst of MAX_REQUESTS requests concurrently
        initial_tasks = [make_request(session, client_id) for _ in range(MAX_REQUESTS)]
        initial_responses = await asyncio.gather(*initial_tasks)
        
        # Verify all initial requests were successful
        assert all(r.status == 200 for r in initial_responses), \
            "All initial requests should be successful"
        assert len(initial_responses) == MAX_REQUESTS, \
            f"Expected {MAX_REQUESTS} successful requests, got {len(initial_responses)}"
        
        # Small delay to ensure all initial requests are processed
        await asyncio.sleep(0.1)
        
        # Make two concurrent requests that should both be rate limited
        extra_tasks = [make_request(session, client_id) for _ in range(2)]
        extra_responses = await asyncio.gather(*extra_tasks)
        
        # Verify these requests are rate limited
        for resp in extra_responses:
            assert resp.status == 429, "Request should be rate limited"
            assert resp.remaining == 0, "Rate limited request should show 0 remaining"
        
        # Wait for window reset
        await asyncio.sleep(WINDOW_SIZE + 5.0)
        
        # Try one more request that should succeed
        reset_response = await make_request(session, client_id)
        assert reset_response.status == 200, "Request after reset should succeed"
        assert reset_response.remaining == MAX_REQUESTS - 1, \
            f"Expected {MAX_REQUESTS - 1} remaining after reset, got {reset_response.remaining}"
        
        logging.info(f"\nResults for {client_id}:")
        logging.info("  All tests passed successfully!")

async def test_sliding_window_log_window_reset():
    """Test that the rate limit window resets correctly after the specified duration."""
    print("\nTesting window reset with parallel requests...")
    client_id = f"reset_test_client_{int(time.time() * 1000)}"
    print(f"\nClient ID: {client_id}")

    async with aiohttp.ClientSession() as session:
        # Make initial burst of requests
        print("\nMaking initial burst of requests...")
        initial_tasks = []
        for i in range(MAX_REQUESTS):
            initial_tasks.append(make_request(session, client_id))
            # Small delay between requests to spread them across the window
            await asyncio.sleep(0.05)
        
        initial_responses = await asyncio.gather(*initial_tasks)
        
        # Track request timestamps and reset times
        request_times = []
        for resp in initial_responses:
            assert resp.status == 200, f"Expected 200 OK for initial requests, got {resp.status}"
            request_times.append((resp.timestamp, resp.reset_time))
            print(f"Initial request at {resp.timestamp:.3f}: Status={resp.status}, Remaining={resp.remaining}, Reset={resp.reset_time}")
        
        # Make one more request that should be rate limited
        print("\nMaking request after limit reached...")
        result = await make_request(session, client_id)
        assert result.status == 429, f"Expected 429 Too Many Requests after limit reached, got {result.status}"
        print(f"Rate limited request: Status={result.status}, Remaining={result.remaining}, Reset={result.reset_time}")

        # Wait for window reset
        await asyncio.sleep(WINDOW_SIZE + 5.0)
        
        # Try another request that should succeed
        print("\nMaking request after window reset...")
        reset_response = await make_request(session, client_id)
        assert reset_response.status == 200, "Request after reset should succeed"
        print(f"Post-reset request: Status={reset_response.status}, Remaining={reset_response.remaining}, Reset={reset_response.reset_time}")

if __name__ == "__main__":
    print("Starting Sliding Window Log Rate Limiter Tests...")
    
    # Run all tests
    asyncio.run(test_sliding_window_log_basic())
    asyncio.run(test_sliding_window_log_concurrent())
    asyncio.run(test_sliding_window_log_window_reset())
    
    print("\nAll tests completed successfully!") 