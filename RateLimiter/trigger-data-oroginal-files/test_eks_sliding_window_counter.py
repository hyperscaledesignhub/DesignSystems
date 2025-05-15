#!/usr/bin/env python3

import requests
import time
import logging
from typing import Dict, Any
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = 'http://localhost:8080'
MAX_REQUESTS = 5  # Maximum requests allowed per window (matching config.yaml)
WINDOW_SIZE = 5.0  # Window size in seconds (matching config.yaml)
PRECISION = 1.0  # Precision in seconds (matching config.yaml)
CLEANUP_INTERVAL = 30.0  # Cleanup interval in seconds (matching config.yaml)
OVERLAP_FACTOR = 0.5  # Overlap factor (matching config.yaml)
NETWORK_LATENCY = 0.05  # 50ms network latency

def make_request(client_id: str) -> Dict[str, Any]:
    """Make a request to the rate-limited endpoint."""
    headers = {"X-Client-ID": client_id}
    response = requests.get(f"{BASE_URL}/api/limited", headers=headers)
    return {
        "status_code": response.status_code,
        "data": response.json() if response.status_code == 200 else None,
        "error": response.json() if response.status_code == 429 else None
    }

def test_rate_limiting():
    """Test rate limiting behavior of the endpoint."""
    client_id = f"test_client_{int(time.time())}"
    responses = []
    
    logger.info(f"\nTesting rate limiting for client {client_id}")
    logger.info(f"Max requests allowed: {MAX_REQUESTS}")
    logger.info(f"Window size: {WINDOW_SIZE} seconds")
    logger.info(f"Precision: {PRECISION} seconds")
    logger.info(f"Cleanup interval: {CLEANUP_INTERVAL} seconds")
    logger.info(f"Overlap factor: {OVERLAP_FACTOR}")
    
    # Phase 1: Send MAX_REQUESTS requests - all should succeed
    logger.info("\nPhase 1: Sending requests that should succeed")
    for i in range(MAX_REQUESTS):
        response = make_request(client_id)
        responses.append(response)
        logger.info(f"Request {i+1}: Status={response['status_code']}")
        
        # Verify successful request
        assert response["status_code"] == 200, f"Expected 200, got {response['status_code']}"
        assert response["data"]["remaining"] == MAX_REQUESTS - (i + 1), f"Expected {MAX_REQUESTS - (i + 1)} remaining requests"
        time.sleep(NETWORK_LATENCY)
    
    # Phase 2: Send additional request - should be rate limited
    logger.info("\nPhase 2: Sending request that should be rate limited")
    response = make_request(client_id)
    responses.append(response)
    logger.info(f"Request {MAX_REQUESTS + 1}: Status={response['status_code']}")
    assert response["status_code"] == 429, f"Expected 429, got {response['status_code']}"
    assert response["error"]["remaining"] == 0, "Rate limited request should show 0 remaining"
    
    # Phase 3: Wait for window to reset and verify new requests succeed
    logger.info(f"\nPhase 3: Waiting {WINDOW_SIZE} seconds for window to reset")
    time.sleep(WINDOW_SIZE + 2.0)  # Add small buffer for safety
    
    logger.info("Sending new request after window reset")
    response = make_request(client_id)
    responses.append(response)
    logger.info(f"Request after reset: Status={response['status_code']}")
    assert response["status_code"] == 200, "Request after reset should succeed"
    assert response["data"]["remaining"] == MAX_REQUESTS - 1, f"Expected {MAX_REQUESTS - 1} remaining after reset"
    
    # Log all responses for analysis
    logger.info("\nResponse Summary:")
    for i, resp in enumerate(responses):
        logger.info(f"Request {i+1}: Status={resp['status_code']}, Remaining={resp['data']['remaining'] if resp['data'] else resp['error']['remaining']}")
    
    # Log final results
    successful_requests = sum(1 for r in responses if r["status_code"] == 200)
    rate_limited_requests = sum(1 for r in responses if r["status_code"] == 429)
    
    logger.info("\nTest Summary:")
    logger.info(f"Total requests made: {len(responses)}")
    logger.info(f"Successful requests: {successful_requests}")
    logger.info(f"Rate limited requests: {rate_limited_requests}")
    logger.info("All assertions passed - rate limiting is working as expected!")

if __name__ == "__main__":
    test_rate_limiting() 