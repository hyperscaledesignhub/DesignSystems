#!/usr/bin/env python3
"""
Demo script for quorum-based causal consistency endpoints
"""

import requests
import json
import time
import sys
import os

# Add distributed to path
sys.path.append('../distributed')

def causal_quorum_write(node_url, key, value, vector_clock=None):
    """Write with causal consistency using quorum replication"""
    try:
        data = {"value": value}
        if vector_clock:
            data["vector_clock"] = vector_clock
            
        response = requests.put(
            f"{node_url}/causal/kv/{key}",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def causal_quorum_read(node_url, key):
    """Read with causal consistency using quorum reads"""
    try:
        response = requests.get(f"{node_url}/causal/kv/{key}", timeout=10)
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
    print("🚀 Quorum-Based Causal Consistency Demo")
    print("="*60)
    
    # Default node URL (first node in cluster)
    node_url = "http://localhost:9999"
    
    print(f"📡 Using node: {node_url}")
    print(f"📋 Testing causal consistency with quorum replication")
    
    # Test 1: Basic causal quorum write
    print_result("Causal Quorum Write", *causal_quorum_write(node_url, "causal-key-1", "causal-value-1"))
    
    # Test 2: Causal quorum read
    print_result("Causal Quorum Read", *causal_quorum_read(node_url, "causal-key-1"))
    
    # Test 3: Causal write with vector clock
    vector_clock = {"node1": 1, "node2": 0, "node3": 0}
    print_result("Causal Write with Vector Clock", *causal_quorum_write(node_url, "causal-key-2", "causal-value-2", vector_clock))
    
    # Test 4: Read the key with vector clock
    print_result("Read Causal Key with Vector Clock", *causal_quorum_read(node_url, "causal-key-2"))
    
    # Test 5: Multiple causal writes to test quorum behavior
    print("\n" + "="*60)
    print("🔄 Testing Multiple Causal Quorum Writes")
    print("="*60)
    
    for i in range(3):
        key = f"batch-causal-key-{i}"
        value = f"batch-causal-value-{i}"
        result, status = causal_quorum_write(node_url, key, value)
        print(f"Causal Write {i+1}: {key} = {value}")
        print(f"  Status: {status}")
        print(f"  Success: {'error' not in result}")
        if 'error' not in result:
            print(f"  Successful writes: {result.get('successful_writes', 'N/A')}")
            print(f"  Async replication: {len(result.get('async_replication', []))} nodes")
            print(f"  Vector clock: {result.get('vector_clock', 'N/A')}")
        time.sleep(0.5)  # Small delay between writes
    
    # Test 6: Read all the batch keys
    print("\n" + "="*60)
    print("📖 Testing Causal Quorum Reads")
    print("="*60)
    
    for i in range(3):
        key = f"batch-causal-key-{i}"
        result, status = causal_quorum_read(node_url, key)
        print(f"Causal Read {i+1}: {key}")
        print(f"  Status: {status}")
        print(f"  Success: {'error' not in result}")
        if 'error' not in result:
            print(f"  Value: {result.get('value', 'N/A')}")
            print(f"  Source: {result.get('source', 'N/A')}")
            print(f"  Consistency level: {result.get('consistency_level', 'N/A')}")
            print(f"  Vector clock: {result.get('vector_clock', 'N/A')}")
    
    # Test 7: Read non-existent key
    print_result("Read Non-existent Causal Key", *causal_quorum_read(node_url, "nonexistent-causal-key"))
    
    print("\n" + "="*60)
    print("✅ Quorum-Based Causal Consistency Demo completed!")
    print("="*60)
    print("\n📚 Key Features:")
    print("• Causal consistency with vector clocks")
    print("• Quorum-based replication for high availability")
    print("• Optimistic replication with async background sync")
    print("• Fallback mechanisms when quorum fails")
    print("• Detailed response information for debugging")

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