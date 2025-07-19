#!/usr/bin/env python3
"""
Test script to debug hash ring distribution
"""

import hashlib
from hashing_lib import initialize_hash_ring, get_responsible_nodes, get_ring_info

def test_hash_ring_distribution():
    """Test hash ring distribution with 3 nodes"""
    
    # Initialize hash ring with 3 nodes
    nodes = ["localhost:9999", "localhost:10000", "localhost:10001"]
    initialize_hash_ring(nodes, replication_factor=1)
    
    # Get ring info
    ring_info = get_ring_info()
    print(f"Ring info: {ring_info}")
    
    # Test keys
    test_keys = [
        "user:alice",
        "user:bob", 
        "user:charlie",
        "config:database",
        "config:cache",
        "session:abc123",
        "session:def456",
        "file:document1.txt",
        "file:document2.txt",
        "demo:consistent-hashing"
    ]
    
    print("\nTesting key distribution:")
    print("=" * 50)
    
    distribution = {}
    
    for key in test_keys:
        responsible_nodes = get_responsible_nodes(key, nodes, replication_factor=1)
        primary_node = responsible_nodes[0] if responsible_nodes else "none"
        
        distribution[primary_node] = distribution.get(primary_node, 0) + 1
        
        key_hash = hashlib.md5(key.encode()).hexdigest()
        print(f"{key_hash[:8]}... -> {key} -> {primary_node}")
    
    print("\nDistribution summary:")
    print("=" * 30)
    for node, count in distribution.items():
        print(f"{node}: {count} keys")
    
    # Check if distribution is balanced
    if len(distribution) > 1:
        print("✅ Keys are distributed across multiple nodes")
    else:
        print("❌ All keys are mapped to the same node")
        print("This indicates a problem with the hash ring implementation")

if __name__ == "__main__":
    test_hash_ring_distribution() 