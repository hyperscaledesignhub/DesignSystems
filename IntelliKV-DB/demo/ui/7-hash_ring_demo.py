#!/usr/bin/env python3
"""
Hash Ring Visualization Demo for Distributed Database
Shows consistent hashing, virtual nodes, and key distribution
"""
import os
import sys
import json
import time
import threading
import requests
import random
import math
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hash-ring-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
CURRENT_RING_STATE = {}
MIGRATION_BASELINE = None

def create_mock_virtual_nodes(physical_nodes):
    """Create mock virtual node data for visualization when hashring library doesn't expose it"""
    import hashlib
    virtual_mapping = {}
    
    for node in physical_nodes:
        vnodes = []
        for i in range(150):  # 150 virtual nodes per physical node
            vnode_name = f"{node}-{i}"
            hash_val = int(hashlib.md5(vnode_name.encode()).hexdigest(), 16)
            position = hash_val / (2**128)  # Normalize to 0-1
            vnodes.append({
                "virtual_node_name": vnode_name,
                "hash": hash_val,
                "position": position
            })
        virtual_mapping[node] = sorted(vnodes, key=lambda x: x['position'])
    
    return virtual_mapping

def get_cluster_nodes():
    """Get cluster nodes from environment or default"""
    global CLUSTER_NODES
    if not CLUSTER_NODES:
        cluster_env = os.environ.get('CLUSTER_NODES')
        if cluster_env:
            CLUSTER_NODES = [node.strip() for node in cluster_env.split(',')]
        else:
            CLUSTER_NODES = ["localhost:9999", "localhost:10000", "localhost:10001"]
    return CLUSTER_NODES

@app.route('/')
def hash_ring_demo():
    """Hash ring visualization demo UI"""
    return render_template('hash_ring_demo.html')

@app.route('/api/ring/status')
def get_ring_status():
    """Get current hash ring status from cluster"""
    nodes = get_cluster_nodes()
    
    # Try to get ring info from first available node
    for node in nodes:
        try:
            # Get virtual node details
            vnode_response = requests.get(f"http://{node}/ring/virtual-nodes", timeout=3)
            if vnode_response.status_code == 200:
                ring_data = vnode_response.json()
                
                # If virtual_node_mapping is not available, create mock data for visualization
                if ring_data.get('virtual_node_mapping') == "not available with hashring library":
                    ring_data['virtual_node_mapping'] = create_mock_virtual_nodes(ring_data.get('physical_nodes', []))
                    ring_data['virtual_nodes'] = len(ring_data.get('physical_nodes', [])) * 150
                    ring_data['virtual_nodes_per_physical'] = 150
                
                # Get key distribution
                dist_response = requests.get(f"http://{node}/ring/key-distribution", timeout=3)
                if dist_response.status_code == 200:
                    distribution_data = dist_response.json()
                    ring_data['key_distribution'] = distribution_data
                
                # Get migration analysis if baseline exists
                if MIGRATION_BASELINE:
                    migration_response = requests.get(f"http://{node}/ring/migration-analysis", timeout=3)
                    if migration_response.status_code == 200:
                        ring_data['migration'] = migration_response.json()
                
                return jsonify({
                    "success": True,
                    "ring_data": ring_data,
                    "timestamp": time.time()
                })
        except Exception as e:
            continue
    
    return jsonify({"success": False, "error": "Could not get ring status from any node"}), 500

@app.route('/api/ring/initialize', methods=['POST'])
def initialize_ring():
    """Initialize hash ring visualization"""
    nodes = get_cluster_nodes()
    
    # Reset migration tracking on all nodes
    for node in nodes:
        try:
            requests.post(f"http://{node}/ring/reset-migration-tracking", timeout=3)
        except:
            continue
    
    global MIGRATION_BASELINE
    MIGRATION_BASELINE = time.time()
    
    return jsonify({
        "success": True,
        "message": "Hash ring initialized and migration tracking reset",
        "nodes": nodes
    })

@app.route('/api/node/add', methods=['POST'])
def add_node():
    """Add a new node to the cluster using cluster management API"""
    data = request.json
    new_node_address = data.get('address', 'localhost:10002')
    
    # Extract host and port from address
    if ':' in new_node_address:
        host, port = new_node_address.split(':')
        port = int(port)
    else:
        host = new_node_address
        port = None
    
    nodes = get_cluster_nodes()
    if not nodes:
        return jsonify({"success": False, "error": "No existing nodes to join"}), 400
    
    try:
        # FIRST: Reset migration tracking to establish baseline BEFORE adding node
        reset_response = requests.post(f"http://{nodes[0]}/ring/reset-migration-tracking", timeout=3)
        time.sleep(1)  # Give it time to reset
        
        # SECOND: Call migration API to initialize metadata with current state (before add)
        baseline_response = requests.get(f"http://{nodes[0]}/ring/migration-analysis", timeout=3)
        baseline_data = baseline_response.json() if baseline_response.status_code == 200 else {}
        print(f"Baseline established with {len(nodes)} nodes")
        
        # THIRD: Use the new cluster management API to add node
        add_data = {
            "host": host,
            "config_file": "yaml/config-local.yaml"
        }
        if port:
            add_data["port"] = port
        
        response = requests.post(f"http://{nodes[0]}/cluster/add-node", 
                               json=add_data, 
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            # Add to our node list
            if result.get('success'):
                new_address = result.get('node_address', new_node_address)
                if new_address not in CLUSTER_NODES:
                    CLUSTER_NODES.append(new_address)
                
                # FOURTH: Get migration analysis after node addition
                time.sleep(3)  # Wait for ring to stabilize 
                migration_response = requests.get(f"http://{nodes[0]}/ring/migration-analysis", timeout=5)
                migration_data = migration_response.json() if migration_response.status_code == 200 else {}
                
                # Debug: Check if migration data is correct
                if migration_data:
                    print(f"Migration analysis: prev={migration_data.get('previous_node_count')}, curr={migration_data.get('current_node_count')}")
                    print(f"Keys migrated: {migration_data.get('migration_summary', {}).get('keys_migrated', 0)}")
                
                return jsonify({
                    "success": True,
                    "message": result.get('message', f"Node {new_address} added to cluster"),
                    "node_info": result,
                    "migration": migration_data
                })
            else:
                return jsonify({"success": False, "error": result.get('error', 'Unknown error')}), 500
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {"error": "HTTP error"}
            return jsonify({"success": False, "error": error_data.get('error', f"HTTP {response.status_code}")}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/node/remove', methods=['POST'])
def remove_node():
    """Remove a node from the cluster using cluster management API"""
    data = request.json
    node_to_remove = data.get('address')
    
    if not node_to_remove:
        return jsonify({"success": False, "error": "No node address provided"}), 400
    
    nodes = get_cluster_nodes()
    if not nodes:
        return jsonify({"success": False, "error": "No nodes available"}), 400
    
    # Don't allow removing original cluster nodes (for demo stability)
    original_nodes = ["localhost:9999", "localhost:10000", "localhost:10001"]
    if node_to_remove in original_nodes:
        return jsonify({"success": False, "error": "Cannot remove original cluster nodes in demo"}), 400
    
    try:
        # FIRST: Reset migration tracking to establish baseline
        reset_response = requests.post(f"http://{nodes[0]}/ring/reset-migration-tracking", timeout=3)
        
        # SECOND: Call migration API to initialize metadata
        baseline_response = requests.get(f"http://{nodes[0]}/ring/migration-analysis", timeout=3)
        
        # THIRD: Use the new cluster management API to remove node
        remove_data = {
            "node_address": node_to_remove,
            "stop_process": True
        }
        
        # Find a node other than the one being removed to send request to
        target_node = None
        for node in nodes:
            if node != node_to_remove:
                target_node = node
                break
        
        if not target_node:
            return jsonify({"success": False, "error": "No other nodes available to process removal"}), 400
        
        response = requests.post(f"http://{target_node}/cluster/remove-node", 
                               json=remove_data, 
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                # Remove from our node list
                if node_to_remove in CLUSTER_NODES:
                    CLUSTER_NODES.remove(node_to_remove)
                
                # FOURTH: Get migration analysis after node removal
                time.sleep(3)  # Wait for ring to stabilize
                migration_response = requests.get(f"http://{target_node}/ring/migration-analysis", timeout=5)
                migration_data = migration_response.json() if migration_response.status_code == 200 else {}
                
                return jsonify({
                    "success": True,
                    "message": result.get('message', f"Node {node_to_remove} removed from cluster"),
                    "migration": migration_data
                })
            else:
                return jsonify({"success": False, "error": result.get('error', 'Unknown error')}), 500
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {"error": "HTTP error"}
            return jsonify({"success": False, "error": error_data.get('error', f"HTTP {response.status_code}")}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/keys/test', methods=['POST'])
def test_key_distribution():
    """Test key distribution with sample keys"""
    data = request.json
    num_keys = data.get('num_keys', 100)
    
    nodes = get_cluster_nodes()
    if not nodes:
        return jsonify({"success": False, "error": "No nodes available"}), 400
    
    try:
        # Generate test keys
        test_keys = [f"test_key_{i}" for i in range(num_keys)]
        keys_param = ','.join(test_keys)
        
        # Get key distribution analysis
        response = requests.get(
            f"http://{nodes[0]}/ring/key-distribution",
            params={"keys": keys_param},
            timeout=5
        )
        
        if response.status_code == 200:
            distribution_data = response.json()
            
            # Emit real-time update
            socketio.emit('key_distribution_update', {
                'distribution': distribution_data,
                'timestamp': time.time()
            })
            
            return jsonify({
                "success": True,
                "distribution": distribution_data,
                "keys_tested": num_keys
            })
        else:
            return jsonify({"success": False, "error": "Failed to analyze key distribution"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cluster/health')
def cluster_health():
    """Get health status of all nodes using cluster management API"""
    nodes = get_cluster_nodes()
    if not nodes:
        return jsonify({"nodes": {}, "cluster_size": 0, "healthy_nodes": 0})
    
    try:
        # Use the new cluster list-nodes API
        response = requests.get(f"http://{nodes[0]}/cluster/list-nodes", timeout=5)
        if response.status_code == 200:
            cluster_data = response.json()
            
            # Convert to our format
            health_status = {}
            for node_info in cluster_data.get('nodes', []):
                node_address = node_info.get('node_address')
                if node_address:
                    health_status[node_address] = {
                        "status": "healthy" if node_info.get('status') == 'running' else "unhealthy",
                        "node_id": node_info.get('node_id', node_address),
                        "is_running": node_info.get('status') == 'running',
                        "is_current": node_info.get('is_current', False)
                    }
            
            return jsonify({
                "nodes": health_status,
                "cluster_size": cluster_data.get('cluster_size', len(health_status)),
                "healthy_nodes": sum(1 for n in health_status.values() if n["status"] == "healthy")
            })
        else:
            # Fallback to individual health checks
            health_status = {}
            for node in nodes:
                try:
                    response = requests.get(f"http://{node}/health", timeout=2)
                    if response.status_code == 200:
                        health_data = response.json()
                        health_status[node] = {
                            "status": "healthy",
                            "node_id": health_data.get("node_id", node),
                            "is_running": health_data.get("is_running", True)
                        }
                    else:
                        health_status[node] = {"status": "unhealthy", "code": response.status_code}
                except Exception as e:
                    health_status[node] = {"status": "offline", "error": str(e)}
            
            return jsonify({
                "nodes": health_status,
                "cluster_size": len(nodes),
                "healthy_nodes": sum(1 for n in health_status.values() if n["status"] == "healthy")
            })
            
    except Exception as e:
        return jsonify({"error": str(e), "nodes": {}, "cluster_size": 0, "healthy_nodes": 0}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to hash ring demo'})

@socketio.on('refresh_ring')
def handle_refresh():
    """Refresh ring visualization"""
    # Get current ring state
    nodes = get_cluster_nodes()
    if nodes:
        try:
            response = requests.get(f"http://{nodes[0]}/ring/virtual-nodes", timeout=3)
            if response.status_code == 200:
                ring_data = response.json()
                emit('ring_update', ring_data)
        except:
            pass

if __name__ == '__main__':
    print("=" * 50)
    print("🎯 Hash Ring Visualization Demo")
    print("=" * 50)
    print("📍 URL: http://localhost:8007")
    print("🔧 Features:")
    print("  - Virtual node visualization")
    print("  - Key distribution analysis")
    print("  - Node addition/removal impact")
    print("  - Migration tracking")
    print("=" * 50)
    
    socketio.run(app, debug=False, host='0.0.0.0', port=8007, allow_unsafe_werkzeug=True)