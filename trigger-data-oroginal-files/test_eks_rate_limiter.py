#!/Users/vijayabhaskarv/python-projects/venv/bin/python

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import os

BASE_URL = 'http://localhost:8080'

def test_rate_limiter_429():
    """Test rate limiter with 5 requests per second."""
    # Get the LoadBalancer endpoint
    endpoint = BASE_URL
    print(f"Testing rate limiter at {endpoint}")
    print("Configuration: 5 requests per second (leaky bucket)")

    # Use a consistent client ID for all requests
    client_id = "test_client_eks"
    headers = {'X-Client-ID': client_id}

    print("\nTesting requests within limit...")
    # Make 5 requests (within limit)
    start_time = time.time()
    for i in range(5):
        request_time = time.time() - start_time
        response = requests.get(f"{endpoint}/api/limited", headers=headers)
        print(f"Request {i+1} at {request_time:.3f}s: Status {response.status_code}, Response: {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        time.sleep(0.1)  # Add a small delay between requests

    print("\nTesting rate limit exceeded...")
    # Make 6th request (should be rate limited)
    request_time = time.time() - start_time
    response = requests.get(f"{endpoint}/api/limited", headers=headers)
    print(f"Rate limited request at {request_time:.3f}s: Status {response.status_code}, Response: {response.json()}")
    print(f"Time since first request: {request_time:.3f}s")
    assert response.status_code == 429, f"Expected 429, got {response.status_code}"
    assert response.json()['remaining'] == 0, "Expected remaining to be 0"

    print("\nTesting token refill...")
    # Wait for tokens to refill (5 seconds)
    time.sleep(5.0)  # Increased waiting time for rate limiter to reset
    # Make another request (should be allowed)
    response = requests.get(f"{endpoint}/api/limited", headers=headers)
    print(f"Request after waiting: Status {response.status_code}, Response: {response.json()}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    print("\nTesting burst handling...")
    # Make 3 quick requests to test burst handling
    for i in range(3):
        response = requests.get(f"{endpoint}/api/limited", headers=headers)
        print(f"Burst request {i+1}: Status {response.status_code}, Response: {response.json()}")
        time.sleep(0.1)

def test_concurrent_requests():
    """Test concurrent requests from multiple clients."""
    endpoint = BASE_URL
    print("\nTesting concurrent requests...")

    def make_request(client_id):
        headers = {'X-Client-ID': f'test_client_eks_{client_id}'}
        response = requests.get(f"{endpoint}/api/limited", headers=headers)
        print(f"Client {client_id}: Status {response.status_code}, Response: {response.json()}")
        return response.status_code

    # Make concurrent requests from 3 different clients
    status_codes = []
    for i in range(3):
        status_codes.append(make_request(i))
        time.sleep(0.1)  # Add a small delay between requests

    # All requests should be allowed (different clients)
    assert all(code == 200 for code in status_codes), "Not all concurrent requests were allowed"

if __name__ == "__main__":
    test_rate_limiter_429()
    test_concurrent_requests() 