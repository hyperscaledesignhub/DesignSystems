#!/usr/bin/env python3
"""
Demo script showing how to invoke quorum read and write operations via API
"""

import requests
import json
import time
import sys
import os

# Add distributed to path
sys.path.append('../distributed')

def quorum_write(node_url, key, value):
    """Write a key-value pair with quorum consistency"""
    try:
        response = requests.put(
            f"{node_url}/kv/{key}",
            json={"value": value},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def quorum_read(node_url, key):
    """Read a key with quorum consistency"""
    try:
        response = requests.get(f"{node_url}/kv/{key}", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def get_quorum_info(node_url, key):
    """Get quorum information for a key"""
    try:
        response = requests.get(f"{node_url}/quorum/{key}", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def direct_write(node_url, key, value):
    """Write directly to local node (bypass quorum)"""
    try:
        response = requests.put(
            f"{node_url}/kv/{key}/direct",
            json={"value": value},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def direct_read(node_url, key):
    """Read directly from local node (bypass quorum)"""
    try:
        response = requests.get(f"{node_url}/kv/{key}/direct", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def print_result(operation, result, status_code):
    """Print operation result in a formatted way"""
    print(f"\n{'='*60}")
    print(f"🔧 {operation}")
    print(f"{'='*60}")
    print(f"Status Code: {status_code}")
    print(f"Response: {json.dumps(result, indent=2)}")

def main():
    """Main demo function"""
    print("🚀 Quorum API Demo")
    print("="*60)
    
    # Default node URL (first node in cluster)
    node_url = "http://localhost:9999"
    
    print(f"📡 Using node: {node_url}")
    print(f"📋 Current config: write_quorum=2, read_quorum=1")
    
    # Test 1: Get quorum info for a key
    print_result("Get Quorum Info", *get_quorum_info(node_url, "demo-key"))
    
    # Test 2: Quorum write
    print_result("Quorum Write", *quorum_write(node_url, "demo-key", "demo-value"))
    
    # Test 3: Quorum read
    print_result("Quorum Read", *quorum_read(node_url, "demo-key"))
    
    # Test 4: Direct write (bypass quorum)
    print_result("Direct Write", *direct_write(node_url, "direct-key", "direct-value"))
    
    # Test 5: Direct read (bypass quorum)
    print_result("Direct Read", *direct_read(node_url, "direct-key"))
    
    # Test 6: Read non-existent key
    print_result("Read Non-existent Key", *quorum_read(node_url, "nonexistent-key"))
    
    # Test 7: Write complex data
    complex_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30,
        "active": True
    }
    print_result("Write Complex Data", *quorum_write(node_url, "user-123", json.dumps(complex_data)))
    
    # Test 8: Read complex data
    print_result("Read Complex Data", *quorum_read(node_url, "user-123"))
    
    # Test 9: Multiple writes to test quorum behavior
    print("\n" + "="*60)
    print("🔄 Testing Multiple Writes")
    print("="*60)
    
    for i in range(3):
        key = f"batch-key-{i}"
        value = f"batch-value-{i}"
        result, status = quorum_write(node_url, key, value)
        print(f"Write {i+1}: {key} = {value}")
        print(f"  Status: {status}")
        print(f"  Success: {'error' not in result}")
        if 'error' not in result:
            print(f"  Successful writes: {result.get('successful_writes', 'N/A')}")
            print(f"  Async replication: {len(result.get('async_replication', []))} nodes")
        time.sleep(0.5)  # Small delay between writes
    
    print("\n" + "="*60)
    print("✅ Demo completed!")
    print("="*60)
    print("\n📚 Key Points:")
    print("• Quorum writes require 2 successful writes (write_quorum=2)")
    print("• Quorum reads require 1 successful read (read_quorum=1)")
    print("• Optimistic replication: returns success after quorum, replicates remaining nodes asynchronously")
    print("• Direct operations bypass quorum for internal/debugging use")
    print("• All operations include detailed response information")

if __name__ == "__main__":
    # Set config file path
    os.environ['CONFIG_FILE'] = '../yaml/config-local.yaml'
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\n💡 Make sure the cluster is running:")
        print("   cd scripts && ./start-cluster-local.sh") 