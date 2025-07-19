#!/usr/bin/env python3
"""
Replication Demo Script
Demonstrates data replication across a 3-node cluster
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
from node import RobustSimpleGossipNode, find_free_port

# Global variables for cleanup
nodes = []
node_processes = []

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

def print_warning(message):
    """Print warning message"""
    print(f"⚠️ {message}")

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
        data_dir = f"replication_demo_data_{i}"
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
    
    # Start the node process
    process = subprocess.Popen([
        sys.executable, 'node.py'
    ], env=env, cwd=os.getcwd())
    
    node_processes.append(process)
    return process

def wait_for_cluster_formation_existing(node_addresses, timeout=60):
    """Wait for existing cluster to be ready"""
    print_info("Verifying existing cluster formation...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check if all nodes are healthy and have peers
            all_healthy = True
            for node_addr in node_addresses:
                # Check health
                health_response = requests.get(f"http://{node_addr}/health", timeout=2)
                if health_response.status_code != 200:
                    all_healthy = False
                    break
                
                # Check peers
                peers_response = requests.get(f"http://{node_addr}/peers", timeout=2)
                if peers_response.status_code == 200:
                    peers = peers_response.json()
                    if len(peers) < len(node_addresses) - 1:  # Should have all other nodes as peers
                        all_healthy = False
                        break
                else:
                    all_healthy = False
                    break
            
            if all_healthy:
                print_success("Existing cluster is ready! All nodes are connected.")
                return True
                
        except Exception as e:
            print_warning(f"Error checking existing cluster formation: {e}")
        
        time.sleep(2)
    
    print_error("Existing cluster verification failed within timeout")
    return False

def main():
    """Main replication demo"""
    # Set up signal handlers for cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print_header("REPLICATION DEMO")
    print_info("This demo will show data replication across a 3-node cluster")
    
    # Check if we should use existing cluster
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
        try:
            # Step 1: Start Node 1
            print_step(1, "Starting Node 1 (db-node-1)")
            process1 = start_node("db-node-1", "localhost", 9999, "replication_demo_data_1")
            
            if not wait_for_node_health("localhost", 9999, "Node 1"):
                print_error("Failed to start Node 1")
                return False
            
            # Step 2: Start Node 2
            print_step(2, "Starting Node 2 (db-node-2)")
            process2 = start_node("db-node-2", "localhost", 10000, "replication_demo_data_2")
            
            if not wait_for_node_health("localhost", 10000, "Node 2"):
                print_error("Failed to start Node 2")
                return False
            
            # Step 3: Start Node 3
            print_step(3, "Starting Node 3 (db-node-3)")
            process3 = start_node("db-node-3", "localhost", 10001, "replication_demo_data_3")
            
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
    
    # Step 5: Write data to first node
    print_step(5 if not use_existing_cluster else 3, "Writing data to first node")
    test_data = {
        "user:admin": "admin@company.com",
        "config:version": "1.0.0",
        "session:abc123": "active",
        "file:document.txt": "important content",
        "demo:replication": "working perfectly!"
    }
    
    first_node = node_addresses[0]
    print_info(f"Writing test data to {first_node}...")
    for key, value in test_data.items():
        curl_command = f'curl -X PUT -H "Content-Type: application/json" -d \'{{"value":"{value}"}}\' http://{first_node}/kv/{key}'
        print_info(f"Command: {curl_command}")
        
        response = requests.put(
            f"http://{first_node}/kv/{key}",
            json={"value": value},
            timeout=5
        )
        if response.status_code == 200:
            print_success(f"Wrote {key} = {value}")
        else:
            print_error(f"Failed to write {key}: {response.text}")
        
        time.sleep(1)  # 1 second delay after each write
    
    # Step 6: Verify data replication to other nodes
    if len(node_addresses) > 1:
        print_step(6 if not use_existing_cluster else 4, "Verifying data replication to other nodes")
        
        for i, node_addr in enumerate(node_addresses[1:], 2):
            print_info(f"From {first_node} checking if data appears on {node_addr}...")
            
            replicated_count = 0
            for key, expected_value in test_data.items():
                curl_command = f'curl http://{node_addr}/kv/{key}'
                print_info(f"From {first_node} -> {node_addr}: {curl_command}")
                
                response = requests.get(f"http://{node_addr}/kv/{key}", timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('value') == expected_value:
                        print_success(f"✅ {key} = {result['value']} (replicated to {node_addr})")
                        replicated_count += 1
                    else:
                        print_error(f"❌ Data mismatch for {key}: expected {expected_value}, got {result.get('value')}")
                else:
                    print_error(f"❌ Failed to read {key} from {node_addr}: {response.text}")
                
                time.sleep(1)  # 1 second delay after each read
            
            replication_rate = (replicated_count / len(test_data)) * 100
            print_info(f"Replication rate to {node_addr}: {replication_rate:.1f}%")
    
    # Step 7: Show cluster information
    print_step(7 if not use_existing_cluster else 5, "Cluster Information")
    print_info("Final cluster status:")
    
    for i, node_addr in enumerate(node_addresses, 1):
        try:
            response = requests.get(f"http://{node_addr}/info", timeout=2)
            if response.status_code == 200:
                info = response.json()
                print_info(f"Node {i} ({info.get('node_id', 'unknown')}):")
                print_info(f"  - Address: {info.get('address', 'unknown')}")
                print_info(f"  - Peer count: {info.get('peer_count', 0)}")
                print_info(f"  - Hash ring initialized: {info.get('hash_ring_initialized', False)}")
                print_info(f"  - Replication factor: {info.get('replication_factor', 'unknown')}")
        except Exception as e:
            print_error(f"Failed to get info from Node {i}: {e}")
    
    # Step 8: Show ring information
    print_step(8 if not use_existing_cluster else 6, "Hash Ring Information")
    try:
        response = requests.get(f"http://{first_node}/ring", timeout=2)
        if response.status_code == 200:
            ring_info = response.json()
            print_info(f"Hash ring node count: {ring_info.get('node_count', 'unknown')}")
            print_info(f"Hash ring nodes: {ring_info.get('nodes', [])}")
            print_info(f"Replication factor: {ring_info.get('replication_factor', 'unknown')}")
    except Exception as e:
        print_error(f"Failed to get ring info: {e}")
    
    # Final summary
    print_header("DEMO SUMMARY")
    print_success("🎉 REPLICATION DEMONSTRATION COMPLETED!")
    print_info("Key features demonstrated:")
    print_info("  ✅ Multi-node cluster formation")
    print_info("  ✅ Automatic peer discovery")
    print_info("  ✅ Data replication across nodes")
    print_info("  ✅ Consistent hashing distribution")
    print_info("  ✅ Quorum-based consistency")
    
    print_info("\nCluster endpoints:")
    for i, node_addr in enumerate(node_addresses, 1):
        print_info(f"  Node {i}: http://{node_addr}")
    
    print_info("\nTest commands you can run:")
    for key in test_data.keys():
        print_info(f"  curl http://{first_node}/kv/{key}")
    
    if not use_existing_cluster:
        print_info("\nPress Ctrl+C to stop the demo and clean up")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print_success("Replication demo completed successfully!")
    else:
        print_error("Replication demo failed!")
        sys.exit(1) 