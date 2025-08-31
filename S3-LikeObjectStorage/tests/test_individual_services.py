#!/usr/bin/env python3
"""
Individual service testing - tests each service directly
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Optional

# Service URLs
SERVICES = {
    "identity": os.getenv("IDENTITY_URL", "http://localhost:7851"),
    "bucket": os.getenv("BUCKET_URL", "http://localhost:7861"),
    "object": os.getenv("OBJECT_URL", "http://localhost:7871"),
    "storage": os.getenv("STORAGE_URL", "http://localhost:7881"),
    "metadata": os.getenv("METADATA_URL", "http://localhost:7891"),
}

class ServiceTester:
    def __init__(self):
        self.test_results = []
        self.test_user_id = f"test-user-{int(time.time())}"
        self.test_api_key = None
        
    def log_test(self, service: str, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅" if passed else "❌"
        print(f"  [{status}] {service}: {test_name}")
        if details and not passed:
            print(f"        Details: {details}")
        self.test_results.append((service, test_name, passed, details))
    
    def test_identity_service(self):
        """Test Identity Service directly"""
        print("\n🔐 Testing Identity Service")
        service_url = SERVICES["identity"]
        
        # Health check
        try:
            resp = requests.get(f"{service_url}/health")
            self.log_test("identity", "Health check", resp.status_code == 200)
        except Exception as e:
            self.log_test("identity", "Health check", False, str(e))
        
        # Create user
        try:
            resp = requests.post(
                f"{service_url}/users",
                json={
                    "user_id": self.test_user_id,
                    "permissions": {"buckets": ["READ", "WRITE"], "objects": ["READ", "WRITE"]}
                }
            )
            success = resp.status_code in [200, 201]
            if success:
                data = resp.json()
                self.test_api_key = data.get("api_key")
            self.log_test("identity", "Create user", success)
        except Exception as e:
            self.log_test("identity", "Create user", False, str(e))
        
        # Get user
        try:
            resp = requests.get(f"{service_url}/users/{self.test_user_id}")
            self.log_test("identity", "Get user", resp.status_code == 200)
        except Exception as e:
            self.log_test("identity", "Get user", False, str(e))
        
        # Validate API key
        if self.test_api_key:
            try:
                resp = requests.post(
                    f"{service_url}/auth/validate",
                    headers={"Authorization": f"Bearer {self.test_api_key}"}
                )
                self.log_test("identity", "Validate API key", resp.status_code == 200)
            except Exception as e:
                self.log_test("identity", "Validate API key", False, str(e))
        
        # Invalid API key
        try:
            resp = requests.post(
                f"{service_url}/auth/validate",
                headers={"Authorization": "Bearer invalid_key"}
            )
            self.log_test("identity", "Invalid API key rejection", resp.status_code == 401)
        except Exception as e:
            self.log_test("identity", "Invalid API key rejection", False, str(e))
    
    def test_bucket_service(self):
        """Test Bucket Service directly"""
        print("\n🪣 Testing Bucket Service")
        service_url = SERVICES["bucket"]
        test_bucket = f"test-bucket-{int(time.time())}"
        
        # Health check
        try:
            resp = requests.get(f"{service_url}/health")
            self.log_test("bucket", "Health check", resp.status_code == 200)
        except Exception as e:
            self.log_test("bucket", "Health check", False, str(e))
        
        # Create bucket
        try:
            resp = requests.post(
                f"{service_url}/buckets",
                json={"bucket_name": test_bucket},
                headers={"X-User-ID": self.test_user_id}
            )
            self.log_test("bucket", "Create bucket", resp.status_code in [200, 201])
        except Exception as e:
            self.log_test("bucket", "Create bucket", False, str(e))
        
        # List buckets
        try:
            resp = requests.get(
                f"{service_url}/buckets",
                headers={"X-User-ID": self.test_user_id}
            )
            success = resp.status_code == 200 and isinstance(resp.json(), list)
            self.log_test("bucket", "List buckets", success)
        except Exception as e:
            self.log_test("bucket", "List buckets", False, str(e))
        
        # Get specific bucket
        try:
            resp = requests.get(
                f"{service_url}/buckets/{test_bucket}",
                headers={"X-User-ID": self.test_user_id}
            )
            self.log_test("bucket", "Get bucket", resp.status_code == 200)
        except Exception as e:
            self.log_test("bucket", "Get bucket", False, str(e))
        
        # Check bucket exists (internal API)
        try:
            resp = requests.get(f"{service_url}/buckets/{test_bucket}/exists")
            success = resp.status_code == 200 and resp.json().get("exists") == True
            self.log_test("bucket", "Check bucket exists", success)
        except Exception as e:
            self.log_test("bucket", "Check bucket exists", False, str(e))
        
        # Invalid bucket name
        try:
            resp = requests.post(
                f"{service_url}/buckets",
                json={"bucket_name": "A"},  # Too short
                headers={"X-User-ID": self.test_user_id}
            )
            self.log_test("bucket", "Invalid bucket name rejection", resp.status_code == 400)
        except Exception as e:
            self.log_test("bucket", "Invalid bucket name rejection", False, str(e))
        
        # Delete bucket
        try:
            resp = requests.delete(
                f"{service_url}/buckets/{test_bucket}",
                headers={"X-User-ID": self.test_user_id}
            )
            self.log_test("bucket", "Delete bucket", resp.status_code in [200, 204])
        except Exception as e:
            self.log_test("bucket", "Delete bucket", False, str(e))
    
    def test_storage_service(self):
        """Test Storage Service directly"""
        print("\n💾 Testing Storage Service")
        service_url = SERVICES["storage"]
        test_content = b"Test storage content"
        test_uuid = None
        
        # Health check
        try:
            resp = requests.get(f"{service_url}/health")
            self.log_test("storage", "Health check", resp.status_code == 200)
        except Exception as e:
            self.log_test("storage", "Health check", False, str(e))
        
        # Store data
        try:
            resp = requests.post(
                f"{service_url}/data",
                data=test_content,
                headers={
                    "X-Object-ID": "test-uuid-12345",
                    "X-Content-Type": "text/plain"
                }
            )
            success = resp.status_code in [200, 201]
            if success:
                test_uuid = resp.headers.get("X-Object-UUID", "test-uuid-12345")
            self.log_test("storage", "Store data", success)
        except Exception as e:
            self.log_test("storage", "Store data", False, str(e))
        
        # Retrieve data
        if test_uuid:
            try:
                resp = requests.get(f"{service_url}/data/{test_uuid}")
                content_match = resp.content == test_content
                self.log_test("storage", "Retrieve data", resp.status_code == 200 and content_match)
            except Exception as e:
                self.log_test("storage", "Retrieve data", False, str(e))
            
            # Get object info
            try:
                resp = requests.get(f"{service_url}/data/{test_uuid}/info")
                self.log_test("storage", "Get object info", resp.status_code == 200)
            except Exception as e:
                self.log_test("storage", "Get object info", False, str(e))
            
            # Delete data
            try:
                resp = requests.delete(f"{service_url}/data/{test_uuid}")
                self.log_test("storage", "Delete data", resp.status_code in [200, 204])
            except Exception as e:
                self.log_test("storage", "Delete data", False, str(e))
        
        # Get storage stats
        try:
            resp = requests.get(f"{service_url}/stats")
            self.log_test("storage", "Get storage stats", resp.status_code == 200)
        except Exception as e:
            self.log_test("storage", "Get storage stats", False, str(e))
        
        # Non-existent object
        try:
            resp = requests.get(f"{service_url}/data/non-existent-uuid")
            self.log_test("storage", "Non-existent object returns 404", resp.status_code == 404)
        except Exception as e:
            self.log_test("storage", "Non-existent object returns 404", False, str(e))
    
    def test_metadata_service(self):
        """Test Metadata Service directly"""
        print("\n📋 Testing Metadata Service")
        service_url = SERVICES["metadata"]
        test_bucket = f"test-metadata-bucket-{int(time.time())}"
        test_object_id = "test-metadata-object-12345"
        
        # Health check
        try:
            resp = requests.get(f"{service_url}/health")
            self.log_test("metadata", "Health check", resp.status_code == 200)
        except Exception as e:
            self.log_test("metadata", "Health check", False, str(e))
        
        # Create object metadata
        metadata = {
            "object_id": test_object_id,
            "bucket_name": test_bucket,
            "object_name": "test-object.txt",
            "content_type": "text/plain",
            "size_bytes": 100,
            "etag": "abcd1234"
        }
        
        try:
            resp = requests.post(
                f"{service_url}/metadata/objects",
                json=metadata
            )
            self.log_test("metadata", "Create object metadata", resp.status_code in [200, 201])
        except Exception as e:
            self.log_test("metadata", "Create object metadata", False, str(e))
        
        # Get object metadata
        try:
            resp = requests.get(f"{service_url}/metadata/objects/{test_object_id}")
            self.log_test("metadata", "Get object metadata", resp.status_code == 200)
        except Exception as e:
            self.log_test("metadata", "Get object metadata", False, str(e))
        
        # List objects in bucket
        try:
            resp = requests.get(f"{service_url}/metadata/buckets/{test_bucket}/objects")
            self.log_test("metadata", "List objects in bucket", resp.status_code == 200)
        except Exception as e:
            self.log_test("metadata", "List objects in bucket", False, str(e))
        
        # List objects with prefix
        try:
            resp = requests.get(
                f"{service_url}/metadata/buckets/{test_bucket}/objects?prefix=test-"
            )
            self.log_test("metadata", "List objects with prefix", resp.status_code == 200)
        except Exception as e:
            self.log_test("metadata", "List objects with prefix", False, str(e))
        
        # Get bucket stats
        try:
            resp = requests.get(f"{service_url}/metadata/buckets/{test_bucket}/stats")
            self.log_test("metadata", "Get bucket stats", resp.status_code == 200)
        except Exception as e:
            self.log_test("metadata", "Get bucket stats", False, str(e))
        
        # Get global stats
        try:
            resp = requests.get(f"{service_url}/metadata/stats")
            self.log_test("metadata", "Get global stats", resp.status_code == 200)
        except Exception as e:
            self.log_test("metadata", "Get global stats", False, str(e))
        
        # Update object metadata
        try:
            updated_metadata = metadata.copy()
            updated_metadata["size_bytes"] = 200
            resp = requests.put(
                f"{service_url}/metadata/objects/{test_object_id}",
                json=updated_metadata
            )
            self.log_test("metadata", "Update object metadata", resp.status_code == 200)
        except Exception as e:
            self.log_test("metadata", "Update object metadata", False, str(e))
        
        # Delete object metadata
        try:
            resp = requests.delete(f"{service_url}/metadata/objects/{test_object_id}")
            self.log_test("metadata", "Delete object metadata", resp.status_code in [200, 204])
        except Exception as e:
            self.log_test("metadata", "Delete object metadata", False, str(e))
        
        # Duplicate metadata creation
        try:
            resp = requests.post(f"{service_url}/metadata/objects", json=metadata)
            resp2 = requests.post(f"{service_url}/metadata/objects", json=metadata)
            self.log_test("metadata", "Duplicate metadata returns 409", resp2.status_code == 409)
            # Cleanup
            requests.delete(f"{service_url}/metadata/objects/{test_object_id}")
        except Exception as e:
            self.log_test("metadata", "Duplicate metadata returns 409", False, str(e))
    
    def test_service_connectivity(self):
        """Test that all services are reachable"""
        print("\n🌐 Testing Service Connectivity")
        
        for service_name, service_url in SERVICES.items():
            try:
                resp = requests.get(f"{service_url}/health", timeout=5)
                self.log_test("connectivity", f"{service_name} service reachable", resp.status_code == 200)
            except Exception as e:
                self.log_test("connectivity", f"{service_name} service reachable", False, str(e))
    
    def cleanup(self):
        """Clean up test resources"""
        print("\n🧹 Cleaning up test resources")
        
        # Delete test user
        if self.test_user_id:
            try:
                requests.delete(f"{SERVICES['identity']}/users/{self.test_user_id}")
                print(f"  Cleaned up user: {self.test_user_id}")
            except:
                pass
    
    def run_all_tests(self):
        """Run all service tests"""
        print("🔧 S3 Storage System - Individual Service Tests")
        print("=" * 60)
        
        start_time = time.time()
        
        self.test_service_connectivity()
        self.test_identity_service()
        self.test_bucket_service()
        self.test_storage_service()
        self.test_metadata_service()
        
        self.cleanup()
        
        # Summary
        duration = time.time() - start_time
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, _, passed, _ in self.test_results if passed)
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"Service Test Summary")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        if failed_tests > 0:
            print(f"\nFailed Tests:")
            for service, test_name, passed, details in self.test_results:
                if not passed:
                    print(f"  - {service}: {test_name}")
                    if details:
                        print(f"    {details}")
        
        return passed_tests == total_tests


def main():
    """Main test runner"""
    print("Checking service connectivity...")
    
    # Check if at least one service is running
    available_services = 0
    for service_name, service_url in SERVICES.items():
        try:
            resp = requests.get(f"{service_url}/health", timeout=2)
            if resp.status_code == 200:
                available_services += 1
                print(f"✅ {service_name} service available")
            else:
                print(f"❌ {service_name} service not responding")
        except:
            print(f"❌ {service_name} service not reachable at {service_url}")
    
    if available_services == 0:
        print("\n❌ No services are reachable. Please start the services first.")
        sys.exit(1)
    
    print(f"\n📊 Found {available_services}/{len(SERVICES)} services available")
    
    # Run tests
    tester = ServiceTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()