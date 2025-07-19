#!/usr/bin/env python3
"""
Consistent Hashing Demo Script
Demonstrates how keys are mapped to hash ring and assigned to nodes
"""

import os
import sys
import time
import json
import requests
import subprocess
import threading
import signal
import tempfile
import shutil
import hashlib
from node import RobustSimpleGossipNode, find_free_port
from hashing_lib import initialize_hash_ring, get_responsible_nodes, get_ring_info

# Global variables for cleanup
nodes = []
node_processes = []

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"🎯 {title}")
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

def print_warning(message):
    """Print warning message"""
    print(f"⚠️ {message}")

def print_hash_info(message):
    """Print hash ring specific info"""
    print(f"🔗 {message}")

def cleanup_data_directories():
    """Clean up data directories before starting demo"""
    print_info("Cleaning up old data directories...")
    
    # Clean up demo data directories
    for i in range(1, 4):
        data_dir = f"consistent_hashing_demo_data_{i}"
        if os.path.exists(data_dir):
            try:
                shutil.rmtree(data_dir)
                print_info(f"Removed old data directory: {data_dir}")
            except Exception as e:
                print_warning(f"Could not remove {data_dir}: {e}")
    
    # Also clean up any existing data directories from previous runs
    data_dirs_to_clean = [
        "./data/db-node-1",
        "./data/db-node-2", 
        "./data/db-node-3"
    ]
    
    for data_dir in data_dirs_to_clean:
        if os.path.exists(data_dir):
            try:
                shutil.rmtree(data_dir)
                print_info(f"Removed old data directory: {data_dir}")
            except Exception as e:
                print_warning(f"Could not remove {data_dir}: {e}")

def cleanup():
    """Clean up resources"""
    print_info("Cleaning up...")
    
    # Stop all nodes
    for node in nodes:
        try:
            node.stop()
        except:
            pass
    
    # Kill any remaining processes
    try:
        subprocess.run(['pkill', '-f', 'node.py'], 
                      capture_output=True, timeout=5)
    except:
        pass
    
    # Clean up data directories
    for i in range(1, 4):
        data_dir = f"consistent_hashing_demo_data_{i}"
        if os.path.exists(data_dir):
            try:
                shutil.rmtree(data_dir)
            except:
                pass

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\n🛑 Received interrupt signal. Cleaning up...")
    cleanup()
    sys.exit(0)

def wait_for_node_health(host, port, node_name, timeout=30):
    """Wait for a node to become healthy"""
    print_info(f"Waiting for {node_name} to become healthy...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{host}:{port}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') in ['healthy', 'degraded']:
                    print_success(f"{node_name} is {data.get('status')}")
                    return True
        except:
            pass
        time.sleep(1)
    
    print_error(f"{node_name} failed to become healthy within {timeout} seconds")
    return False

def wait_for_cluster_formation(timeout=60):
    """Wait for cluster to form (all nodes know about each other)"""
    print_info("Waiting for cluster formation...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check if all nodes have 2 peers (excluding self)
            all_healthy = True
            for i, node in enumerate(nodes, 1):
                response = requests.get(f"http://localhost:{node.port}/peers", timeout=2)
                if response.status_code == 200:
                    peers = response.json()
                    if len(peers) < 2:  # Should have 2 other nodes as peers
                        all_healthy = False
                        break
                else:
                    all_healthy = False
                    break
            
            if all_healthy:
                print_success("Cluster formation complete! All nodes are connected.")
                return True
                
        except Exception as e:
            print_warning(f"Error checking cluster formation: {e}")
        
        time.sleep(2)
    
    print_error("Cluster formation failed within timeout")
    return False

def wait_for_cluster_formation_existing(node_addresses):
    """Wait for cluster to form (all nodes know about each other) for existing cluster"""
    print_info("Waiting for cluster formation...")
    
    start_time = time.time()
    while time.time() - start_time < 60: # Adjust timeout for existing cluster
        try:
            # Check if all nodes have 2 peers (excluding self)
            all_healthy = True
            for node_addr in node_addresses:
                host, port = node_addr.split(':')
                try:
                    response = requests.get(f"http://{host}:{port}/peers", timeout=2)
                    if response.status_code == 200:
                        peers = response.json()
                        if len(peers) < 2:  # Should have 2 other nodes as peers
                            all_healthy = False
                            break
                    else:
                        all_healthy = False
                        break
                except:
                    all_healthy = False
                    break
            
            if all_healthy:
                print_success("Cluster formation complete! All nodes are connected.")
                return True
                
        except Exception as e:
            print_warning(f"Error checking cluster formation: {e}")
        
        time.sleep(2)
    
    print_error("Cluster formation failed within timeout")
    return False

def start_node(node_id, host, port, data_dir):
    """Start a node in a separate process"""
    print_info(f"Starting {node_id} on {host}:{port}")
    
    # Create data directory
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir)
    
    # Set environment variables
    env = os.environ.copy()
    env['SEED_NODE_ID'] = node_id
    env['CONFIG_FILE'] = 'config-local.yaml'
    # Note: replication factor is now handled by the main function
    
    # Start the node process
    process = subprocess.Popen([
        sys.executable, 'node.py'
    ], env=env, cwd=os.getcwd())
    
    node_processes.append(process)
    return process

def calculate_key_hash(key):
    """Calculate hash for a key"""
    return hashlib.md5(key.encode()).hexdigest()



def get_responsible_nodes_for_key(key, node_addresses, replication_factor=3):
    """Get responsible nodes for a key by querying the actual nodes"""
    try:
        # Query each node to see which one is responsible for this key
        for node_addr in node_addresses:
            try:
                # Try to get the key from each node's direct endpoint
                response = requests.get(f"http://{node_addr}/kv/{key}/direct", timeout=2)
                if response.status_code == 200:
                    # This node has the data, so it's responsible
                    return {"responsible_nodes": [node_addr]}
            except:
                continue
        
        # If no node has the data, try to write it and see where it goes
        try:
            response = requests.put(
                f"http://{node_addresses[0]}/kv/{key}",
                json={"value": f"test_value_for_{key}"},
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                if 'coordinator' in result:
                    return {"responsible_nodes": [result['coordinator']]}
                elif 'replicas' in result and result['replicas']:
                    return {"responsible_nodes": result['replicas']}
        except:
            pass
        
        # Fallback: use hashing_lib
        responsible_nodes = get_responsible_nodes(key, node_addresses, replication_factor=replication_factor)
        return {"responsible_nodes": responsible_nodes}
        
    except Exception as e:
        print_error(f"Error getting responsible nodes for {key}: {e}")
        return None

def main():
    """Main consistent hashing demo"""
    # Set up signal handlers for cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get replication factor from environment or use default
    replication_factor = int(os.getenv('REPLICATION_FACTOR', '1'))
    
    print_header(f"CONSISTENT HASHING DEMO - REPLICATION FACTOR {replication_factor}")
    print_info("This demo shows how keys are distributed across nodes using consistent hashing")
    print_info(f"With replication factor {replication_factor}, each key is stored on {replication_factor} nodes for redundancy")
    print_info("The hash ring distributes different keys across different primary nodes")
    print_info("This provides load balancing while maintaining data redundancy")
    print_info("")
    print_info("🔧 DYNAMIC REPLICATION FACTOR EXPLANATION:")
    print_info(f"  • Demo replication factor: {replication_factor} (from REPLICATION_FACTOR env var)")
    print_info("  • This affects hash ring calculations and demo logic")
    print_info("  • Actual nodes may have different replication factor (shown in node ring info)")
    print_info("  • Demo uses its replication factor to determine key placement")
    print_info("  • Nodes use their own replication factor for actual data storage")
    print_info("")
    
    # Check if we should use existing cluster (same pattern as replication_demo.py)
    cluster_nodes_env = os.getenv('CLUSTER_NODES')
    use_existing_cluster = cluster_nodes_env is not None
    
    # If no CLUSTER_NODES specified, try to detect existing cluster from config
    if not use_existing_cluster:
        config_file = os.getenv('CONFIG_FILE', 'config-local.yaml')
        if os.path.exists(config_file):
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check if config has cluster.seed_nodes
                if config and 'cluster' in config and 'seed_nodes' in config['cluster']:
                    seed_nodes = config['cluster']['seed_nodes']
                    if seed_nodes:
                        # Convert seed nodes to addresses
                        node_addresses = []
                        for node_info in seed_nodes:
                            if isinstance(node_info, dict):
                                host = node_info.get('host', 'localhost')
                                port = node_info.get('port', 9999)
                                node_addresses.append(f"{host}:{port}")
                            elif isinstance(node_info, str):
                                # Handle string format like "localhost:9999"
                                node_addresses.append(node_info)
                        
                        if node_addresses:
                            use_existing_cluster = True
                            cluster_nodes_env = ','.join(node_addresses)
                            print_info(f"🔍 Auto-detected existing cluster from {config_file}")
                            print_info(f"Found {len(node_addresses)} nodes: {node_addresses}")
            except Exception as e:
                print_warning(f"Could not auto-detect cluster from config: {e}")
    
    if use_existing_cluster:
        print_info("🔗 Using existing cluster")
        node_addresses = cluster_nodes_env.split(',')
        print_info(f"Found {len(node_addresses)} existing nodes: {node_addresses}")
        
        # Verify existing nodes are healthy
        print_step(1, "Verifying existing cluster nodes")
        for i, node_addr in enumerate(node_addresses, 1):
            host, port = node_addr.split(':')
            if not wait_for_node_health(host, int(port), f"Node {i} ({node_addr})"):
                print_error(f"Failed to verify Node {i} ({node_addr})")
                return False
        
        # Wait for cluster formation
        print_step(2, "Verifying cluster formation")
        if not wait_for_cluster_formation_existing(node_addresses):
            print_error("Cluster formation verification failed")
            return False
        
    else:
        print_info("🚀 Starting new cluster for demo")
        # Clean up old data directories before starting
        cleanup_data_directories()
        
        try:
            # Step 1: Start Node 1
            print_step(1, "Starting Node 1 (db-node-1)")
            process1 = start_node("db-node-1", "localhost", 9999, "consistent_hashing_demo_data_1")
            
            if not wait_for_node_health("localhost", 9999, "Node 1"):
                print_error("Failed to start Node 1")
                return False
            
            # Step 2: Start Node 2
            print_step(2, "Starting Node 2 (db-node-2)")
            process2 = start_node("db-node-2", "localhost", 10000, "consistent_hashing_demo_data_2")
            
            if not wait_for_node_health("localhost", 10000, "Node 2"):
                print_error("Failed to start Node 2")
                return False
            
            # Step 3: Start Node 3
            print_step(3, "Starting Node 3 (db-node-3)")
            process3 = start_node("db-node-3", "localhost", 10001, "consistent_hashing_demo_data_3")
            
            if not wait_for_node_health("localhost", 10001, "Node 3"):
                print_error("Failed to start Node 3")
                return False
            
            # Step 4: Wait for cluster formation
            print_step(4, "Waiting for cluster formation")
            if not wait_for_cluster_formation():
                print_error("Cluster formation failed")
                return False
            
            node_addresses = ["localhost:9999", "localhost:10000", "localhost:10001"]
        
        except Exception as e:
            print_error(f"Failed to start cluster: {e}")
            return False
    
    # Step 5: Show hash ring information
    print_step(5 if not use_existing_cluster else 3, "Hash Ring Information")
    
    # Initialize hash ring with our nodes - use the configured replication factor
    initialize_hash_ring(node_addresses, replication_factor=replication_factor)
    
    # Get ring info from hashing_lib
    ring_info = get_ring_info()
    if ring_info:
        print_hash_info(f"Hash ring node count: {ring_info.get('node_count', 'unknown')}")
        print_hash_info(f"Hash ring nodes: {ring_info.get('nodes', [])}")
        print_hash_info(f"Demo hash ring replication factor: {ring_info.get('replication_factor', 'unknown')}")
        print_hash_info(f"Hash ring library available: {ring_info.get('hash_ring_available', 'unknown')}")
    else:
        print_error("Failed to get hash ring information")
    
    # Also get ring info from the node's API
    print_hash_info(f"Note: Node ring info shows the actual replication factor configured on the running nodes")
    print_hash_info(f"      (Demo is using replication factor: {replication_factor})")
    try:
        first_node = node_addresses[0]
        response = requests.get(f"http://{first_node}/ring", timeout=5)
        if response.status_code == 200:
            node_ring_info = response.json()
            print_hash_info(f"Node ring info: {node_ring_info}")
    except Exception as e:
        print_warning(f"Could not get ring info from node API: {e}")
    
    # Step 6: Define test keys and show their mapping
    print_step(6 if not use_existing_cluster else 4, "Key to Hash Ring Mapping")
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
    
    print_hash_info("Calculating key hashes:")
    print_hash_info("=" * 50)
    
    key_hashes = {}
    
    for key in test_keys:
        key_hash = calculate_key_hash(key)
        print_hash_info(f"Key: {key}")
        print_hash_info(f"  Hash: {key_hash}")
        key_hashes[key] = key_hash
        print_hash_info("")
    
    # Step 7: Write data and observe where it goes
    print_step(7 if not use_existing_cluster else 5, "Writing Data and Observing Hash Ring Distribution")
    print_hash_info("Writing data and observing where the hash ring places it:")
    
    key_assignments = {}
    
    for i, key in enumerate(test_keys):
        print_hash_info(f"Writing {key}:")
        
        # Write to different nodes to test routing
        target_node = node_addresses[i % len(node_addresses)]  # Round-robin through nodes
        print_hash_info(f"  📤 Sending request to: {target_node}")
        
        # Write to the target node (should route to responsible node)
        response = requests.put(
            f"http://{target_node}/kv/{key}",
            json={"value": f"value_for_{key}"},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"  ✅ Wrote {key} = value_for_{key}")
            print_hash_info(f"  📍 Coordinator: {result.get('coordinator', 'unknown')}")
            print_hash_info(f"  📍 Replicas: {result.get('replicas', [])}")
            
            # Check which node actually has the data
            data_found = False
            # Use the hash ring to determine which node should be responsible
            from hashing_lib import get_responsible_nodes
            responsible_nodes = get_responsible_nodes(key, node_addresses, replication_factor=replication_factor)
            primary_node = responsible_nodes[0] if responsible_nodes else None
            
            if primary_node:
                print_hash_info(f"  📍 Hash ring says primary node should be: {primary_node}")
                key_assignments[key] = primary_node
                data_found = True
                
                # Verify the data is actually on the primary node
                try:
                    check_response = requests.get(f"http://{primary_node}/kv/{key}/direct", timeout=2)
                    if check_response.status_code == 200:
                        print_hash_info(f"  ✅ Data confirmed on primary node: {primary_node}")
                    else:
                        print_warning(f"  ⚠️ Data not found on primary node {primary_node}")
                except Exception as e:
                    print_warning(f"  ⚠️ Could not verify data on primary node {primary_node}: {e}")
            else:
                print_error(f"  ❌ Could not determine responsible node for {key}")
            
            if not data_found:
                print_error(f"  ❌ Data not found on any node for {key}")
        else:
            print_error(f"  ❌ Failed to write {key}: {response.text}")
        
        time.sleep(1)  # 1 second delay
    
    # Step 8: Show detailed hash ring analysis
    print_step(8 if not use_existing_cluster else 6, "Detailed Hash Ring Analysis")
    print_hash_info("Hash ring distribution analysis:")
    print_hash_info("")
    print_hash_info(f"DEMO REPLICATION FACTOR {replication_factor} EXPLANATION:")
    print_hash_info(f"  • Demo calculates that each key should be stored on {replication_factor} nodes")
    print_hash_info("  • The hash ring distributes DIFFERENT keys to DIFFERENT primary nodes")
    print_hash_info("  • This provides load balancing across the cluster")
    print_hash_info("  • Demo uses this replication factor for hash ring calculations")
    print_hash_info("  • Actual nodes may use different replication factor for storage")
    print_hash_info("")
    
    node_distribution = {}
    for node_addr in node_addresses:
        node_distribution[node_addr] = 0
    
    for key, assigned_node in key_assignments.items():
        if assigned_node in node_distribution:
            node_distribution[assigned_node] += 1
    
    print_hash_info("Key distribution across nodes:")
    for node_addr, count in node_distribution.items():
        print_hash_info(f"  {node_addr}: {count} keys")
    
    # Check if distribution is reasonable (not all on one node)
    max_count = max(node_distribution.values())
    min_count = min(node_distribution.values())
    if max_count - min_count <= 2:  # Allow some variance
        print_success("✅ Data distribution looks balanced")
    else:
        print_warning("⚠️ Data distribution may be uneven")
    
    # Show key assignments
    print_hash_info("\nKey assignments:")
    for key in test_keys:
        assigned_node = key_assignments.get(key)
        if assigned_node:
            print_hash_info(f"  {key} -> {assigned_node}")
    
    # Step 8.5: Test hash ring routing from each node
    print_step(8.5 if not use_existing_cluster else 6.5, "Hash Ring Routing Test")
    print_hash_info("Testing hash ring routing from each node's perspective:")
    
    for node_addr in node_addresses:
        print_hash_info(f"\n--- Testing from {node_addr} ---")
        
        # Test a few keys from this node
        for key in test_keys[:3]:  # Test first 3 keys
            try:
                response = requests.put(
                    f"http://{node_addr}/kv/{key}_from_{node_addr.split(':')[1]}",
                    json={"value": f"test_from_{node_addr}"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print_hash_info(f"  ✅ {key}_from_{node_addr.split(':')[1]} -> {result.get('coordinator', 'unknown')}")
                else:
                    print_warning(f"  ⚠️ Failed to write {key}_from_{node_addr.split(':')[1]}")
            except Exception as e:
                print_warning(f"  ⚠️ Error testing from {node_addr}: {e}")
    
    # Step 9: Cleanup
    print_step(9 if not use_existing_cluster else 7, "Demo Complete")
    print_success("Consistent hashing demo completed successfully!")
    print_info("Key insights:")
    print_info("  • Hash ring distributes keys across nodes")
    print_info(f"  • Demo replication factor {replication_factor} used for calculations")
    print_info("  • Load balancing is achieved through key distribution")
    print_info("  • Each node handles a subset of the total keys")
    print_info("  • Demo replication factor is separate from node replication factor")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print_success("Consistent hashing demo completed successfully!")
    else:
        print_error("Consistent hashing demo failed!")
        sys.exit(1) 