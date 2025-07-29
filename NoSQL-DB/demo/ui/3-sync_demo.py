#!/usr/bin/env python3
"""
Simple Data Sync Demo - Shows how nodes sync data after recovery
No health polling, no heartbeats - just data operations
"""
import os
import sys
import json
import time
import subprocess
import signal
import requests
import random
from flask import Flask, render_template, jsonify, request

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = Flask(__name__)

# Simple configuration
NODES = {
    "node-1": {"address": "localhost:9999", "process": None},
    "node-2": {"address": "localhost:10000", "process": None},
    "node-3": {"address": "localhost:10001", "process": None}
}

# Track which node is stopped
STOPPED_NODE = None
GENERATED_KEYS = []

@app.route('/')
def sync_demo():
    """Main demo page"""
    return render_template('sync_demo.html')

@app.route('/api/generate_data', methods=['POST'])
def generate_data():
    """Generate test data across all nodes"""
    global GENERATED_KEYS
    
    # Generate 5 random key-value pairs
    new_keys = []
    for i in range(5):
        key = f"test_key_{int(time.time())}_{i}"
        value = f"value_{random.randint(1000, 9999)}"
        
        # Write to first available node (it will replicate)
        success = False
        for node_id, node_info in NODES.items():
            try:
                response = requests.put(
                    f"http://{node_info['address']}/kv/{key}",
                    json={"value": value},
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    success = True
                    new_keys.append({"key": key, "value": value})
                    GENERATED_KEYS.append(key)
                    break
            except:
                continue
        
        if not success:
            return jsonify({"success": False, "error": "Failed to write data to any node"})
    
    # Keep only last 20 keys
    if len(GENERATED_KEYS) > 20:
        GENERATED_KEYS = GENERATED_KEYS[-20:]
    
    return jsonify({
        "success": True,
        "generated": new_keys,
        "message": f"Generated {len(new_keys)} key-value pairs"
    })

@app.route('/api/get_all_node_data')
def get_all_node_data():
    """Get data from all nodes without health checks"""
    node_data = {}
    
    for node_id, node_info in NODES.items():
        node_data[node_id] = {
            "address": node_info["address"],
            "status": "stopped" if node_id == STOPPED_NODE else "running",
            "data": {}
        }
        
        # Skip if node is stopped
        if node_id == STOPPED_NODE:
            continue
            
        # Get data for all generated keys
        for key in GENERATED_KEYS[-10:]:  # Check last 10 keys
            try:
                response = requests.get(
                    f"http://{node_info['address']}/kv/{key}",
                    timeout=8
                )
                if response.status_code == 200:
                    data = response.json()
                    node_data[node_id]["data"][key] = data.get("value", "")
            except:
                # Node might be down or key doesn't exist
                pass
    
    return jsonify({
        "nodes": node_data,
        "total_keys": len(GENERATED_KEYS),
        "stopped_node": STOPPED_NODE
    })

@app.route('/api/stop_random_node', methods=['POST'])
def stop_random_node():
    """Stop a random node by killing its process"""
    global STOPPED_NODE
    
    if STOPPED_NODE:
        return jsonify({"success": False, "error": "A node is already stopped"})
    
    # Choose a random node to stop
    available_nodes = list(NODES.keys())
    STOPPED_NODE = random.choice(available_nodes)
    
    # Kill the node process
    node_address = NODES[STOPPED_NODE]["address"]
    port = node_address.split(":")[1]
    
    try:
        # Find and kill the process using the port
        result = subprocess.run(
            f"lsof -ti :{port} | xargs kill -9",
            shell=True,
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "success": True,
            "stopped_node": STOPPED_NODE,
            "message": f"Stopped {STOPPED_NODE} on port {port}"
        })
    except Exception as e:
        STOPPED_NODE = None
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/start_stopped_node', methods=['POST'])
def start_stopped_node():
    """Start the previously stopped node"""
    global STOPPED_NODE
    
    if not STOPPED_NODE:
        return jsonify({"success": False, "error": "No node is currently stopped"})
    
    node_id = STOPPED_NODE
    
    # Determine the correct SEED_NODE_ID based on node
    seed_node_map = {
        "node-1": "db-node-1",
        "node-2": "db-node-2", 
        "node-3": "db-node-3"
    }
    
    seed_node_id = seed_node_map[node_id]
    
    try:
        # Start the node
        process = subprocess.Popen(
            f"CONFIG_FILE=yaml/config-local.yaml SEED_NODE_ID={seed_node_id} python distributed/node.py",
            shell=True,
            cwd="/Users/vijayabhaskarv/hyper-scale/kvdb/DesignSystems/NoSQL-DB"
        )
        
        NODES[node_id]["process"] = process
        
        # Wait a bit for node to start
        time.sleep(3)
        
        # Clear stopped node
        started_node = STOPPED_NODE
        STOPPED_NODE = None
        
        return jsonify({
            "success": True,
            "started_node": started_node,
            "message": f"Started {started_node}. Data will sync automatically."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/check_sync_status')
def check_sync_status():
    """Check if all nodes have the same data"""
    if STOPPED_NODE:
        return jsonify({"synced": False, "reason": "A node is stopped"})
    
    # Compare data across all nodes for recent keys
    test_keys = GENERATED_KEYS[-5:] if GENERATED_KEYS else []
    
    if not test_keys:
        return jsonify({"synced": True, "reason": "No data to check"})
    
    node_values = {}
    for node_id, node_info in NODES.items():
        node_values[node_id] = {}
        for key in test_keys:
            try:
                response = requests.get(
                    f"http://{node_info['address']}/kv/{key}",
                    timeout=8
                )
                if response.status_code == 200:
                    data = response.json()
                    # Extract value properly from response
                    if isinstance(data, dict) and "value" in data:
                        node_values[node_id][key] = data["value"]
                    else:
                        node_values[node_id][key] = str(data)
            except:
                node_values[node_id][key] = None
    
    # Check if all nodes have same values
    synced = True
    for key in test_keys:
        values = [node_values[node_id].get(key) for node_id in NODES.keys()]
        # Remove None values (node might be starting)
        values = [v for v in values if v is not None]
        if len(set(values)) > 1:
            synced = False
            break
    
    return jsonify({
        "synced": synced,
        "node_values": node_values,
        "test_keys": test_keys
    })

if __name__ == '__main__':
    print("🚀 Starting Simple Sync Demo...")
    print("📍 Demo URL: http://localhost:8008")
    print("🎯 Features:")
    print("   - Generate test data")
    print("   - Stop random node")
    print("   - Show data on all nodes")
    print("   - Start stopped node")
    print("   - Observe automatic data sync")
    print("")
    print("💡 No health polling or heartbeats!")
    print("")
    print("Press Ctrl+C to stop the demo")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=8008)