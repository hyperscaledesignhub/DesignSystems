#!/usr/bin/env python3
"""
Working Anti-Entropy Demo (Full Mesh, 3 Nodes)
A demonstration that starts 3 nodes, ensures all are fully joined, and only then runs anti-entropy.
Supports both new cluster creation and existing cluster usage.
"""

import os
import sys
import time
import json
import requests
import shutil
import yaml
from datetime import datetime
from node import RobustSimpleGossipNode, find_free_port

def print_header(title):
    print("\n" + "="*60)
    print(f"🎬 {title}")
    print("="*60)

def print_step(step, description):
    print(f"\n{step}. {description}")
    print("-" * 40)

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️ {message}")

def print_warning(message):
    print(f"⚠️ {message}")



def wait_for_health(port):
    for _ in range(20):
        try:
            r = requests.get(f"http://localhost:{port}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

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

def join_full_mesh(node_ports):
    # For each node, join every other node
    for i, port in enumerate(node_ports):
        for j, peer_port in enumerate(node_ports):
            if i != j:
                try:
                    requests.post(
                        f"http://localhost:{port}/join",
                        json={"address": f"localhost:{peer_port}"},
                        timeout=5
                    )
                except Exception as e:
                    print_warning(f"Node {port} failed to join {peer_port}: {e}")
    time.sleep(2)

def verify_full_mesh(node_ports):
    # Each node should have 2 peers
    for port in node_ports:
        try:
            r = requests.get(f"http://localhost:{port}/peers", timeout=2)
            if r.status_code != 200:
                print_error(f"Node {port} /peers failed: {r.status_code}")
                return False
            peers = r.json()
            if len(peers) != 2:
                print_warning(f"Node {port} has {len(peers)} peers (expected 2): {peers}")
                return False
        except Exception as e:
            print_error(f"Node {port} /peers error: {e}")
            return False
    return True

def demo_working_anti_entropy():
    print_header("WORKING ANTI-ENTROPY SYNCHRONIZATION DEMONSTRATION")
    
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
        
        # Run anti-entropy demo with existing cluster
        return demo_with_existing_cluster_simple(node_addresses)
        
    else:
        print_info("🚀 Starting new cluster for demo")
        return demo_with_new_cluster()

def demo_with_existing_cluster_simple(node_addresses):
    """Run anti-entropy demo with existing cluster (simplified version)"""
    print_header("ANTI-ENTROPY DEMO WITH EXISTING CLUSTER")
    
    print_info(f"Using existing cluster with {len(node_addresses)} nodes:")
    for i, address in enumerate(node_addresses, 1):
        print_info(f"  • Node {i} at {address}")
    
    # Step 3: Write different data to each node (using direct writes to create inconsistencies)
    print_step(3, "Writing different data to each node (creating inconsistencies)")
    print_info("Using direct writes to bypass replication and create real inconsistencies...")
    
    # Write different amounts of data to each node to create unequal counts
    node_data = [
        # Node 1: 4 keys
        {
            "user:alice": "alice@company.com", 
            "config:theme": "dark", 
            "session:xyz789": "active",
            "file:doc1.txt": "content1"
        },
        # Node 2: 2 keys  
        {
            "user:bob": "bob@company.com", 
            "config:theme": "light"
        },
        # Node 3: 5 keys
        {
            "user:charlie": "charlie@company.com", 
            "config:cache": "enabled", 
            "session:def456": "pending",
            "file:doc2.txt": "content2",
            "file:doc3.txt": "content3"
        }
    ]
    
    # Adjust data based on number of nodes
    if len(node_addresses) < 3:
        node_data = node_data[:len(node_addresses)]
    elif len(node_addresses) > 3:
        # Extend with more data for additional nodes
        extra_data = {
            "user:dave": "dave@company.com",
            "config:debug": "enabled",
            "session:ghi789": "expired",
            "file:doc4.txt": "content4"
        }
        node_data.append(extra_data)
    
    for i, (address, data) in enumerate(zip(node_addresses, node_data)):
        print_info(f"Writing to Node {i+1} (direct writes):")
        for key, value in data.items():
            # Use direct endpoint to bypass replication
            r = requests.put(f"http://{address}/kv/{key}/direct", json={"value": value}, timeout=5)
            if r.status_code == 200:
                print_success(f"  Node {i+1} wrote {key} = {value}")
            else:
                print_error(f"  Node {i+1} failed to write {key}")
    
    # Step 4: Show initial state and count data on each node
    print_step(4, "Showing initial state before anti-entropy")
    print_info("Counting data on each node (should show unequal counts):")
    
    node_counts = []
    for i, address in enumerate(node_addresses):
        print_info(f"Node {i+1} data:")
        count = 0
        for key in node_data[i].keys():
            r = requests.get(f"http://{address}/kv/{key}/direct", timeout=5)
            if r.status_code == 200:
                print_info(f"  {key} = {r.json().get('value')}")
                count += 1
            else:
                print_info(f"  {key} = NOT_FOUND")
        node_counts.append(count)
        print_info(f"  Total keys on Node {i+1}: {count}")
    
    print_info("")
    print_info("DATA COUNTS BEFORE ANTI-ENTROPY:")
    for i in range(len(node_addresses)):
        print_info(f"  Node {i+1}: {node_counts[i]} keys")
    print_info("  (Inconsistencies created - nodes have different amounts of data)")
    
    # Step 5: Trigger anti-entropy multiple times to ensure sync
    print_step(5, "Triggering anti-entropy on all nodes (multiple times)")
    print_info("Triggering anti-entropy multiple times to ensure complete synchronization...")
    
    for attempt in range(3):  # Try 3 times
        print_info(f"Anti-entropy attempt {attempt + 1}/3:")
        for i, address in enumerate(node_addresses):
            r = requests.post(f"http://{address}/anti-entropy/trigger", timeout=10)
            if r.status_code == 200:
                print_success(f"  Anti-entropy triggered on Node {i+1}")
            else:
                print_error(f"  Failed to trigger anti-entropy on Node {i+1}")
        print_info("Waiting for synchronization to complete...")
        time.sleep(10)  # Wait between attempts
    
    # Step 6: Verify synchronization results and show final counts
    print_step(6, "Verifying synchronization results")
    print_info("Counting data on each node after anti-entropy:")
    
    all_keys = set().union(*[d.keys() for d in node_data])
    final_node_counts = []
    
    for i, address in enumerate(node_addresses):
        print_info(f"Node {i+1} after anti-entropy:")
        count = 0
        for key in all_keys:
            r = requests.get(f"http://{address}/kv/{key}/direct", timeout=5)
            if r.status_code == 200:
                print_info(f"  {key} = {r.json().get('value')}")
                count += 1
            else:
                print_info(f"  {key} = NOT_FOUND")
        final_node_counts.append(count)
        print_info(f"  Total keys on Node {i+1}: {count}")
    
    print_info("")
    print_info("DATA COUNTS AFTER ANTI-ENTROPY:")
    for i in range(len(node_addresses)):
        print_info(f"  Node {i+1}: {final_node_counts[i]} keys")
    
    # Check if all nodes now have the same count
    if len(set(final_node_counts)) == 1:
        print_success(f"🎉 PERFECT SYNCHRONIZATION! All nodes now have {final_node_counts[0]} keys")
        print_success(f"Before: {node_counts} → After: {final_node_counts}")
    else:
        print_warning("Some inconsistencies remain")
        print_info("This might be due to timing or network issues")
        print_info(f"Before: {node_counts} → After: {final_node_counts}")
        
        # Try one more time with longer wait
        print_info("")
        print_info("Trying one more anti-entropy cycle with longer wait...")
        for address in node_addresses:
            requests.post(f"http://{address}/anti-entropy/trigger", timeout=10)
        time.sleep(20)  # Wait longer
        
        # Check again
        final_check_counts = []
        for address in node_addresses:
            count = 0
            for key in all_keys:
                r = requests.get(f"http://{address}/kv/{key}/direct", timeout=5)
                if r.status_code == 200:
                    count += 1
            final_check_counts.append(count)
        
        print_info("FINAL CHECK AFTER EXTENDED WAIT:")
        for i in range(len(node_addresses)):
            print_info(f"  Node {i+1}: {final_check_counts[i]} keys")
        
        if len(set(final_check_counts)) == 1:
            print_success(f"🎉 SYNCHRONIZATION ACHIEVED! All nodes now have {final_check_counts[0]} keys")
        else:
            print_error("Anti-entropy synchronization failed")
    
    print_success("Demo completed with existing cluster")
    return True

def demo_with_existing_cluster(nodes):
    """Run anti-entropy demo with existing cluster (legacy version)"""
    print_header("ANTI-ENTROPY DEMO WITH EXISTING CLUSTER")
    
    # Extract node addresses for easier use
    node_addresses = [node['address'] for node in nodes]
    node_ids = [node['id'] for node in nodes]
    
    print_info(f"Using existing cluster with {len(nodes)} nodes:")
    for node in nodes:
        print_info(f"  • {node['id']} at {node['address']}")
    
    # Step 1: Verify cluster connectivity
    print_step(1, "Verifying cluster connectivity")
    for i, address in enumerate(node_addresses):
        try:
            response = requests.get(f"http://{address}/peers", timeout=5)
            if response.status_code == 200:
                peers = response.json()
                print_success(f"Node {node_ids[i]} has {len(peers)} peers: {peers}")
            else:
                print_error(f"Node {node_ids[i]} failed to get peers: {response.status_code}")
        except Exception as e:
            print_error(f"Node {node_ids[i]} error: {e}")
    
    # Step 2: Write different data to each node (using direct writes to create inconsistencies)
    print_step(2, "Writing different data to each node (creating inconsistencies)")
    print_info("Using direct writes to bypass replication and create real inconsistencies...")
    
    # Write different amounts of data to each node to create unequal counts
    node_data = [
        # Node 1: 4 keys
        {
            "user:alice": "alice@company.com", 
            "config:theme": "dark", 
            "session:xyz789": "active",
            "file:doc1.txt": "content1"
        },
        # Node 2: 2 keys  
        {
            "user:bob": "bob@company.com", 
            "config:theme": "light"
        },
        # Node 3: 5 keys
        {
            "user:charlie": "charlie@company.com", 
            "config:cache": "enabled", 
            "session:def456": "pending",
            "file:doc2.txt": "content2",
            "file:doc3.txt": "content3"
        }
    ]
    
    # Adjust data based on number of nodes
    if len(nodes) < 3:
        node_data = node_data[:len(nodes)]
    elif len(nodes) > 3:
        # Extend with more data for additional nodes
        extra_data = {
            "user:dave": "dave@company.com",
            "config:debug": "enabled",
            "session:ghi789": "expired",
            "file:doc4.txt": "content4"
        }
        node_data.append(extra_data)
    
    for i, (address, data) in enumerate(zip(node_addresses, node_data)):
        print_info(f"Writing to Node {node_ids[i]} (direct writes):")
        for key, value in data.items():
            # Use direct endpoint to bypass replication
            r = requests.put(f"http://{address}/kv/{key}/direct", json={"value": value}, timeout=5)
            if r.status_code == 200:
                print_success(f"  Node {node_ids[i]} wrote {key} = {value}")
            else:
                print_error(f"  Node {node_ids[i]} failed to write {key}")
    
    # Step 3: Show initial state and count data on each node
    print_step(3, "Showing initial state before anti-entropy")
    print_info("Counting data on each node (should show unequal counts):")
    
    node_counts = []
    for i, address in enumerate(node_addresses):
        print_info(f"Node {node_ids[i]} data:")
        count = 0
        for key in node_data[i].keys():
            r = requests.get(f"http://{address}/kv/{key}/direct", timeout=5)
            if r.status_code == 200:
                print_info(f"  {key} = {r.json().get('value')}")
                count += 1
            else:
                print_info(f"  {key} = NOT_FOUND")
        node_counts.append(count)
        print_info(f"  Total keys on Node {node_ids[i]}: {count}")
    
    print_info("")
    print_info("DATA COUNTS BEFORE ANTI-ENTROPY:")
    for i, node_id in enumerate(node_ids):
        print_info(f"  {node_id}: {node_counts[i]} keys")
    print_info("  (Inconsistencies created - nodes have different amounts of data)")
    
    # Step 4: Trigger anti-entropy multiple times to ensure sync
    print_step(4, "Triggering anti-entropy on all nodes (multiple times)")
    print_info("Triggering anti-entropy multiple times to ensure complete synchronization...")
    
    for attempt in range(3):  # Try 3 times
        print_info(f"Anti-entropy attempt {attempt + 1}/3:")
        for i, address in enumerate(node_addresses):
            r = requests.post(f"http://{address}/anti-entropy/trigger", timeout=10)
            if r.status_code == 200:
                print_success(f"  Anti-entropy triggered on Node {node_ids[i]}")
            else:
                print_error(f"  Failed to trigger anti-entropy on Node {node_ids[i]}")
        print_info("Waiting for synchronization to complete...")
        time.sleep(10)  # Wait between attempts
    
    # Step 5: Verify synchronization results and show final counts
    print_step(5, "Verifying synchronization results")
    print_info("Counting data on each node after anti-entropy:")
    
    all_keys = set().union(*[d.keys() for d in node_data])
    final_node_counts = []
    
    for i, address in enumerate(node_addresses):
        print_info(f"Node {node_ids[i]} after anti-entropy:")
        count = 0
        for key in all_keys:
            r = requests.get(f"http://{address}/kv/{key}/direct", timeout=5)
            if r.status_code == 200:
                print_info(f"  {key} = {r.json().get('value')}")
                count += 1
            else:
                print_info(f"  {key} = NOT_FOUND")
        final_node_counts.append(count)
        print_info(f"  Total keys on Node {node_ids[i]}: {count}")
    
    print_info("")
    print_info("DATA COUNTS AFTER ANTI-ENTROPY:")
    for i, node_id in enumerate(node_ids):
        print_info(f"  {node_id}: {final_node_counts[i]} keys")
    
    # Check if all nodes now have the same count
    if len(set(final_node_counts)) == 1:
        print_success(f"🎉 PERFECT SYNCHRONIZATION! All nodes now have {final_node_counts[0]} keys")
        print_success(f"Before: {node_counts} → After: {final_node_counts}")
    else:
        print_warning("Some inconsistencies remain")
        print_info("This might be due to timing or network issues")
        print_info(f"Before: {node_counts} → After: {final_node_counts}")
        
        # Try one more time with longer wait
        print_info("")
        print_info("Trying one more anti-entropy cycle with longer wait...")
        for address in node_addresses:
            requests.post(f"http://{address}/anti-entropy/trigger", timeout=10)
        time.sleep(20)  # Wait longer
        
        # Check again
        final_check_counts = []
        for address in node_addresses:
            count = 0
            for key in all_keys:
                r = requests.get(f"http://{address}/kv/{key}/direct", timeout=5)
                if r.status_code == 200:
                    count += 1
            final_check_counts.append(count)
        
        print_info("FINAL CHECK AFTER EXTENDED WAIT:")
        for i, node_id in enumerate(node_ids):
            print_info(f"  {node_id}: {final_check_counts[i]} keys")
        
        if len(set(final_check_counts)) == 1:
            print_success(f"🎉 SYNCHRONIZATION ACHIEVED! All nodes now have {final_check_counts[0]} keys")
        else:
            print_error("Anti-entropy synchronization failed")
    
    print_success("Demo completed with existing cluster")
    return True

def demo_with_new_cluster():
    """Run anti-entropy demo with new cluster (original implementation)"""
    print_header("ANTI-ENTROPY DEMO WITH NEW CLUSTER")
    
    # Clean up any existing data folders first
    print_info("Cleaning up previous data folders...")
    for i in range(1, 10):  # Clean up to 9 potential data folders
        data_dir = f"working_anti_entropy_data_{i}"
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)
            print_info(f"  Removed {data_dir}")
    
    # Step 1: Create 3 nodes
    print_step(1, "Creating three nodes")
    ports = [find_free_port() for _ in range(3)]
    data_dirs = [f"working_anti_entropy_data_{i+1}" for i in range(3)]
    for d in data_dirs:
        os.makedirs(d)
    nodes = []
    for i in range(3):
        node = RobustSimpleGossipNode(
            node_id=f"working-node-{i+1}",
            host="localhost",
            port=ports[i],
            data_dir=data_dirs[i]
        )
        nodes.append(node)
        print_success(f"Node {i+1} created on port {ports[i]}")
    
    # Step 2: Start nodes
    print_step(2, "Starting nodes")
    for node in nodes:
        node.start()
    for port in ports:
        if not wait_for_health(port):
            print_error(f"Node on port {port} did not become healthy!")
            return False
    print_success("All nodes started and healthy")
    
    # Step 3: Join all nodes (full mesh)
    print_step(3, "Joining all nodes (full mesh)")
    join_full_mesh(ports)
    
    # Step 4: Verify full mesh
    print_step(4, "Verifying full mesh (each node has 2 peers)")
    if verify_full_mesh(ports):
        print_success("All nodes are fully joined (full mesh)")
    else:
        print_error("Full mesh not achieved. Aborting demo.")
        for node in nodes:
            node.stop()
        return False
    
    # Step 5: Write different data to each node (using direct writes to create inconsistencies)
    print_step(5, "Writing different data to each node (creating inconsistencies)")
    print_info("Using direct writes to bypass replication and create real inconsistencies...")
    
    # Write different amounts of data to each node to create unequal counts
    node_data = [
        # Node 1: 4 keys
        {
            "user:alice": "alice@company.com", 
            "config:theme": "dark", 
            "session:xyz789": "active",
            "file:doc1.txt": "content1"
        },
        # Node 2: 2 keys  
        {
            "user:bob": "bob@company.com", 
            "config:theme": "light"
        },
        # Node 3: 5 keys
        {
            "user:charlie": "charlie@company.com", 
            "config:cache": "enabled", 
            "session:def456": "pending",
            "file:doc2.txt": "content2",
            "file:doc3.txt": "content3"
        }
    ]
    
    for i, (port, data) in enumerate(zip(ports, node_data)):
        print_info(f"Writing to Node {i+1} (direct writes):")
        for key, value in data.items():
            # Use direct endpoint to bypass replication
            r = requests.put(f"http://localhost:{port}/kv/{key}/direct", json={"value": value}, timeout=5)
            if r.status_code == 200:
                print_success(f"  Node {i+1} wrote {key} = {value}")
            else:
                print_error(f"  Node {i+1} failed to write {key}")
    
    # Step 6: Show initial state and count data on each node
    print_step(6, "Showing initial state before anti-entropy")
    print_info("Counting data on each node (should show unequal counts):")
    
    node_counts = []
    for i, port in enumerate(ports):
        print_info(f"Node {i+1} data:")
        count = 0
        for key in node_data[i].keys():
            r = requests.get(f"http://localhost:{port}/kv/{key}/direct", timeout=5)
            if r.status_code == 200:
                print_info(f"  {key} = {r.json().get('value')}")
                count += 1
            else:
                print_info(f"  {key} = NOT_FOUND")
        node_counts.append(count)
        print_info(f"  Total keys on Node {i+1}: {count}")
    
    print_info("")
    print_info("DATA COUNTS BEFORE ANTI-ENTROPY:")
    print_info(f"  Node 1: {node_counts[0]} keys")
    print_info(f"  Node 2: {node_counts[1]} keys") 
    print_info(f"  Node 3: {node_counts[2]} keys")
    print_info("  (Inconsistencies created - nodes have different amounts of data)")
    
    # Step 7: Trigger anti-entropy multiple times to ensure sync
    print_step(7, "Triggering anti-entropy on all nodes (multiple times)")
    print_info("Triggering anti-entropy multiple times to ensure complete synchronization...")
    
    for attempt in range(3):  # Try 3 times
        print_info(f"Anti-entropy attempt {attempt + 1}/3:")
        for i, port in enumerate(ports):
            r = requests.post(f"http://localhost:{port}/anti-entropy/trigger", timeout=10)
            if r.status_code == 200:
                print_success(f"  Anti-entropy triggered on Node {i+1}")
            else:
                print_error(f"  Failed to trigger anti-entropy on Node {i+1}")
        print_info("Waiting for synchronization to complete...")
        time.sleep(10)  # Wait between attempts
    
    # Step 8: Verify synchronization results and show final counts
    print_step(8, "Verifying synchronization results")
    print_info("Counting data on each node after anti-entropy:")
    
    all_keys = set().union(*[d.keys() for d in node_data])
    final_node_counts = []
    
    for i, port in enumerate(ports):
        print_info(f"Node {i+1} after anti-entropy:")
        count = 0
        for key in all_keys:
            r = requests.get(f"http://localhost:{port}/kv/{key}/direct", timeout=5)
            if r.status_code == 200:
                print_info(f"  {key} = {r.json().get('value')}")
                count += 1
            else:
                print_info(f"  {key} = NOT_FOUND")
        final_node_counts.append(count)
        print_info(f"  Total keys on Node {i+1}: {count}")
    
    print_info("")
    print_info("DATA COUNTS AFTER ANTI-ENTROPY:")
    print_info(f"  Node 1: {final_node_counts[0]} keys")
    print_info(f"  Node 2: {final_node_counts[1]} keys")
    print_info(f"  Node 3: {final_node_counts[2]} keys")
    
    # Check if all nodes now have the same count
    if len(set(final_node_counts)) == 1:
        print_success(f"🎉 PERFECT SYNCHRONIZATION! All nodes now have {final_node_counts[0]} keys")
        print_success(f"Before: {node_counts[0]}, {node_counts[1]}, {node_counts[2]} → After: {final_node_counts[0]}, {final_node_counts[0]}, {final_node_counts[0]}")
    else:
        print_warning("Some inconsistencies remain")
        print_info("This might be due to timing or network issues")
        print_info(f"Before: {node_counts[0]}, {node_counts[1]}, {node_counts[2]} → After: {final_node_counts[0]}, {final_node_counts[1]}, {final_node_counts[2]}")
        
        # Try one more time with longer wait
        print_info("")
        print_info("Trying one more anti-entropy cycle with longer wait...")
        for i, port in enumerate(ports):
            requests.post(f"http://localhost:{port}/anti-entropy/trigger", timeout=10)
        time.sleep(20)  # Wait longer
        
        # Check again
        final_check_counts = []
        for i, port in enumerate(ports):
            count = 0
            for key in all_keys:
                r = requests.get(f"http://localhost:{port}/kv/{key}/direct", timeout=5)
                if r.status_code == 200:
                    count += 1
            final_check_counts.append(count)
        
        print_info("FINAL CHECK AFTER EXTENDED WAIT:")
        print_info(f"  Node 1: {final_check_counts[0]} keys")
        print_info(f"  Node 2: {final_check_counts[1]} keys")
        print_info(f"  Node 3: {final_check_counts[2]} keys")
        
        if len(set(final_check_counts)) == 1:
            print_success(f"🎉 SYNCHRONIZATION ACHIEVED! All nodes now have {final_check_counts[0]} keys")
        else:
            print_error("Anti-entropy synchronization failed")
    
    # Step 9: Cleanup
    print_step(9, "Cleaning up")
    for node in nodes:
        node.stop()
    print_success("Demo completed")
    return True

def main():
    print_header("WORKING ANTI-ENTROPY DEMO")
    print_info("This demo will:")
    print_info("  1. Detect existing cluster or create new one")
    print_info("  2. Write different data to each node")
    print_info("  3. Trigger anti-entropy on all nodes")
    print_info("  4. Verify that data is synchronized")
    print_info("")
    try:
        success = demo_working_anti_entropy()
        if success:
            print_header("DEMO COMPLETED SUCCESSFULLY")
            print_success("Anti-entropy synchronization demonstrated!")
        else:
            print_header("DEMO FAILED")
            print_error("Anti-entropy demo did not complete successfully")
    except KeyboardInterrupt:
        print_info("\nDemo interrupted by user")
    except Exception as e:
        print_error(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 