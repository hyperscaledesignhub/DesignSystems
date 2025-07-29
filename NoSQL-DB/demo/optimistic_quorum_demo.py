#!/usr/bin/env python3
"""
Optimistic Quorum Write Demo
Demonstrates how quorum writes work with optimistic replication:
1. Write to self (fastest)
2. Write to one more node to meet quorum
3. Return success immediately
4. Replicate to remaining nodes asynchronously
"""

import sys
import os
import time
import threading
import requests
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set config file path
os.environ['CONFIG_FILE'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml')

from distributed.node import RobustSimpleGossipNode, find_free_port

def create_test_cluster():
    """Create a 3-node test cluster"""
    print("🚀 Creating 3-node test cluster...")
    
    # Create nodes
    node1 = RobustSimpleGossipNode("node1", "localhost", find_free_port())
    node2 = RobustSimpleGossipNode("node2", "localhost", find_free_port())
    node3 = RobustSimpleGossipNode("node3", "localhost", find_free_port())
    
    # Start nodes
    node1.start()
    node2.start()
    node3.start()
    
    # Wait for nodes to start
    time.sleep(2)
    
    # Join nodes to form cluster
    print("🔗 Joining nodes to form cluster...")
    node2.join(node1.address)
    node3.join(node1.address)
    
    # Wait for cluster formation
    time.sleep(3)
    
    return node1, node2, node3

def test_optimistic_quorum_write(node1, node2, node3):
    """Test optimistic quorum write behavior"""
    print("\n" + "="*60)
    print("🧪 TESTING OPTIMISTIC QUORUM WRITE")
    print("="*60)
    
    # Test key that should be distributed across all 3 nodes
    test_key = "optimistic-test-key"
    test_value = "optimistic-test-value"
    
    print(f"\n📝 Writing key '{test_key}' with value '{test_value}'")
    print(f"📊 Expected: RF=3, WQ=2 (write to 2 nodes, return success, async replicate to 3rd)")
    
    # Perform the write
    start_time = time.time()
    result = node1.handle_put_key(test_key, test_value)
    end_time = time.time()
    
    print(f"\n⏱️  Write completed in {end_time - start_time:.3f} seconds")
    print(f"📋 Result: {json.dumps(result, indent=2)}")
    
    # Verify the behavior
    if "error" not in result:
        print(f"\n✅ SUCCESS: Quorum write completed!")
        print(f"   • Successful writes: {result['successful_writes']}")
        print(f"   • Write quorum required: {result['write_quorum']}")
        print(f"   • Replication factor: {result['replication_factor']}")
        print(f"   • Optimistic: {result.get('optimistic', False)}")
        
        if 'async_replication' in result:
            print(f"   • Async replication nodes: {result['async_replication']}")
            print(f"   • Async replication count: {len(result['async_replication'])}")
        
        # Wait a bit for async replication
        if 'async_replication' in result and result['async_replication']:
            print(f"\n⏳ Waiting 3 seconds for async replication to complete...")
            time.sleep(3)
        
        # Verify data on all nodes
        print(f"\n🔍 Verifying data on all nodes...")
        verify_data_on_all_nodes(node1, node2, node3, test_key, test_value)
        
    else:
        print(f"\n❌ FAILURE: {result['error']}")

def verify_data_on_all_nodes(node1, node2, node3, key, expected_value):
    """Verify that data exists on all nodes"""
    nodes = [("node1", node1), ("node2", node2), ("node3", node3)]
    
    for node_name, node in nodes:
        try:
            result = node.handle_get_key(key)
            if "error" not in result:
                actual_value = result.get("value")
                if actual_value == expected_value:
                    print(f"   ✅ {node_name}: Found correct value '{actual_value}'")
                else:
                    print(f"   ❌ {node_name}: Found wrong value '{actual_value}' (expected '{expected_value}')")
            else:
                print(f"   ❌ {node_name}: Error - {result['error']}")
        except Exception as e:
            print(f"   ❌ {node_name}: Exception - {e}")

def test_quorum_info_endpoint(node1):
    """Test the quorum info endpoint"""
    print(f"\n" + "="*60)
    print("🔍 TESTING QUORUM INFO ENDPOINT")
    print("="*60)
    
    test_key = "quorum-info-test"
    
    # Get quorum info
    quorum_info = node1.get_quorum_info(test_key)
    
    print(f"\n📊 Quorum Info for key '{test_key}':")
    print(json.dumps(quorum_info, indent=2))
    
    # Test HTTP endpoint
    try:
        with node1.app.test_client() as client:
            response = client.get(f'/quorum/{test_key}')
            if response.status_code == 200:
                data = response.get_json()
                print(f"\n🌐 HTTP Quorum Info Endpoint:")
                print(json.dumps(data, indent=2))
            else:
                print(f"❌ HTTP endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ HTTP endpoint test failed: {e}")

def test_performance_comparison(node1):
    """Compare performance of optimistic vs traditional approach"""
    print(f"\n" + "="*60)
    print("⚡ PERFORMANCE COMPARISON")
    print("="*60)
    
    test_key = "performance-test"
    test_value = "performance-test-value"
    
    # Test optimistic write (current implementation)
    print(f"\n🚀 Testing optimistic quorum write...")
    start_time = time.time()
    result = node1.handle_put_key(test_key, test_value)
    optimistic_time = time.time() - start_time
    
    print(f"   ⏱️  Optimistic write time: {optimistic_time:.3f} seconds")
    print(f"   📊 Result: {'SUCCESS' if 'error' not in result else 'FAILURE'}")
    
    # Simulate what traditional approach would be (writing to all nodes)
    print(f"\n🐌 Simulating traditional approach (writing to all nodes)...")
    start_time = time.time()
    
    # Get responsible nodes
    responsible_nodes = node1.state.get_responsible_nodes(test_key + "-traditional")
    
    # Write to all nodes sequentially
    for node in responsible_nodes:
        try:
            if node == node1.address:
                # Local write
                node1.local_data[test_key + "-traditional"] = test_value
            else:
                # Remote write
                node_address = node1._get_node_address(node)
                if node_address:
                    response = requests.put(
                        f"http://{node_address}/kv/{test_key}-traditional/direct",
                        json={"value": test_value, "timestamp": time.time()},
                        timeout=2
                    )
        except Exception as e:
            print(f"   ❌ Error writing to {node}: {e}")
    
    traditional_time = time.time() - start_time
    
    print(f"   ⏱️  Traditional write time: {traditional_time:.3f} seconds")
    
    # Calculate speedup
    if traditional_time > 0:
        speedup = traditional_time / optimistic_time
        print(f"\n📈 Performance Improvement:")
        print(f"   • Optimistic: {optimistic_time:.3f}s")
        print(f"   • Traditional: {traditional_time:.3f}s")
        print(f"   • Speedup: {speedup:.2f}x faster")

def main():
    """Main demo function"""
    print("🎯 OPTIMISTIC QUORUM WRITE DEMO")
    print("="*60)
    print("This demo shows how quorum writes work with optimistic replication:")
    print("1. Write to self (fastest)")
    print("2. Write to one more node to meet quorum")
    print("3. Return success immediately")
    print("4. Replicate to remaining nodes asynchronously")
    print("="*60)
    
    try:
        # Create test cluster
        node1, node2, node3 = create_test_cluster()
        
        # Test optimistic quorum write
        test_optimistic_quorum_write(node1, node2, node3)
        
        # Test quorum info endpoint
        test_quorum_info_endpoint(node1)
        
        # Test performance comparison
        test_performance_comparison(node1)
        
        print(f"\n" + "="*60)
        print("✅ DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up...")
        try:
            node1.stop()
            node2.stop()
            node3.stop()
            print("✅ Cleanup completed")
        except:
            pass

if __name__ == "__main__":
    main() 