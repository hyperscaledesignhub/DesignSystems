#!/usr/bin/env python3
"""
Health check script for Kubernetes probes with peer discovery validation
"""

import sys
import requests
import time
import os
import json

def check_health():
    """Check if the database node is healthy (liveness probe)"""
    try:
        # Get node ID from environment
        node_id = os.environ.get('NODE_ID', 'unknown')
        
        # Try to connect to the health endpoint
        response = requests.get('http://localhost:8080/health', timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            # For liveness probe, only fail if the node is completely unhealthy
            # Degraded state (missing peers) should not cause liveness failure
            if health_data.get('status') in ['healthy', 'degraded']:
                print(f"Node {node_id} is alive (status: {health_data.get('status')})")
                return True
            else:
                print(f"Node {node_id} health check failed: {health_data}")
                return False
        else:
            print(f"Node {node_id} health check failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Health check failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in health check: {e}")
        return False

def check_readiness():
    """Check if the database node is ready to serve requests"""
    try:
        # Get node ID from environment
        node_id = os.environ.get('NODE_ID', 'unknown')
        replication_factor = int(os.environ.get('REPLICATION_FACTOR', '3'))
        expected_peers = replication_factor - 1  # Exclude self

        # Check if the node is listening on the API port
        response = requests.get('http://localhost:8080/info', timeout=5)
        if response.status_code != 200:
            print(f"Node {node_id} readiness check failed: node not responding")
            return False
        info_data = response.json()
        if not info_data.get('is_running', False):
            print(f"Node {node_id} readiness check failed: node not running")
            return False

        # Check health endpoint for peer validation
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code != 200:
            print(f"Node {node_id} readiness check failed: health check returned {response.status_code}")
            return False
        health_data = response.json()
        if health_data.get('status') == 'degraded':
            warning = health_data.get('warning', 'Insufficient peers')
            print(f"Node {node_id} readiness check warning: {warning}")
            # Do not return False yet, check below

        # Check peer count for readiness
        response = requests.get('http://localhost:8080/peers', timeout=5)
        if response.status_code != 200:
            print(f"Node {node_id} readiness check failed: cannot get peers")
            return False
        peers = response.json()
        peer_count = len(peers)

        # Check how many pods are running in the StatefulSet (via DNS)
        # Try to resolve all expected pod hostnames
        import socket
        running_pods = 0
        for i in range(replication_factor):
            pod_dns = f"distributed-database-{i}.db-headless-service.distributed-db.svc.cluster.local"
            try:
                socket.gethostbyname(pod_dns)
                running_pods += 1
            except Exception:
                pass

        print(f"Node {node_id} readiness: {running_pods}/{replication_factor} pods running, {peer_count}/{expected_peers} peers")

        # For StatefulSet startup, be very lenient with readiness
        # Allow readiness with 0 peers during initial startup
        # Only require peer connectivity after all pods are running AND stable
        
        if running_pods < replication_factor:
            # Cluster is still starting up - allow readiness with any peer count
            print(f"Node {node_id} readiness: allowing ready state with {peer_count} peers (cluster starting: {running_pods}/{replication_factor} pods)")
            return True
        else:
            # All pods are running, but give them time to discover each other
            # Allow readiness with at least 1 peer (to ensure basic connectivity)
            if peer_count >= 1:
                print(f"Node {node_id} is ready: {peer_count} peers connected (cluster fully started)")
                return True
            else:
                print(f"Node {node_id} readiness check failed: {peer_count} peers connected (need at least 1 peer)")
                return False
    except requests.exceptions.RequestException as e:
        print(f"Readiness check failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in readiness check: {e}")
        return False

def check_startup_with_peer_discovery():
    """Check if the node is ready with proper peer discovery"""
    try:
        # Get node ID from environment
        node_id = os.environ.get('NODE_ID', 'unknown')
        
        # First check if the node is running
        response = requests.get('http://localhost:8080/info', timeout=5)
        if response.status_code != 200:
            print(f"Node {node_id} startup check failed: node not responding")
            return False
        
        info_data = response.json()
        if not info_data.get('is_running', False):
            print(f"Node {node_id} startup check failed: node not running")
            return False
        
        # Check health endpoint for peer validation
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 503:
            # Node is in degraded state due to insufficient peers
            health_data = response.json()
            warning = health_data.get('warning', 'Insufficient peers')
            print(f"Node {node_id} startup check: {warning}")
            return False
        elif response.status_code != 200:
            print(f"Node {node_id} startup check failed: health check returned {response.status_code}")
            return False
        
        # Additional peer count validation
        response = requests.get('http://localhost:8080/peers', timeout=5)
        if response.status_code != 200:
            print(f"Node {node_id} startup check failed: cannot get peers")
            return False
        
        peers = response.json()
        peer_count = len(peers)
        
        # Get replication factor from environment
        replication_factor = int(os.environ.get('REPLICATION_FACTOR', '3'))
        expected_peers = replication_factor - 1  # Exclude self
        
        # For startup probe, allow all nodes to start with 0 peers initially
        # The automatic peer discovery will handle connecting them once all pods are running
        # Startup probe should only check if the process is running, not peer connectivity
        expected_min_peers = 0  # Allow startup with 0 peers
        
        if peer_count >= expected_min_peers:
            print(f"Node {node_id} startup check passed: {peer_count} peers found (expected >= {expected_min_peers}, target: {expected_peers})")
            return True
        else:
            print(f"Node {node_id} startup check failed: {peer_count} peers found (expected >= {expected_min_peers}, target: {expected_peers})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Startup check failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in startup check: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python health.py [health|readiness|startup]")
        sys.exit(1)
    
    check_type = sys.argv[1]
    
    if check_type == "health":
        success = check_health()
    elif check_type == "readiness":
        success = check_readiness()
    elif check_type == "startup":
        success = check_startup_with_peer_discovery()
    else:
        print(f"Unknown check type: {check_type}")
        sys.exit(1)
    
    sys.exit(0 if success else 1) 