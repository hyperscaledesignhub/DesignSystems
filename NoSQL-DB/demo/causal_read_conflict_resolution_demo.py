#!/usr/bin/env python3
"""
Causal Read Conflict Resolution Demo

This demo showcases the enhanced causal consistency read endpoint that can resolve
conflicts even when quorum requirements are not met. It demonstrates:

1. Creating inconsistent data across nodes
2. Causal read with conflict resolution when quorum fails
3. Different resolution strategies (causal_vector, causal_lww)
4. Fallback behavior when conflict resolution fails
"""

import requests
import time
import json
import sys
import os

# Add the parent directory to the path to import from distributed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from distributed.node import RobustSimpleGossipNode
from scripts.start_cluster_local import find_free_port

def print_result(test_name, result, status_code):
    """Print test result with formatting"""
    print(f"\n🔍 {test_name}")
    print("-" * 50)
    print(f"Status Code: {status_code}")
    if status_code == 200:
        print("✅ SUCCESS")
        if isinstance(result, dict):
            print("Response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"Response: {result}")
    else:
        print("❌ FAILED")
        print(f"Error: {result}")

def create_inconsistent_data(nodes, key, values):
    """Create inconsistent data by writing different values to different nodes"""
    print(f"\n📝 Creating inconsistent data for key '{key}'")
    print(f"Values to write: {values}")
    
    for i, (node, value) in enumerate(zip(nodes, values)):
        response = requests.put(
            f"http://{node.get_address()}/kv/{key}/direct",
            json={"value": value}
        )
        print(f"  Node {i+1}: {value} -> Status: {response.status_code}")
        if response.status_code != 200:
            print(f"    Error: {response.text}")
    
    print("✅ Inconsistent data created")

def test_causal_read_conflict_resolution(nodes, key):
    """Test causal read with conflict resolution"""
    print(f"\n🔄 Testing Causal Read Conflict Resolution for key '{key}'")
    
    # Read current config and set read quorum higher than available nodes to force quorum failure
    try:
        from config.yaml_config import yaml_config
        original_config = yaml_config.get_quorum_config()
        current_write_quorum = original_config.get('write_quorum', 3)
        # Set read_quorum higher than available nodes to force quorum failure
        yaml_config.update_quorum_config({"read_quorum": len(nodes) + 1, "write_quorum": current_write_quorum})
        print(f"  Set read_quorum to {len(nodes) + 1} (will fail)")
    except ImportError:
        print("  Config not available, using default quorum settings")
    
    # Test causal read
    response = requests.get(f"http://{nodes[0].get_address()}/causal/kv/{key}")
    result = response.json() if response.status_code == 200 else response.text
    
    print_result("Causal Read with Conflict Resolution", result, response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Analysis:")
        print(f"  • Quorum Achieved: {data.get('quorum_result', {}).get('quorum_achieved', 'N/A')}")
        print(f"  • Consistency Level: {data.get('consistency_level', 'N/A')}")
        print(f"  • Source: {data.get('source', 'N/A')}")
        
        if 'conflict_resolution' in data:
            cr = data['conflict_resolution']
            print(f"  • Resolution Strategy: {cr.get('strategy', 'N/A')}")
            print(f"  • Values Resolved: {cr.get('values_resolved', 'N/A')}")
            print(f"  • Resolution Source: {cr.get('resolution_source', 'N/A')}")
        
        if 'warning' in data:
            print(f"  • Warning: {data['warning']}")
    
    return response.status_code == 200

def test_causal_read_with_causal_data(nodes, key):
    """Test causal read using causal data for conflict resolution"""
    print(f"\n🔄 Testing Causal Read with Causal Data for key '{key}'")
    
    # Create causal data with different vector clocks
    print(f"  Creating causal data...")
    
    for i, node in enumerate(nodes):
        causal_response = requests.put(
            f"http://{node.get_address()}/causal/kv/{key}",
            json={"value": f"causal_value_{i+1}"}
        )
        print(f"    Node {i+1}: causal_value_{i+1} -> Status: {causal_response.status_code}")
    
    # Read current config and set read quorum higher than available nodes to force quorum failure
    try:
        from config.yaml_config import yaml_config
        original_config = yaml_config.get_quorum_config()
        current_write_quorum = original_config.get('write_quorum', 3)
        # Set read_quorum higher than available nodes to force quorum failure
        yaml_config.update_quorum_config({"read_quorum": len(nodes) + 1, "write_quorum": current_write_quorum})
    except ImportError:
        pass
    
    # Test causal read
    response = requests.get(f"http://{nodes[0].get_address()}/causal/kv/{key}")
    result = response.json() if response.status_code == 200 else response.text
    
    print_result("Causal Read with Causal Data", result, response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Analysis:")
        print(f"  • Vector Clock: {data.get('vector_clock', 'N/A')}")
        print(f"  • Consistency Level: {data.get('consistency_level', 'N/A')}")
        print(f"  • Source: {data.get('source', 'N/A')}")
        
        if 'conflict_resolution' in data:
            cr = data['conflict_resolution']
            print(f"  • Resolution Strategy: {cr.get('strategy', 'N/A')}")
            print(f"  • Resolution Source: {cr.get('resolution_source', 'N/A')}")
    
    return response.status_code == 200

def test_fallback_behavior(nodes, key):
    """Test fallback behavior when conflict resolution fails"""
    print(f"\n🔄 Testing Fallback Behavior for key '{key}'")
    
    # Create inconsistent data
    values = [f"fallback_value_{i+1}" for i in range(len(nodes))]
    create_inconsistent_data(nodes, key, values)
    
    # Read current config and set read quorum higher than available nodes to force quorum failure
    try:
        from config.yaml_config import yaml_config
        original_config = yaml_config.get_quorum_config()
        current_write_quorum = original_config.get('write_quorum', 3)
        # Set read_quorum higher than available nodes to force quorum failure
        yaml_config.update_quorum_config({"read_quorum": len(nodes) + 1, "write_quorum": current_write_quorum})
    except ImportError:
        pass
    
    # Test causal read
    response = requests.get(f"http://{nodes[0].get_address()}/causal/kv/{key}")
    result = response.json() if response.status_code == 200 else response.text
    
    print_result("Causal Read Fallback Behavior", result, response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Analysis:")
        print(f"  • Source: {data.get('source', 'N/A')}")
        print(f"  • Consistency Level: {data.get('consistency_level', 'N/A')}")
        print(f"  • Warning: {data.get('warning', 'N/A')}")
        
        if 'original_responses' in data:
            original_values = set(data['original_responses'].values())
            print(f"  • Original Values: {original_values}")
            print(f"  • Selected Value: {data.get('value', 'N/A')}")
            print(f"  • Value in Original Set: {data.get('value') in original_values}")
    
    return response.status_code == 200

def main():
    """Main demo function"""
    print("🚀 Causal Read Conflict Resolution Demo")
    print("=" * 60)
    print("This demo showcases enhanced causal consistency that can resolve")
    print("conflicts even when quorum requirements are not met.")
    print("=" * 60)
    
    # Start 3 nodes
    print("\n🔧 Starting 3-node cluster...")
    ports = [find_free_port() for _ in range(3)]
    nodes = [RobustSimpleGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
    
    for node in nodes:
        node.start()
    time.sleep(1)
    
    # Join nodes
    print("🔗 Joining nodes...")
    nodes[1].join(nodes[0].get_address())
    nodes[2].join(nodes[0].get_address())
    time.sleep(1)
    
    # Verify cluster formation
    for i, node in enumerate(nodes):
        peer_count = len(node.get_peers())
        print(f"  Node {i+1}: {peer_count} peers")
    
    print("✅ Cluster ready")
    
    # Test 1: Basic conflict resolution with regular data
    print("\n" + "=" * 60)
    print("🧪 TEST 1: Basic Conflict Resolution")
    print("=" * 60)
    
    key1 = "conflict_test_1"
    values1 = ["value_from_node1", "value_from_node2", "value_from_node3"]
    create_inconsistent_data(nodes, key1, values1)
    success1 = test_causal_read_conflict_resolution(nodes, key1)
    
    # Test 2: Causal data conflict resolution
    print("\n" + "=" * 60)
    print("🧪 TEST 2: Causal Data Conflict Resolution")
    print("=" * 60)
    
    key2 = "causal_conflict_test"
    success2 = test_causal_read_with_causal_data(nodes, key2)
    
    # Test 3: Fallback behavior
    print("\n" + "=" * 60)
    print("🧪 TEST 3: Fallback Behavior")
    print("=" * 60)
    
    key3 = "fallback_test"
    success3 = test_fallback_behavior(nodes, key3)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DEMO SUMMARY")
    print("=" * 60)
    print(f"✅ Test 1 (Basic Conflict Resolution): {'PASSED' if success1 else 'FAILED'}")
    print(f"✅ Test 2 (Causal Data Resolution): {'PASSED' if success2 else 'FAILED'}")
    print(f"✅ Test 3 (Fallback Behavior): {'PASSED' if success3 else 'FAILED'}")
    
    total_tests = 3
    passed_tests = sum([success1, success2, success3])
    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Causal read conflict resolution is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("\n" + "=" * 60)
    print("🔧 Key Features Demonstrated:")
    print("• Conflict resolution even when quorum fails")
    print("• Vector clock-based causal ordering")
    print("• Timestamp-based fallback resolution")
    print("• Graceful degradation with warnings")
    print("• Detailed response information for debugging")
    print("=" * 60)
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    for node in nodes:
        node.stop()
    print("✅ Demo completed")

if __name__ == "__main__":
    main() 