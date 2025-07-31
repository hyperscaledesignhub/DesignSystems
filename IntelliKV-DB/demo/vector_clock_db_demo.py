#!/usr/bin/env python3
"""
Vector Clock Demo in Distributed DB

This script demonstrates vector clock behavior in a real 3-node distributed DB cluster:
- Shows vector clock increment on writes
- Shows vector clock merge on gossip/sync
- Demonstrates causal ordering and conflict resolution
- Fetches and prints vector clocks from each node
"""

import time
import requests
import subprocess
import os
import signal
from typing import Dict, List

def robust_request(method, url, max_retries=5, wait=1, **kwargs):
    """Retry API calls up to max_retries times, waiting between attempts."""
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, timeout=10, **kwargs)
            return resp
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[WARN] {method} {url} failed (attempt {attempt+1}/{max_retries}): {e}. Retrying...")
                time.sleep(wait)
            else:
                print(f"[ERROR] {method} {url} failed after {max_retries} attempts: {e}")
    return None

def wait_for_node_ready(address, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"http://{address}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def wait_for_cluster_formation_existing(node_addresses, timeout=60):
    """Wait for existing cluster to be ready"""
    print("Verifying existing cluster formation...")
    
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
                print("✅ Existing cluster is ready! All nodes are connected.")
                return True
                
        except Exception as e:
            print(f"[WARN] Error checking existing cluster formation: {e}")
        
        time.sleep(2)
    
    print("❌ Existing cluster verification failed within timeout")
    return False

def start_nodes():
    print("=== STARTING 3 NODES FOR VECTOR CLOCK DEMO ===")
    nodes = []
    ports = [9999, 10000, 10001]
    for i, port in enumerate(ports, 1):
        node_id = f"db-node-{i}"
        env = dict(os.environ)
        env['SEED_NODE_ID'] = node_id
        env['CONFIG_FILE'] = 'config-local.yaml'
        process = subprocess.Popen(
            ["python", "node.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        address = f"localhost:{port}"
        print(f"Starting {node_id} on {address}...")
        if wait_for_node_ready(address, timeout=20):
            print(f"✅ {node_id} is healthy!")
        else:
            print(f"❌ {node_id} failed to become healthy!")
            process.terminate()
            return None
        nodes.append({'id': node_id, 'address': address, 'process': process})
    print("Waiting 3s for all nodes to stabilize...")
    time.sleep(3)
    return nodes

def form_cluster(nodes):
    print("\n=== FORMING CLUSTER ===")
    for i in range(1, len(nodes)):
        response = robust_request(
            "POST",
            f"http://{nodes[i]['address']}/join",
            json={"address": nodes[0]['address']},
        )
        if response and response.status_code == 200:
            print(f"✅ {nodes[i]['id']} joined {nodes[0]['id']}")
        else:
            print(f"❌ Failed to join {nodes[i]['id']}")
    print("⏳ Waiting for cluster to stabilize...")
    time.sleep(5)
    for node in nodes:
        response = robust_request("GET", f"http://{node['address']}/peers")
        if response and response.status_code == 200:
            peers = response.json()
            print(f"✅ {node['id']} has {len(peers)} peers: {peers}")
        else:
            print(f"❌ Failed to get peers for {node['id']}")

def print_vector_clock(node, key):
    response = robust_request("GET", f"http://{node['address']}/causal/kv/{key}")
    if response and response.status_code == 200:
        result = response.json()
        value = result.get('value', 'NOT_FOUND')
        vector_clock = result.get('vector_clock', {})
        print(f"   {node['id']}: value='{value}', vector_clock={vector_clock}")
        return vector_clock
    else:
        print(f"[WARN] Could not fetch value from {node['id']}")
    return None

def demo_vector_clock_behavior(nodes):
    print("\n=== VECTOR CLOCK DEMO ===")
    key = "vc_demo_key"
    # Step 1: Write from node 1
    print("\n1. Node 1 writes initial value")
    node1 = nodes[0]
    r = robust_request("PUT", f"http://{node1['address']}/causal/kv/{key}", json={"value": "v1", "node_id": node1['id']})
    print(f"Write response: {r.status_code if r else 'FAILED'}")
    time.sleep(2)
    print("Vector clocks after node 1 write:")
    for node in nodes:
        print_vector_clock(node, key)
    # Step 2: Node 2 writes a causally dependent value (after reading from node 1)
    print("\n2. Node 2 reads, then writes a new value (causal dependency)")
    node2 = nodes[1]
    r = robust_request("GET", f"http://{node2['address']}/causal/kv/{key}")
    prev_clock = r.json().get('vector_clock', {}) if r and r.status_code == 200 else {}
    r = robust_request("PUT", f"http://{node2['address']}/causal/kv/{key}", json={"value": "v2", "node_id": node2['id'], "vector_clock": prev_clock})
    print(f"Write response: {r.status_code if r else 'FAILED'}")
    time.sleep(2)
    print("Vector clocks after node 2 write:")
    for node in nodes:
        print_vector_clock(node, key)
    # Step 3: Node 3 writes concurrently (without reading latest)
    print("\n3. Node 3 writes concurrently (no dependency)")
    node3 = nodes[2]
    r = robust_request("PUT", f"http://{node3['address']}/causal/kv/{key}", json={"value": "v3", "node_id": node3['id']})
    print(f"Write response: {r.status_code if r else 'FAILED'}")
    time.sleep(2)
    print("Vector clocks after node 3 concurrent write:")
    for node in nodes:
        print_vector_clock(node, key)
    # Step 4: Wait for gossip and convergence
    print("\n4. Waiting for gossip and convergence...")
    time.sleep(7)
    print("Vector clocks after gossip:")
    for node in nodes:
        print_vector_clock(node, key)
    # Step 5: Show conflict stats
    print("\n5. Conflict stats:")
    for node in nodes:
        response = robust_request("GET", f"http://{node['address']}/causal/stats")
        if response and response.status_code == 200:
            stats = response.json()
            print(f"   {node['id']}: {stats}")
        else:
            print(f"[WARN] Could not fetch stats from {node['id']}")

def cleanup(nodes):
    print("\n=== CLEANING UP ===")
    for node in nodes:
        try:
            node['process'].terminate()
            node['process'].wait(timeout=5)
            print(f"✅ Stopped {node['id']}")
        except Exception as e:
            print(f"❌ Error stopping {node['id']}: {e}")
            try:
                node['process'].kill()
            except:
                pass

def main():
    print("=== VECTOR CLOCK DEMO IN DISTRIBUTED DB ===")
    
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
                            print(f"🔍 Auto-detected existing cluster from {config_file}")
                            print(f"Found {len(node_addresses)} nodes: {node_addresses}")
            except Exception as e:
                print(f"[WARN] Could not auto-detect cluster from config: {e}")
    
    nodes = None
    try:
        if use_existing_cluster:
            print("🔗 Using existing cluster")
            node_addresses = cluster_nodes_env.split(',')
            print(f"Found {len(node_addresses)} existing nodes: {node_addresses}")
            
            # Verify existing nodes are healthy
            print("=== VERIFYING EXISTING CLUSTER NODES ===")
            for i, node_addr in enumerate(node_addresses, 1):
                host, port = node_addr.split(':')
                if not wait_for_node_ready(node_addr, timeout=20):
                    print(f"❌ Failed to verify Node {i} ({node_addr})")
                    return
            
            # Wait for cluster formation
            print("=== VERIFYING CLUSTER FORMATION ===")
            if not wait_for_cluster_formation_existing(node_addresses):
                print("❌ Cluster formation verification failed")
                return
            
            # Create nodes list for existing cluster
            nodes = []
            for i, node_addr in enumerate(node_addresses, 1):
                node_id = f"db-node-{i}"
                nodes.append({'id': node_id, 'address': node_addr, 'process': None})
            
        else:
            print("🚀 Starting new cluster for demo")
            nodes = start_nodes()
            if not nodes:
                print("❌ Failed to start nodes")
                return
            form_cluster(nodes)
        
        demo_vector_clock_behavior(nodes)
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
    finally:
        if nodes and not use_existing_cluster:
            cleanup(nodes)

if __name__ == "__main__":
    main() 