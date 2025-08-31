#!/usr/bin/env python3
"""
Performance and load testing for S3 Storage System
"""

import os
import sys
import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import requests

# Configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:7841")
API_KEY = os.getenv("API_KEY", "")

class PerformanceTester:
    def __init__(self, gateway_url: str, api_key: str):
        self.gateway_url = gateway_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.bucket_name = f"perf-test-{int(time.time())}"
        
    def setup(self):
        """Create test bucket"""
        session = requests.Session()
        session.headers.update(self.headers)
        resp = session.post(
            f"{self.gateway_url}/buckets",
            json={"bucket_name": self.bucket_name}
        )
        return resp.status_code in [200, 201]
    
    def cleanup(self):
        """Clean up test bucket"""
        session = requests.Session()
        session.headers.update(self.headers)
        
        # Delete all objects
        try:
            resp = session.get(f"{self.gateway_url}/buckets/{self.bucket_name}/objects")
            if resp.status_code == 200:
                objects = resp.json().get("objects", [])
                for obj in objects:
                    session.delete(
                        f"{self.gateway_url}/buckets/{self.bucket_name}/objects/{obj['object_name']}"
                    )
        except:
            pass
        
        # Delete bucket
        try:
            session.delete(f"{self.gateway_url}/buckets/{self.bucket_name}")
        except:
            pass
    
    def upload_object(self, obj_name: str, content: bytes) -> Tuple[bool, float]:
        """Upload object and measure time"""
        session = requests.Session()
        session.headers.update(self.headers)
        
        start_time = time.time()
        try:
            resp = session.put(
                f"{self.gateway_url}/buckets/{self.bucket_name}/objects/{obj_name}",
                data=content
            )
            duration = time.time() - start_time
            return resp.status_code in [200, 201], duration
        except Exception:
            return False, time.time() - start_time
    
    def download_object(self, obj_name: str) -> Tuple[bool, float, int]:
        """Download object and measure time"""
        session = requests.Session()
        session.headers.update(self.headers)
        
        start_time = time.time()
        try:
            resp = session.get(
                f"{self.gateway_url}/buckets/{self.bucket_name}/objects/{obj_name}"
            )
            duration = time.time() - start_time
            return resp.status_code == 200, duration, len(resp.content)
        except Exception:
            return False, time.time() - start_time, 0
    
    def test_upload_performance(self, file_sizes: List[int], num_threads: int = 1):
        """Test upload performance for different file sizes"""
        print(f"\n📤 Testing Upload Performance ({num_threads} threads)")
        print("-" * 60)
        
        for size in file_sizes:
            content = os.urandom(size)
            results = []
            
            def upload_worker(worker_id: int) -> Tuple[bool, float]:
                obj_name = f"upload-test-{size}-{worker_id}.bin"
                return self.upload_object(obj_name, content)
            
            start_time = time.time()
            
            if num_threads == 1:
                success, duration = upload_worker(0)
                results = [(success, duration)]
            else:
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [executor.submit(upload_worker, i) for i in range(num_threads)]
                    results = [f.result() for f in as_completed(futures)]
            
            total_time = time.time() - start_time
            successful_uploads = sum(1 for success, _ in results if success)
            durations = [duration for success, duration in results if success]
            
            if durations:
                avg_duration = statistics.mean(durations)
                throughput = (size * successful_uploads) / total_time / 1024 / 1024  # MB/s
                
                print(f"Size: {size//1024:>6} KB | "
                      f"Success: {successful_uploads:>2}/{num_threads} | "
                      f"Avg Time: {avg_duration:>6.3f}s | "
                      f"Throughput: {throughput:>6.2f} MB/s")
            else:
                print(f"Size: {size//1024:>6} KB | All uploads failed")
    
    def test_download_performance(self, file_sizes: List[int], num_threads: int = 1):
        """Test download performance"""
        print(f"\n📥 Testing Download Performance ({num_threads} threads)")
        print("-" * 60)
        
        # First upload test files
        test_objects = []
        for size in file_sizes:
            content = os.urandom(size)
            obj_name = f"download-test-{size}.bin"
            success, _ = self.upload_object(obj_name, content)
            if success:
                test_objects.append((obj_name, size))
        
        for obj_name, size in test_objects:
            results = []
            
            def download_worker(worker_id: int) -> Tuple[bool, float, int]:
                return self.download_object(obj_name)
            
            start_time = time.time()
            
            if num_threads == 1:
                success, duration, content_size = download_worker(0)
                results = [(success, duration, content_size)]
            else:
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [executor.submit(download_worker, i) for i in range(num_threads)]
                    results = [f.result() for f in as_completed(futures)]
            
            total_time = time.time() - start_time
            successful_downloads = sum(1 for success, _, _ in results if success)
            durations = [duration for success, duration, _ in results if success]
            
            if durations:
                avg_duration = statistics.mean(durations)
                throughput = (size * successful_downloads) / total_time / 1024 / 1024  # MB/s
                
                print(f"Size: {size//1024:>6} KB | "
                      f"Success: {successful_downloads:>2}/{num_threads} | "
                      f"Avg Time: {avg_duration:>6.3f}s | "
                      f"Throughput: {throughput:>6.2f} MB/s")
            else:
                print(f"Size: {size//1024:>6} KB | All downloads failed")
    
    def test_concurrent_operations(self):
        """Test concurrent mixed operations"""
        print(f"\n🔀 Testing Concurrent Mixed Operations")
        print("-" * 60)
        
        operations = []
        results = []
        
        # Define mixed operations
        def upload_small():
            content = os.urandom(1024)  # 1KB
            obj_name = f"concurrent-small-{threading.get_ident()}.bin"
            start = time.time()
            success, _ = self.upload_object(obj_name, content)
            return "upload_small", success, time.time() - start
        
        def upload_large():
            content = os.urandom(100 * 1024)  # 100KB
            obj_name = f"concurrent-large-{threading.get_ident()}.bin"
            start = time.time()
            success, _ = self.upload_object(obj_name, content)
            return "upload_large", success, time.time() - start
        
        def list_objects():
            session = requests.Session()
            session.headers.update(self.headers)
            start = time.time()
            try:
                resp = session.get(f"{self.gateway_url}/buckets/{self.bucket_name}/objects")
                success = resp.status_code == 200
            except:
                success = False
            return "list_objects", success, time.time() - start
        
        # Create operation mix
        for _ in range(20):
            operations.extend([upload_small, upload_large, list_objects])
        
        # Execute concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(op) for op in operations]
            results = [f.result() for f in as_completed(futures)]
        
        # Analyze results
        by_operation = {}
        for op_type, success, duration in results:
            if op_type not in by_operation:
                by_operation[op_type] = []
            by_operation[op_type].append((success, duration))
        
        for op_type, op_results in by_operation.items():
            successful = sum(1 for success, _ in op_results if success)
            total = len(op_results)
            durations = [duration for success, duration in op_results if success]
            
            if durations:
                avg_duration = statistics.mean(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                
                print(f"{op_type:>12} | "
                      f"Success: {successful:>2}/{total} | "
                      f"Avg: {avg_duration:>6.3f}s | "
                      f"Min: {min_duration:>6.3f}s | "
                      f"Max: {max_duration:>6.3f}s")
    
    def test_bucket_operations_performance(self):
        """Test bucket operations performance"""
        print(f"\n🪣 Testing Bucket Operations Performance")
        print("-" * 60)
        
        session = requests.Session()
        session.headers.update(self.headers)
        
        # Test bucket creation speed
        bucket_names = [f"perf-bucket-{i}-{int(time.time())}" for i in range(10)]
        
        start_time = time.time()
        created_buckets = []
        for bucket_name in bucket_names:
            try:
                resp = session.post(
                    f"{self.gateway_url}/buckets",
                    json={"bucket_name": bucket_name}
                )
                if resp.status_code in [200, 201]:
                    created_buckets.append(bucket_name)
            except:
                pass
        
        creation_time = time.time() - start_time
        print(f"Bucket Creation | "
              f"Created: {len(created_buckets)}/10 | "
              f"Total Time: {creation_time:.3f}s | "
              f"Rate: {len(created_buckets)/creation_time:.1f} buckets/s")
        
        # Test bucket listing speed
        start_time = time.time()
        list_success = 0
        for _ in range(10):
            try:
                resp = session.get(f"{self.gateway_url}/buckets")
                if resp.status_code == 200:
                    list_success += 1
            except:
                pass
        
        listing_time = time.time() - start_time
        print(f"Bucket Listing  | "
              f"Success: {list_success}/10 | "
              f"Total Time: {listing_time:.3f}s | "
              f"Rate: {list_success/listing_time:.1f} ops/s")
        
        # Cleanup
        for bucket_name in created_buckets:
            try:
                session.delete(f"{self.gateway_url}/buckets/{bucket_name}")
            except:
                pass
    
    def run_performance_tests(self):
        """Run all performance tests"""
        print("🚀 S3 Storage System - Performance Test Suite")
        print("=" * 60)
        
        if not self.setup():
            print("❌ Failed to create test bucket")
            return False
        
        try:
            # Test file sizes: 1KB, 10KB, 100KB, 1MB
            file_sizes = [1024, 10*1024, 100*1024, 1024*1024]
            
            # Single-threaded tests
            self.test_upload_performance(file_sizes, 1)
            self.test_download_performance(file_sizes, 1)
            
            # Multi-threaded tests
            self.test_upload_performance(file_sizes[:3], 5)  # Skip 1MB for multi-threaded
            self.test_download_performance(file_sizes[:3], 5)
            
            # Mixed operations
            self.test_concurrent_operations()
            
            # Bucket operations
            self.test_bucket_operations_performance()
            
            print(f"\n✅ Performance tests completed")
            return True
            
        finally:
            self.cleanup()


def main():
    if not API_KEY:
        print("❌ ERROR: API_KEY environment variable not set")
        print("Usage: API_KEY=your_api_key python test_performance.py")
        sys.exit(1)
    
    # Check if services are running
    try:
        resp = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        if resp.status_code != 200:
            print(f"❌ ERROR: API Gateway not responding at {GATEWAY_URL}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Cannot connect to API Gateway at {GATEWAY_URL}")
        sys.exit(1)
    
    tester = PerformanceTester(GATEWAY_URL, API_KEY)
    success = tester.run_performance_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()