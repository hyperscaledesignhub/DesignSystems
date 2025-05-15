#!/usr/bin/env python3

import requests
import time
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = 'http://localhost:8080'
CAPACITY = 5  # Maximum tokens in the bucket (matching config.yaml)
REFILL_RATE = 1.0  # Tokens added per second (matching config.yaml)
NETWORK_LATENCY = 0.05  # 50ms network latency
RETRY_ATTEMPTS = 5  # Number of retries for continuous phase


def make_request(client_id: str) -> Dict[str, Any]:
    """Make a request to the rate-limited endpoint."""
    headers = {"X-Client-ID": client_id}
    response = requests.get(f"{BASE_URL}/api/limited", headers=headers)
    return {
        "status_code": response.status_code,
        "data": response.json() if response.status_code == 200 else None,
        "error": response.json() if response.status_code == 429 else None
    }


def test_token_bucket_rate_limiting():
    """Test rate limiting behavior of the token bucket endpoint."""
    client_id = f"test_client_{int(time.time())}"
    responses = []
    
    logger.info(f"\nTesting token bucket rate limiting for client {client_id}")
    logger.info(f"Bucket capacity: {CAPACITY}")
    logger.info(f"Refill rate: {REFILL_RATE} tokens/second")
    
    # Phase 1: Fill the bucket to capacity - all should succeed
    logger.info("\nPhase 1: Filling bucket to capacity")
    for i in range(CAPACITY):
        response = make_request(client_id)
        responses.append(response)
        logger.info(f"Request {i+1}: Status={response['status_code']}, Response={response['data'] if response['data'] else response['error']}")
        assert response["status_code"] == 200, f"Expected 200, got {response['status_code']}"
        if response["data"]:
            logger.info(f"Remaining tokens: {response['data']['remaining']}")
        time.sleep(NETWORK_LATENCY)
    
    # Phase 2: Try to exceed capacity - should be rate limited
    logger.info("\nPhase 2: Attempting to exceed bucket capacity")
    response = make_request(client_id)
    responses.append(response)
    logger.info(f"Request {CAPACITY + 1}: Status={response['status_code']}, Response={response['error']}")
    assert response["status_code"] == 429, f"Expected 429, got {response['status_code']}"
    assert response["error"]["remaining"] == 0, "Rate limited request should show 0 remaining"
    
    # Phase 3: Wait for bucket to refill and verify new requests succeed
    refill_wait_time = 1.0 / REFILL_RATE  # Time for one token to refill
    logger.info(f"\nPhase 3: Waiting {refill_wait_time} seconds for one token to refill")
    time.sleep(refill_wait_time + 0.1)  # Add small buffer for safety
    
    logger.info("Sending new request after refill")
    success = False
    for attempt in range(RETRY_ATTEMPTS):
        response = make_request(client_id)
        logger.info(f"Request after refill, attempt {attempt+1}: Status={response['status_code']}, Response={response['data'] if response['data'] else response['error']}")
        if response["status_code"] == 200:
            success = True
            break
        time.sleep(0.1)  # Small delay between retries
    assert success, "Request after refill should succeed after retries"
    responses.append(response)
    
    # Phase 4: Test continuous request pattern (robust to timing)
    logger.info("\nPhase 4: Testing continuous request pattern with retries")
    continuous_success = 0
    for i in range(3):
        success = False
        for attempt in range(RETRY_ATTEMPTS):
            time.sleep(refill_wait_time)
            response = make_request(client_id)
            logger.info(f"Continuous request {i+1}, attempt {attempt+1}: Status={response['status_code']}, Response={response['data'] if response['data'] else response['error']}")
            if response["status_code"] == 200:
                success = True
                break
        if success:
            continuous_success += 1
        else:
            logger.warning(f"Continuous request {i+1} failed after {RETRY_ATTEMPTS} attempts.")
        responses.append(response)
    assert continuous_success >= 2, f"Expected at least 2 successful continuous requests, got {continuous_success}"
    
    # Log all responses for analysis
    logger.info("\nResponse Summary:")
    for i, resp in enumerate(responses):
        logger.info(f"Request {i+1}: Status={resp['status_code']}, Response={resp['data'] if resp['data'] else resp['error']}")
    
    # Log final results
    successful_requests = sum(1 for r in responses if r["status_code"] == 200)
    rate_limited_requests = sum(1 for r in responses if r["status_code"] == 429)
    
    logger.info("\nTest Summary:")
    logger.info(f"Total requests made: {len(responses)}")
    logger.info(f"Successful requests: {successful_requests}")
    logger.info(f"Rate limited requests: {rate_limited_requests}")
    logger.info("All assertions passed - token bucket rate limiting is working as expected!")


if __name__ == "__main__":
    test_token_bucket_rate_limiting() 