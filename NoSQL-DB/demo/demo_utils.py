#!/usr/bin/env python3
"""
Demo Utilities for NoSQL Database Demonstrations
Provides common utilities for demo scripts including logging and cluster management
"""

import os
import sys
import time
import requests
import subprocess
import json
from datetime import datetime
from typing import List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DemoLogger:
    """Logger for demo scripts with consistent formatting"""
    
    def __init__(self, demo_name: str):
        self.demo_name = demo_name
        self.step_count = 0
        
    def header(self, message: str):
        """Print a header message"""
        print(f"\n{'='*60}")
        print(f"{message:^60}")
        print(f"{'='*60}\n")
        
    def step(self, message: str):
        """Print a step message"""
        self.step_count += 1
        print(f"\n[Step {self.step_count}] {message}")
        print("-" * 50)
        
    def info(self, message: str):
        """Print an info message"""
        print(f"ℹ️  {message}")
        
    def success(self, message: str):
        """Print a success message"""
        print(f"✅ {message}")
        
    def warning(self, message: str):
        """Print a warning message"""
        print(f"⚠️  {message}")
        
    def error(self, message: str):
        """Print an error message"""
        print(f"❌ {message}")
        
def find_cluster_config() -> Optional[str]:
    """Find cluster configuration file"""
    config_paths = [
        "cluster_config.yaml",
        "config/cluster_config.yaml",
        "../config/cluster_config.yaml",
        os.path.expanduser("~/.kvdb/cluster_config.yaml")
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            return path
    return None

def read_cluster_config(config_path: str) -> List[str]:
    """Read cluster nodes from config file"""
    nodes = []
    try:
        # Simple YAML parsing for cluster nodes
        with open(config_path, 'r') as f:
            content = f.read()
            
        # Look for seed_nodes section
        in_seed_nodes = False
        for line in content.split('\n'):
            line = line.strip()
            if 'seed_nodes:' in line:
                in_seed_nodes = True
                continue
            if in_seed_nodes and line.startswith('-'):
                # Extract host and port
                if 'host:' in line:
                    host = line.split('host:')[1].strip()
                elif 'http_port:' in line:
                    port = line.split('http_port:')[1].strip()
                    if 'host' in locals():
                        nodes.append(f"{host}:{port}")
                        del host
    except Exception as e:
        print(f"Error reading config: {e}")
        
    return nodes

def check_cluster_status(nodes: List[str]) -> bool:
    """Check if all nodes in cluster are healthy"""
    all_healthy = True
    
    for node in nodes:
        try:
            response = requests.get(f"http://{node}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Node {node} is healthy")
            else:
                print(f"❌ Node {node} returned status {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"❌ Node {node} is not reachable: {e}")
            all_healthy = False
            
    return all_healthy

def start_local_cluster(logger: DemoLogger, num_nodes: int = 3) -> List[str]:
    """Start a local cluster for demo purposes"""
    logger.info(f"Starting local cluster with {num_nodes} nodes...")
    
    nodes = []
    base_port = 8000
    
    for i in range(num_nodes):
        port = base_port + i
        node_id = f"demo-node-{i+1}"
        
        # Start node process
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "distributed", "node.py"),
            "--port", str(port),
            "--node-id", node_id
        ]
        
        # If this is not the first node, add seed node
        if i > 0:
            cmd.extend(["--seed-node", f"localhost:{base_port}"])
            
        try:
            # Start in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Give node time to start
            time.sleep(2)
            
            # Check if node is healthy
            node_addr = f"localhost:{port}"
            if wait_for_node(node_addr):
                nodes.append(node_addr)
                logger.success(f"Started {node_id} on port {port}")
            else:
                logger.error(f"Failed to start {node_id}")
                
        except Exception as e:
            logger.error(f"Error starting node: {e}")
            
    return nodes

def wait_for_node(node_addr: str, timeout: int = 30) -> bool:
    """Wait for a node to become healthy"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{node_addr}/health", timeout=1)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.5)
        
    return False

def ensure_cluster_running(logger: DemoLogger) -> List[str]:
    """Ensure a cluster is running, either existing or start a new one"""
    
    # Check environment variable first
    cluster_env = os.environ.get('CLUSTER_NODES')
    if cluster_env:
        nodes = [node.strip() for node in cluster_env.split(',')]
        logger.info(f"Using cluster from CLUSTER_NODES env: {nodes}")
        if check_cluster_status(nodes):
            return nodes
        else:
            logger.warning("Some nodes in CLUSTER_NODES are unhealthy")
            
    # Check for config file
    config_path = find_cluster_config()
    if config_path:
        logger.info(f"Found cluster config at: {config_path}")
        nodes = read_cluster_config(config_path)
        if nodes and check_cluster_status(nodes):
            return nodes
        else:
            logger.warning("Configured cluster is not healthy")
            
    # Try common local ports
    local_nodes = ["localhost:9999", "localhost:10000", "localhost:10001"]
    logger.info("Checking for local cluster on default ports...")
    if check_cluster_status(local_nodes):
        return local_nodes
        
    # Ask user what to do
    logger.warning("No healthy cluster found!")
    print("\nOptions:")
    print("1. Start a new local cluster")
    print("2. Specify cluster nodes manually")
    print("3. Exit")
    
    choice = input("\nChoose option (1-3): ").strip()
    
    if choice == "1":
        return start_local_cluster(logger)
    elif choice == "2":
        nodes_input = input("Enter comma-separated node addresses (e.g., localhost:8000,localhost:8001): ")
        nodes = [node.strip() for node in nodes_input.split(',')]
        if check_cluster_status(nodes):
            # Save for future use
            os.environ['CLUSTER_NODES'] = ','.join(nodes)
            return nodes
        else:
            logger.error("Specified nodes are not healthy")
            return []
    else:
        logger.info("Exiting...")
        return []

def format_json(data: dict) -> str:
    """Format JSON data for pretty printing"""
    return json.dumps(data, indent=2, sort_keys=True)

def create_test_data(prefix: str, count: int) -> dict:
    """Create test data for demos"""
    data = {}
    for i in range(count):
        key = f"{prefix}_{i}"
        data[key] = {
            "id": i,
            "value": f"Test value {i}",
            "timestamp": time.time(),
            "metadata": {
                "created_by": "demo",
                "version": 1
            }
        }
    return data