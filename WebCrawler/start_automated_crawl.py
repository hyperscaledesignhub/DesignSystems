#!/usr/bin/env python3
"""
Start an automated crawl that orchestrates all microservices automatically
"""
import requests
import time
import json

def start_automated_crawl():
    """Start automated crawling through API Gateway"""
    
    gateway_url = "http://localhost:5010"
    
    print("🚀 Starting Automated Microservices Crawl")
    print("=" * 50)
    
    # Seed URLs to crawl
    seed_urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/links/3",
        "https://httpbin.org/json"
    ]
    
    print(f"📝 Seed URLs: {seed_urls}")
    
    # Start the crawl - Gateway will orchestrate all services automatically
    print("\n🔄 Starting crawl (Gateway orchestrates all services)...")
    response = requests.post(
        f"{gateway_url}/crawl/start",
        json={"seed_urls": seed_urls},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        crawl_id = data.get('crawl_id')
        print(f"✅ Crawl started: {crawl_id}")
        print("   Gateway is now orchestrating all services automatically!")
        
        # Monitor progress
        print("\n📊 Monitoring Progress (auto-refresh every 2 seconds):")
        print("-" * 50)
        
        for i in range(30):  # Monitor for 60 seconds
            time.sleep(2)
            
            # Get status
            status_response = requests.get(f"{gateway_url}/crawl/status")
            if status_response.status_code == 200:
                status = status_response.json()
                
                print(f"\r⏱️  [{i*2}s] Status: {status['status']} | "
                      f"Processed: {status['pages_processed']} | "
                      f"Queued: {status['pages_queued']} | "
                      f"Duplicates: {status['duplicates_found']} | "
                      f"Errors: {status['errors_count']}", end="")
                
                # Stop if completed
                if status['status'] in ['completed', 'stopped']:
                    print("\n\n✅ Crawl completed!")
                    break
        
        print("\n" + "=" * 50)
        print("📈 Final Statistics:")
        
        # Get final stats from all services
        stats_response = requests.get(f"{gateway_url}/stats")
        if stats_response.status_code == 200:
            all_stats = stats_response.json()
            
            for service, stats in all_stats.items():
                if stats and not stats.get('error'):
                    print(f"\n{service.upper()}:")
                    for key, value in stats.items():
                        print(f"  • {key}: {value}")
        
    else:
        print(f"❌ Failed to start crawl: {response.text}")

if __name__ == "__main__":
    print("🎯 Microservices Automated Crawl Demo")
    print("This demonstrates all services working together automatically")
    print("=" * 50)
    
    # Check if services are running
    print("🔍 Checking services...")
    services_ok = True
    
    for service, port in [('Gateway', 5010), ('Frontier', 5011), ('Downloader', 5002), ('Parser', 5003), ('Dedup', 5004)]:
        try:
            r = requests.get(f"http://localhost:{port}/health", timeout=2)
            if r.status_code == 200:
                print(f"✅ {service} is healthy")
            else:
                print(f"❌ {service} is unhealthy")
                services_ok = False
        except:
            print(f"❌ {service} is not running")
            services_ok = False
    
    if not services_ok:
        print("\n⚠️  Some services are not running!")
        print("Run: docker-compose -f docker-compose-simple.yml up -d")
    else:
        print("\n✅ All services healthy!")
        start_automated_crawl()