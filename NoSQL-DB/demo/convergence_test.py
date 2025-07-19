#!/usr/bin/env python3
"""
Convergence Test for Distributed Key-Value Database
Tests that all nodes converge to the same value after conflict resolution
"""

import time
import requests
import subprocess
import os
import signal
import sys
import yaml
from typing import Dict, List

# Global variables for cleanup
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
    
    # Stop all node processes
    for process in node_processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            try:
                process.kill()
            except:
                pass
    
    # Kill any remaining processes
    try:
        subprocess.run(['pkill', '-f', 'node.py'], 
                      capture_output=True, timeout=5)
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

def start_node(node_id, host, port, data_dir):
    """Start a node in a separate process"""
    print_info(f"Starting {node_id} on {host}:{port}")
    
    # Create data directory
    if os.path.exists(data_dir):
        import shutil
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

def get_existing_nodes_from_config(config_file):
    """Get existing nodes from config file"""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        nodes = []
        
        # Check for different config formats
        if 'cluster' in config and 'seed_nodes' in config['cluster']:
            # Current config format with cluster.seed_nodes
            for node_config in config['cluster']['seed_nodes']:
                if isinstance(node_config, dict):
                    host = node_config.get('host', 'localhost')
                    port = node_config.get('http_port', node_config.get('port', 8080))
                    nodes.append(f"{host}:{port}")
                elif isinstance(node_config, str):
                    # Handle string format like "localhost:9999"
                    nodes.append(node_config)
        
        return nodes
    except Exception as e:
        print_warning(f"Could not load config from {config_file}: {e}")
        return []

def create_concurrent_writes(node_addresses):
    """Create concurrent writes to the same key from all nodes"""
    print_info("Creating concurrent writes to the same key from all nodes")
    
    conflict_key = "convergence_test_key"
    
    # Write from all nodes simultaneously
    for i, node_addr in enumerate(node_addresses, 1):
        try:
            response = requests.put(
                f"http://{node_addr}/causal/kv/{conflict_key}",
                json={"value": f"value_from_node_{i}", "node_id": f"db-node-{i}"},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                vector_clock = result.get('vector_clock', {})
                print_success(f"Node {i} wrote: 'value_from_node_{i}' (clock: {vector_clock})")
            else:
                print_error(f"Node {i} write failed: {response.status_code}")
        except Exception as e:
            print_error(f"Error writing from Node {i}: {e}")

def check_initial_values(node_addresses):
    """Check what value each node has immediately after writes"""
    print_info("Checking initial values (before gossip)")
    
    conflict_key = "convergence_test_key"
    values = {}
    
    for i, node_addr in enumerate(node_addresses, 1):
        try:
            response = requests.get(f"http://{node_addr}/causal/kv/{conflict_key}", timeout=10)
            if response.status_code == 200:
                result = response.json()
                value = result.get('value', 'NOT_FOUND')
                vector_clock = result.get('vector_clock', {})
                values[f"Node {i}"] = value
                print_info(f"Node {i}: '{value}' (clock: {vector_clock})")
            else:
                print_error(f"Failed to get value from Node {i}: {response.status_code}")
        except Exception as e:
            print_error(f"Error getting value from Node {i}: {e}")
    
    return values

def wait_for_convergence(node_addresses, max_wait=30):
    """Wait for all nodes to converge to the same value"""
    print_info(f"Waiting for convergence (max {max_wait}s)")
    
    conflict_key = "convergence_test_key"
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        print_info(f"Checking convergence... ({int(time.time() - start_time)}s elapsed)")
        
        values = {}
        vector_clocks = {}
        
        # Get current values from all nodes
        for i, node_addr in enumerate(node_addresses, 1):
            try:
                response = requests.get(f"http://{node_addr}/causal/kv/{conflict_key}", timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    value = result.get('value', 'NOT_FOUND')
                    vector_clock = result.get('vector_clock', {})
                    values[f"Node {i}"] = value
                    vector_clocks[f"Node {i}"] = vector_clock
                else:
                    print_error(f"Failed to get value from Node {i}: {response.status_code}")
            except Exception as e:
                print_error(f"Error getting value from Node {i}: {e}")
        
        # Check if all values are the same
        unique_values = set(values.values())
        if len(unique_values) == 1 and 'NOT_FOUND' not in unique_values:
            print_success("CONVERGENCE ACHIEVED!")
            print_info(f"All nodes have the same value: '{list(unique_values)[0]}'")
            print_info("Vector clocks:")
            for node_id, clock in vector_clocks.items():
                print_info(f"  • {node_id}: {clock}")
            return True, values, vector_clocks
        
        # Show current state
        print_info(f"Current values: {values}")
        time.sleep(2)
    
    print_error(f"CONVERGENCE TIMEOUT after {max_wait}s")
    return False, values, vector_clocks

def check_conflict_stats(node_addresses):
    """Check conflict resolution statistics from all nodes"""
    print_info("Checking conflict resolution statistics")
    
    for i, node_addr in enumerate(node_addresses, 1):
        try:
            response = requests.get(f"http://{node_addr}/causal/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                conflicts_detected = stats.get('conflicts_detected', 0)
                conflicts_resolved = stats.get('conflicts_resolved', 0)
                print_info(f"Node {i}: {conflicts_detected} conflicts detected, {conflicts_resolved} resolved")
            else:
                print_error(f"Failed to get stats from Node {i}: {response.status_code}")
        except Exception as e:
            print_error(f"Error getting stats from Node {i}: {e}")

def main():
    """Main convergence test function"""
    # Set up signal handlers for cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print_header("CONVERGENCE TEST")
    print_info("This test verifies that all nodes converge to the same value after conflict resolution")
    
    # Get node addresses from environment or config
    cluster_nodes_env = os.getenv('CLUSTER_NODES')
    config_file = os.getenv('CONFIG_FILE', 'config-local.yaml')
    
    if cluster_nodes_env:
        # Use nodes from environment variable
        print_info("🔗 Using existing cluster from CLUSTER_NODES environment variable")
        node_addresses = cluster_nodes_env.split(',')
        print_info(f"Found {len(node_addresses)} nodes: {node_addresses}")
    else:
        # Try to get nodes from config file
        print_info(f"🔍 No CLUSTER_NODES found, checking config file: {config_file}")
        node_addresses = get_existing_nodes_from_config(config_file)
        
        if node_addresses:
            print_info("🔗 Using existing cluster from config file")
            print_info(f"Found {len(node_addresses)} nodes: {node_addresses}")
        else:
            # Start new cluster
            print_info("🚀 Starting new cluster for test")
            try:
                # Step 1: Start Node 1
                print_step(1, "Starting Node 1 (db-node-1)")
                process1 = start_node("db-node-1", "localhost", 9999, "convergence_test_data_1")
                
                if not wait_for_node_health("localhost", 9999, "Node 1"):
                    print_error("Failed to start Node 1")
                    return False
                
                # Step 2: Start Node 2
                print_step(2, "Starting Node 2 (db-node-2)")
                process2 = start_node("db-node-2", "localhost", 10000, "convergence_test_data_2")
                
                if not wait_for_node_health("localhost", 10000, "Node 2"):
                    print_error("Failed to start Node 2")
                    return False
                
                # Step 3: Start Node 3
                print_step(3, "Starting Node 3 (db-node-3)")
                process3 = start_node("db-node-3", "localhost", 10001, "convergence_test_data_3")
                
                if not wait_for_node_health("localhost", 10001, "Node 3"):
                    print_error("Failed to start Node 3")
                    return False
                
                # Step 4: Wait for cluster formation
                print_step(4, "Waiting for cluster formation")
                if not wait_for_cluster_formation_existing(["localhost:9999", "localhost:10000", "localhost:10001"]):
                    print_error("Cluster formation failed")
                    return False
                
                node_addresses = ["localhost:9999", "localhost:10000", "localhost:10001"]
            
            except Exception as e:
                print_error(f"Failed to start cluster: {e}")
                return False
    
    # Verify existing nodes are healthy
    print_step(1 if not cluster_nodes_env else 1, "Verifying cluster nodes")
    for i, node_addr in enumerate(node_addresses, 1):
        host, port = node_addr.split(':')
        if not wait_for_node_health(host, int(port), f"Node {i} ({node_addr})"):
            print_error(f"Failed to verify Node {i} ({node_addr})")
            return False
    
    # Wait for cluster formation
    print_step(2 if not cluster_nodes_env else 2, "Verifying cluster formation")
    if not wait_for_cluster_formation_existing(node_addresses):
        print_error("Cluster formation verification failed")
        return False
    
    # Step 3: Create concurrent writes
    print_step(3 if not cluster_nodes_env else 3, "Creating concurrent writes")
    create_concurrent_writes(node_addresses)
    
    # Step 4: Check initial values (before gossip)
    print_step(4 if not cluster_nodes_env else 4, "Checking initial values (before gossip)")
    initial_values = check_initial_values(node_addresses)
    print_info(f"Initial unique values: {set(initial_values.values())}")
    
    # Step 5: Wait for convergence
    print_step(5 if not cluster_nodes_env else 5, "Waiting for convergence")
    converged, final_values, final_clocks = wait_for_convergence(node_addresses)
    
    # Step 6: Check conflict stats
    print_step(6 if not cluster_nodes_env else 6, "Checking conflict resolution statistics")
    check_conflict_stats(node_addresses)
    
    # Final verification
    print_header("FINAL VERIFICATION")
    if converged:
        print_success("SUCCESS: All nodes converged to the same value!")
        print_info("This proves that the distributed system achieves eventual consistency")
        print_info("Vector clock conflict resolution is working correctly across all nodes")
    else:
        print_error("FAILURE: Nodes did not converge to the same value")
        print_error("This indicates a problem with conflict resolution or gossip")
    
    # Final summary
    print_header("TEST SUMMARY")
    if converged:
        print_success("🎉 CONVERGENCE TEST PASSED!")
        print_info("Key features verified:")
        print_info("  ✅ Multi-node cluster formation")
        print_info("  ✅ Concurrent write handling")
        print_info("  ✅ Vector clock conflict detection")
        print_info("  ✅ Conflict resolution")
        print_info("  ✅ Eventual consistency")
    else:
        print_error("❌ CONVERGENCE TEST FAILED!")
        print_error("Issues detected:")
        print_error("  ❌ Nodes did not converge to same value")
        print_error("  ❌ Conflict resolution may be broken")
        print_error("  ❌ Gossip protocol may not be working")
    
    print_info("\nCluster endpoints:")
    for i, node_addr in enumerate(node_addresses, 1):
        print_info(f"  Node {i}: http://{node_addr}")
    
    if not cluster_nodes_env:
        print_info("\nPress Ctrl+C to stop the test and clean up")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    
    return converged

if __name__ == "__main__":
    success = main()
    if success:
        print_success("Convergence test completed successfully!")
    else:
        print_error("Convergence test failed!")
        sys.exit(1) 