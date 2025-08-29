#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_auto_indexing():
    print("Testing automatic email indexing...")
    
    # Step 1: Register a test user
    print("\n1. Registering test user...")
    register_data = {
        "email": "testuser@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register", json=register_data)
        print(f"Register response: {response.status_code}")
        if response.status_code != 200:
            print(f"Register failed: {response.text}")
    except Exception as e:
        print(f"Register error: {e}")
    
    # Step 2: Login to get token
    print("\n2. Logging in...")
    login_data = {
        "email": "testuser@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"Login response: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"Got token: {access_token[:20]}..." if access_token else "No token received")
        else:
            print(f"Login failed: {response.text}")
            return
    except Exception as e:
        print(f"Login error: {e}")
        return
    
    # Step 3: Send an email (which should auto-index)
    print("\n3. Sending email (should auto-index)...")
    headers = {"Authorization": f"Bearer {access_token}"}
    email_data = {
        "to_recipients": ["recipient@example.com"],
        "subject": "Auto Index Test Email",
        "body": "This email should be automatically indexed for search",
        "priority": "normal",
        "is_draft": False
    }
    
    try:
        response = requests.post(f"{BASE_URL}/emails", json=email_data, headers=headers)
        print(f"Send email response: {response.status_code}")
        if response.status_code == 200:
            email_response = response.json()
            email_id = email_response.get("id")
            print(f"Email sent with ID: {email_id}")
        else:
            print(f"Send email failed: {response.text}")
            return
    except Exception as e:
        print(f"Send email error: {e}")
        return
    
    # Step 4: Wait a moment for background indexing
    print("\n4. Waiting 3 seconds for background indexing...")
    time.sleep(3)
    
    # Step 5: Search for the email
    print("\n5. Searching for the email...")
    search_data = {
        "query": "Auto Index Test Email",
        "limit": 10,
        "offset": 0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/search", json=search_data, headers=headers)
        print(f"Search response: {response.status_code}")
        if response.status_code == 200:
            search_results = response.json()
            total_results = search_results.get("total", 0)
            print(f"Search found {total_results} results")
            
            if total_results > 0:
                print("✅ SUCCESS: Email was automatically indexed and is searchable!")
                for result in search_results.get("results", [])[:3]:
                    print(f"  - Subject: {result.get('subject')}")
            else:
                print("❌ FAILED: Email was not found in search results")
        else:
            print(f"Search failed: {response.text}")
    except Exception as e:
        print(f"Search error: {e}")

if __name__ == "__main__":
    test_auto_indexing()