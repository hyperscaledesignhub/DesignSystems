#!/usr/bin/env python3
"""
Test script for microservices (can run locally without Docker)
"""
import requests
import json
import time
import sys

def test_service(name, url, endpoint="/health"):
    """Test if a service is running"""
    try:
        response = requests.get(f"{url}{endpoint}", timeout=2)
        if response.status_code == 200:
            print(f"✅ {name}: Running at {url}")
            return True
        else:
            print(f"❌ {name}: Returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name}: Not running at {url}")
        return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False

def test_crawl_workflow():
    """Test the complete crawl workflow"""
    gateway_url = "http://localhost:5000"
    
    print("\n🔄 Testing Crawl Workflow...")
    
    # Test processing a single URL
    test_url = "https://httpbin.org/html"
    
    try:
        print(f"   Processing: {test_url}")
        response = requests.post(
            f"{gateway_url}/process",
            json={"url": test_url},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("   ✅ URL processed successfully")
                print(f"   📊 Steps completed: {list(result.get('steps', {}).keys())}")
            else:
                print(f"   ❌ Processing failed: {result.get('error')}")
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_crawl_start():
    """Test starting a crawl"""
    gateway_url = "http://localhost:5000"
    
    print("\n🚀 Testing Crawl Start...")
    
    seed_urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/links/3"
    ]
    
    try:
        # Start crawl
        response = requests.post(
            f"{gateway_url}/crawl/start",
            json={"seed_urls": seed_urls},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                crawl_id = result.get('crawl_id')
                print(f"   ✅ Crawl started: {crawl_id}")
                
                # Wait a bit
                time.sleep(3)
                
                # Check status
                status_response = requests.get(f"{gateway_url}/crawl/status")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"   📊 Status: {status.get('status')}")
                    print(f"   📊 Pages processed: {status.get('pages_processed')}")
                    print(f"   📊 Pages queued: {status.get('pages_queued')}")
                
                # Stop crawl
                stop_response = requests.post(f"{gateway_url}/crawl/stop")
                if stop_response.status_code == 200:
                    print("   ✅ Crawl stopped")
            else:
                print(f"   ❌ Failed to start: {result.get('error')}")
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    print("=" * 60)
    print("🧪 Microservices Crawler Test")
    print("=" * 60)
    
    # Define services to test
    services = {
        "API Gateway": "http://localhost:5000",
        "URL Frontier": "http://localhost:5001",
        "HTML Downloader": "http://localhost:5002",
        "Content Parser": "http://localhost:5003",
        "Deduplication": "http://localhost:5004"
    }
    
    print("\n📡 Testing Service Health...")
    all_running = True
    for name, url in services.items():
        if not test_service(name, url):
            all_running = False
    
    if not all_running:
        print("\n⚠️  Not all services are running!")
        print("Please start services with: docker-compose up -d")
        return 1
    
    print("\n✅ All services are healthy!")
    
    # Test workflow
    test_crawl_workflow()
    
    # Test crawl management
    test_crawl_start()
    
    print("\n" + "=" * 60)
    print("✅ Tests completed!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())