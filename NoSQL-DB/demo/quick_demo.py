#!/usr/bin/env python3
"""
Quick Demo: Persistence and Anti-Entropy Features
Simple command-line demonstration for stakeholders
"""

import os
import sys
import time
import json
import requests
import subprocess
from node import RobustSimpleGossipNode, find_free_port

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"🎬 {title}")
    print("="*60)

def print_step(step, description):
    """Print a formatted step"""
    print(f"\n{step}. {description}")
    print("-" * 40)

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️ {message}")

def demo_persistence():
    """Demonstrate data persistence"""
    print_header("DATA PERSISTENCE DEMONSTRATION")
    
    # Create node
    print_step(1, "Creating node with persistence")
    port = find_free_port()
    data_dir = "demo_persistence_data"
    
    if os.path.exists(data_dir):
        import shutil
        shutil.rmtree(data_dir)
    os.makedirs(data_dir)
    
    node = RobustSimpleGossipNode(
        node_id="demo-persistence-node",
        host="localhost",
        port=port,
        data_dir=data_dir
    )
    
    print_success(f"Node created on port {port}")
    
    # Start node
    print_step(2, "Starting node")
    node.start()
    time.sleep(2)
    print_success("Node started successfully")
    
    # Write data
    print_step(3, "Writing test data")
    test_data = {
        "user:admin": "admin@company.com",
        "config:version": "1.0.0",
        "session:abc123": "active",
        "file:document.txt": "important content"
    }
    
    for key, value in test_data.items():
        response = requests.put(
            f"http://localhost:{port}/kv/{key}",
            json={"value": value}
        )
        if response.status_code == 200:
            print_success(f"Wrote {key} = {value}")
        else:
            print_error(f"Failed to write {key}")
    
    # Show persistence stats
    print_step(4, "Showing persistence statistics")
    response = requests.get(f"http://localhost:{port}/persistence/stats")
    if response.status_code == 200:
        stats = response.json()
        print_info(f"Cache entries: {stats.get('cache_entries', 0)}")
        print_info(f"WAL size: {stats.get('wal_size_bytes', 0)} bytes")
        print_info(f"SSTable files: {stats.get('sstable_files', 0)}")
    
    # Simulate crash
    print_step(5, "Simulating node crash")
    node.stop()
    print_success("Node stopped (simulated crash)")
    
    time.sleep(2)
    
    # Restart node
    print_step(6, "Restarting node")
    node.start()
    time.sleep(3)
    print_success("Node restarted")
    
    # Verify recovery
    print_step(7, "Verifying data recovery")
    recovered_count = 0
    for key, expected_value in test_data.items():
        response = requests.get(f"http://localhost:{port}/kv/{key}")
        if response.status_code == 200:
            result = response.json()
            if result.get('value') == expected_value:
                print_success(f"Recovered {key} = {result['value']}")
                recovered_count += 1
            else:
                print_error(f"Data mismatch for {key}")
        else:
            print_error(f"Failed to recover {key}")
    
    recovery_rate = (recovered_count / len(test_data)) * 100
    print_info(f"Recovery rate: {recovery_rate:.1f}%")
    
    if recovery_rate == 100:
        print_success("PERFECT DATA PERSISTENCE!")
    else:
        print_error("Some data was lost during recovery")
    
    # Cleanup
    node.stop()
    print_info("Demo completed")

def demo_anti_entropy():
    """Demonstrate anti-entropy synchronization"""
    print_header("ANTI-ENTROPY SYNCHRONIZATION DEMONSTRATION")
    
    # Create two nodes
    print_step(1, "Creating two nodes")
    port1 = find_free_port()
    port2 = find_free_port()
    
    data_dir1 = "demo_anti_entropy_data_1"
    data_dir2 = "demo_anti_entropy_data_2"
    
    for data_dir in [data_dir1, data_dir2]:
        if os.path.exists(data_dir):
            import shutil
            shutil.rmtree(data_dir)
        os.makedirs(data_dir)
    
    node1 = RobustSimpleGossipNode(
        node_id="demo-node-1",
        host="localhost",
        port=port1,
        data_dir=data_dir1
    )
    
    node2 = RobustSimpleGossipNode(
        node_id="demo-node-2", 
        host="localhost",
        port=port2,
        data_dir=data_dir2
    )
    
    print_success(f"Node 1 created on port {port1}")
    print_success(f"Node 2 created on port {port2}")
    
    # Start nodes
    print_step(2, "Starting nodes")
    node1.start()
    node2.start()
    time.sleep(2)
    print_success("Both nodes started")
    
    # Join nodes
    print_step(3, "Joining nodes to form cluster")
    response = requests.post(
        f"http://localhost:{port2}/join",
        json={"peer_address": f"localhost:{port1}"}
    )
    if response.status_code == 200:
        print_success("Nodes joined successfully")
    else:
        print_error("Failed to join nodes")
    
    time.sleep(2)
    
    # Write different data to each node
    print_step(4, "Writing different data to each node")
    
    node1_data = {
        "user:alice": "alice@company.com",
        "config:theme": "dark"
    }
    
    node2_data = {
        "user:bob": "bob@company.com",
        "config:theme": "light"
    }
    
    print_info("Writing to Node 1:")
    for key, value in node1_data.items():
        response = requests.put(
            f"http://localhost:{port1}/kv/{key}",
            json={"value": value}
        )
        if response.status_code == 200:
            print_success(f"Wrote {key} = {value}")
    
    print_info("Writing to Node 2:")
    for key, value in node2_data.items():
        response = requests.put(
            f"http://localhost:{port2}/kv/{key}",
            json={"value": value}
        )
        if response.status_code == 200:
            print_success(f"Wrote {key} = {value}")
    
    # Show initial state
    print_step(5, "Showing initial state")
    print_info(f"Node 1 has {len(node1_data)} keys")
    print_info(f"Node 2 has {len(node2_data)} keys")
    
    # Trigger anti-entropy
    print_step(6, "Triggering anti-entropy synchronization")
    response = requests.post(f"http://localhost:{port1}/anti-entropy/trigger")
    if response.status_code == 200:
        print_success("Anti-entropy triggered on Node 1")
    
    response = requests.post(f"http://localhost:{port2}/anti-entropy/trigger")
    if response.status_code == 200:
        print_success("Anti-entropy triggered on Node 2")
    
    print_info("Waiting for synchronization...")
    time.sleep(5)
    
    # Verify synchronization
    print_step(7, "Verifying synchronization")
    all_keys = set(node1_data.keys()) | set(node2_data.keys())
    
    print_info("Checking Node 1:")
    node1_sync = 0
    for key in all_keys:
        response = requests.get(f"http://localhost:{port1}/kv/{key}")
        if response.status_code == 200:
            result = response.json()
            expected_value = node1_data.get(key) or node2_data.get(key)
            if result.get('value') == expected_value:
                print_success(f"Node 1 has {key} = {result['value']}")
                node1_sync += 1
            else:
                print_error(f"Node 1 missing {key}")
    
    print_info("Checking Node 2:")
    node2_sync = 0
    for key in all_keys:
        response = requests.get(f"http://localhost:{port2}/kv/{key}")
        if response.status_code == 200:
            result = response.json()
            expected_value = node1_data.get(key) or node2_data.get(key)
            if result.get('value') == expected_value:
                print_success(f"Node 2 has {key} = {result['value']}")
                node2_sync += 1
            else:
                print_error(f"Node 2 missing {key}")
    
    sync_rate1 = (node1_sync / len(all_keys)) * 100
    sync_rate2 = (node2_sync / len(all_keys)) * 100
    
    print_info(f"Node 1 sync rate: {sync_rate1:.1f}%")
    print_info(f"Node 2 sync rate: {sync_rate2:.1f}%")
    
    if sync_rate1 == 100 and sync_rate2 == 100:
        print_success("PERFECT ANTI-ENTROPY SYNCHRONIZATION!")
    else:
        print_error("Some data was not synchronized")
    
    # Cleanup
    node1.stop()
    node2.stop()
    print_info("Demo completed")

def demo_merkle_trees():
    """Demonstrate Merkle tree snapshots"""
    print_header("MERKLE TREE SNAPSHOTS DEMONSTRATION")
    
    # Create node
    print_step(1, "Creating node")
    port = find_free_port()
    data_dir = "demo_merkle_data"
    
    if os.path.exists(data_dir):
        import shutil
        shutil.rmtree(data_dir)
    os.makedirs(data_dir)
    
    node = RobustSimpleGossipNode(
        node_id="demo-merkle-node",
        host="localhost",
        port=port,
        data_dir=data_dir
    )
    
    print_success(f"Node created on port {port}")
    
    # Start node
    print_step(2, "Starting node")
    node.start()
    time.sleep(2)
    print_success("Node started")
    
    # Write data
    print_step(3, "Writing data for Merkle tree")
    test_data = {
        "file:doc1.txt": "content1",
        "file:doc2.txt": "content2",
        "file:doc3.txt": "content3",
        "config:version": "1.0.0"
    }
    
    for key, value in test_data.items():
        response = requests.put(
            f"http://localhost:{port}/kv/{key}",
            json={"value": value}
        )
        if response.status_code == 200:
            print_success(f"Wrote {key} = {value}")
    
    # Generate Merkle snapshot
    print_step(4, "Generating Merkle tree snapshot")
    response = requests.get(f"http://localhost:{port}/merkle/snapshot")
    
    if response.status_code == 200:
        snapshot = response.json()
        print_success("Merkle snapshot generated")
        print_info(f"Node ID: {snapshot.get('node_id')}")
        print_info(f"Timestamp: {snapshot.get('timestamp')}")
        print_info(f"Tree height: {snapshot.get('tree_height', 'N/A')}")
        print_info(f"Root hash: {snapshot.get('root_hash', 'N/A')[:16]}...")
        print_info(f"Total keys: {len(snapshot.get('keys', []))}")
        
        # Show sample keys
        keys = snapshot.get('keys', [])
        if keys:
            print_info("Sample keys in snapshot:")
            for key in keys[:3]:
                print_info(f"  - {key}")
            if len(keys) > 3:
                print_info(f"  - ... and {len(keys) - 3} more")
    else:
        print_error("Failed to generate Merkle snapshot")
    
    # Cleanup
    node.stop()
    print_info("Demo completed")

def main():
    """Main demo runner"""
    print("🎬 QUICK PERSISTENCE & ANTI-ENTROPY DEMO")
    print("=" * 60)
    print("Choose a demonstration:")
    print("1. Data Persistence Demo")
    print("2. Anti-Entropy Synchronization Demo") 
    print("3. Merkle Tree Snapshots Demo")
    print("4. Run All Demos")
    print("5. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                demo_persistence()
            elif choice == "2":
                demo_anti_entropy()
            elif choice == "3":
                demo_merkle_trees()
            elif choice == "4":
                demo_persistence()
                demo_anti_entropy()
                demo_merkle_trees()
                print_header("ALL DEMOS COMPLETED")
                print_success("All demonstrations completed successfully!")
            elif choice == "5":
                print_info("Goodbye!")
                break
            else:
                print_error("Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print_info("\nDemo interrupted by user")
            break
        except Exception as e:
            print_error(f"Demo failed: {e}")

if __name__ == "__main__":
    main() 