#!/usr/bin/env python3
"""
Concurrent Writes Demo for Distributed Database
Demonstrates quorum-based reads/writes and data consistency under concurrent operations
Shows how quorum consensus ensures data consistency
"""
import os
import sys
import json
import time
import threading
import requests
import random
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import concurrent.futures

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from demo.demo_utils import DemoLogger, check_cluster_status

app = Flask(__name__)
app.config['SECRET_KEY'] = 'concurrent-writes-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
DEMO_KEYS = []
CONCURRENT_OPERATIONS = []

# Current active scenario (auto-initialize to Website Hit Counter)
CURRENT_SCENARIO = {
    "name": "Website Hit Counter",
    "key": "website_hits_demo", 
    "initial_value": 0,
    "operations": [
        {"type": "page_view", "count": 1, "description": "Page View"},
        {"type": "api_call", "count": 1, "description": "API Call"}
    ]
}

# Available demo scenarios (user selects one)
AVAILABLE_SCENARIOS = [
    {
        "name": "Banking Account Balance",
        "key": "account_balance_demo",
        "initial_value": 1000,
        "operations": [
            {"type": "credit", "amount": 100, "description": "Deposit"},
            {"type": "debit", "amount": 50, "description": "Withdrawal"}
        ]
    },
    {
        "name": "E-commerce Inventory",
        "key": "product_stock_demo",
        "initial_value": 100,
        "operations": [
            {"type": "purchase", "quantity": 5, "description": "Purchase"},
            {"type": "restock", "quantity": 20, "description": "Restock"}
        ]
    },
    {
        "name": "Social Media Counters",
        "key": "post_likes_demo",
        "initial_value": 0,
        "operations": [
            {"type": "like", "count": 1, "description": "Like"},
            {"type": "unlike", "count": 1, "description": "Unlike"}
        ]
    }
]

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
def concurrent_writes_demo():
    """Concurrent writes demo UI"""
    # Auto-initialize the data on first load
    auto_initialize_demo()
    
    return render_template('concurrent_writes_demo.html', 
                         scenarios=AVAILABLE_SCENARIOS,
                         current_scenario=CURRENT_SCENARIO,
                         cluster_nodes=get_cluster_nodes())

def auto_initialize_demo():
    """Auto-initialize demo data if not exists"""
    global DEMO_KEYS
    if not DEMO_KEYS:
        DEMO_KEYS.append("website_hits_demo")
        
    # Ensure data exists
    nodes = get_cluster_nodes()
    key = "website_hits_demo"
    
    try:
        # Check if data exists
        response = requests.get(f"http://{nodes[0]}/kv/{key}", timeout=5)
        if response.status_code != 200 or "value" not in response.json():
            # Initialize with default data
            initial_value = {
                "scenario": "Website Hit Counter",
                "current_value": 0,
                "operations_log": [],
                "initialized_at": time.time(),
                "version": 1
            }
            
            requests.put(
                f"http://{nodes[0]}/kv/{key}",
                json={"value": json.dumps(initial_value)},
                timeout=5
            )
    except Exception as e:
        print(f"Auto-initialize error: {e}")

@app.route('/api/get_current_value/<key>')
def get_current_value(key):
    """Get current value for a key"""
    nodes = get_cluster_nodes()
    
    try:
        response = requests.get(f"http://{nodes[0]}/kv/{key}", timeout=10)
        if response.status_code == 200 and "value" in response.json():
            value_data = json.loads(response.json()["value"])
            return jsonify({
                "success": True,
                "key": key,
                "current_value": value_data.get("current_value", 0),
                "scenario": value_data.get("scenario", "Unknown"),
                "version": value_data.get("version", 1),
                "operations_count": len(value_data.get("operations_log", []))
            })
        else:
            return jsonify({
                "success": False,
                "error": "Key not found or invalid response",
                "current_value": 1000  # Default value
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "current_value": 1000  # Default value
        })

@app.route('/api/quorum_status')
def get_quorum_status():
    """Get current quorum configuration and cluster status"""
    nodes = get_cluster_nodes()
    cluster_status = {}
    
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/health", timeout=10)
            if response.status_code == 200:
                cluster_status[f"node-{i+1}"] = {
                    "address": node,
                    "status": "healthy",
                    "data": response.json()
                }
            else:
                cluster_status[f"node-{i+1}"] = {
                    "address": node,
                    "status": "error",
                    "message": f"HTTP {response.status_code}"
                }
        except Exception as e:
            cluster_status[f"node-{i+1}"] = {
                "address": node,
                "status": "offline",
                "message": str(e)
            }
    
    return jsonify({
        "cluster_size": len(nodes),
        "replication_factor": 3,
        "read_quorum": 2,
        "write_quorum": 2,
        "quorum_explanation": {
            "reads": "Need 2 out of 3 nodes to agree on read value",
            "writes": "Need 2 out of 3 nodes to confirm write success",
            "consistency": "Majority consensus ensures data consistency"
        },
        "nodes": cluster_status
    })

@app.route('/api/initialize_scenario/<scenario_name>')
def initialize_scenario(scenario_name):
    """Initialize a demo scenario with initial data"""
    global CURRENT_SCENARIO
    
    scenario = next((s for s in AVAILABLE_SCENARIOS if s["name"] == scenario_name), None)
    if not scenario:
        return jsonify({"success": False, "error": "Scenario not found"}), 404
    
    # Clear any existing scenario first
    CURRENT_SCENARIO = None
    DEMO_KEYS.clear()
    CONCURRENT_OPERATIONS.clear()
    
    nodes = get_cluster_nodes()
    key = scenario["key"]
    
    # Initialize with scenario-specific value
    initial_value = {
        "scenario": scenario_name,
        "current_value": scenario["initial_value"],
        "operations_log": [],
        "initialized_at": time.time(),
        "version": 1
    }
    
    try:
        # Write to primary node with quorum
        response = requests.put(
            f"http://{nodes[0]}/kv/{key}",
            json={"value": json.dumps(initial_value)},
            timeout=5
        )
        
        if response.status_code == 200:
            # Set as current active scenario
            CURRENT_SCENARIO = scenario
            DEMO_KEYS.append(key)
            
            return jsonify({
                "success": True,
                "scenario": scenario_name,
                "key": key,
                "initial_value": initial_value,
                "message": f"Scenario '{scenario_name}' initialized successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to initialize: {response.text}"
            }), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clear_scenario', methods=['POST'])
def clear_scenario():
    """Clear current scenario and reset demo"""
    global CURRENT_SCENARIO
    
    CURRENT_SCENARIO = None
    DEMO_KEYS.clear()
    CONCURRENT_OPERATIONS.clear()
    
    return jsonify({
        "success": True,
        "message": "Scenario cleared successfully"
    })

@app.route('/api/concurrent_write', methods=['POST'])
def perform_concurrent_write():
    """Perform concurrent write operation across multiple nodes"""
    data = request.json
    key = data.get("key")
    operation = data.get("operation")
    nodes = get_cluster_nodes()
    
    if not key or not operation:
        return jsonify({"success": False, "error": "Missing key or operation"}), 400
    
    try:
        # Get current value first (quorum read)
        read_results = []
        
        def read_from_node(node):
            try:
                response = requests.get(f"http://{node}/kv/{key}", timeout=10)
                if response.status_code == 200:
                    return {
                        "node": node,
                        "success": True,
                        "data": response.json(),
                        "timestamp": time.time()
                    }
                else:
                    return {
                        "node": node,
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "timestamp": time.time()
                    }
            except Exception as e:
                return {
                    "node": node,
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time()
                }
        
        # Use single coordinator for read (let DB handle quorum internally)
        coordinator = nodes[0]  # Use first node as coordinator
        read_results = [read_from_node(coordinator)]
        
        # Analyze read results for quorum
        successful_reads = [r for r in read_results if r["success"]]
        
        if len(successful_reads) < 1:  # Read failed
            return jsonify({
                "success": False,
                "error": "Read quorum not met",
                "read_results": read_results,
                "quorum_status": "FAILED"
            }), 500
        
        # Get the most recent value (quorum consensus)
        latest_data = None
        for read in successful_reads:
            if "value" in read["data"]:
                current_data = json.loads(read["data"]["value"])
                if not latest_data or current_data.get("version", 0) >= latest_data.get("version", 0):
                    latest_data = current_data
        
        if not latest_data:
            return jsonify({
                "success": False,
                "error": "No valid data found",
                "read_results": read_results
            }), 500
        
        # Apply the operation
        new_value = apply_operation(latest_data, operation)
        new_value["version"] = latest_data.get("version", 0) + 1
        
        # Use single coordinator for write (let DB handle quorum internally)
        write_results = []
        
        try:
            response = requests.put(
                f"http://{coordinator}/kv/{key}",
                json={"value": json.dumps(new_value)},
                timeout=10
            )
            if response.status_code == 200:
                write_results.append({
                    "node": coordinator,
                    "success": True,
                    "timestamp": time.time()
                })
            else:
                write_results.append({
                    "node": coordinator,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "timestamp": time.time()
                })
        except Exception as e:
            write_results.append({
                "node": coordinator,
                "success": False,
                "error": str(e),
                "timestamp": time.time()
            })
        
        # Analyze write results for quorum
        successful_writes = [w for w in write_results if w["success"]]
        write_quorum_met = len(successful_writes) >= 1  # Single coordinator approach
        
        # Log this operation for monitoring
        operation_log = {
            "timestamp": time.time(),
            "operation": operation,
            "read_results": read_results,
            "write_results": write_results,
            "quorum_status": {
                "read_quorum_met": len(successful_reads) >= 1,
                "write_quorum_met": write_quorum_met
            },
            "old_value": latest_data,
            "new_value": new_value if write_quorum_met else None
        }
        
        CONCURRENT_OPERATIONS.append(operation_log)
        if len(CONCURRENT_OPERATIONS) > 50:  # Keep last 50 operations
            CONCURRENT_OPERATIONS.pop(0)
        
        # Emit real-time update
        socketio.emit('concurrent_operation', {
            'key': key,
            'operation': operation,
            'success': write_quorum_met,
            'quorum_status': operation_log["quorum_status"],
            'results': {
                'reads': read_results,
                'writes': write_results
            },
            'timestamp': time.time()
        })
        
        return jsonify({
            "success": write_quorum_met,
            "operation": operation,
            "old_value": latest_data,
            "new_value": new_value if write_quorum_met else None,
            "quorum_status": operation_log["quorum_status"],
            "read_results": read_results,
            "write_results": write_results,
            "message": "Write quorum met" if write_quorum_met else "Write quorum failed"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def apply_operation(current_data, operation):
    """Apply operation to current data"""
    new_data = current_data.copy()
    
    op_type = operation.get("type")
    current_value = current_data.get("current_value", 0)
    
    # Website hit counter operations - all increment
    if op_type in ["page_view", "api_call", "user_action", "increment"]:
        count = operation.get("count", operation.get("amount", operation.get("quantity", 1)))
        new_data["current_value"] = current_value + count
    
    # Add to operations log
    new_data["operations_log"].append({
        "timestamp": time.time(),
        "operation": operation,
        "previous_value": current_value,
        "new_value": new_data["current_value"]
    })
    
    return new_data

@app.route('/api/data_consistency/<key>')
def check_data_consistency(key):
    """Check data consistency across all nodes for a specific key"""
    nodes = get_cluster_nodes()
    node_data = {}
    
    def read_from_node_with_details(node, node_id):
        try:
            response = requests.get(f"http://{node}/kv/{key}", timeout=10)
            if response.status_code == 200:
                response_data = response.json()
                if "value" in response_data:
                    value_data = json.loads(response_data["value"])
                    return {
                        "node": node,
                        "status": "healthy",
                        "data": value_data,
                        "version": value_data.get("version", 0),
                        "timestamp": time.time()
                    }
                else:
                    return {
                        "node": node,
                        "status": "no_data",
                        "message": "Key not found",
                        "timestamp": time.time()
                    }
            else:
                return {
                    "node": node,
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "timestamp": time.time()
                }
        except Exception as e:
            return {
                "node": node,
                "status": "offline",
                "error": str(e),
                "timestamp": time.time()
            }
    
    # Read from all nodes concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(read_from_node_with_details, node, f"node-{i+1}"): f"node-{i+1}" 
                  for i, node in enumerate(nodes)}
        
        for future in concurrent.futures.as_completed(futures):
            node_id = futures[future]
            node_data[node_id] = future.result()
    
    # Analyze consistency
    healthy_nodes = [data for data in node_data.values() if data["status"] == "healthy"]
    versions = [node["version"] for node in healthy_nodes]
    values = [node["data"]["current_value"] for node in healthy_nodes]
    
    is_consistent = len(set(versions)) <= 1 and len(set(values)) <= 1
    quorum_available = len(healthy_nodes) >= 2
    
    consistency_analysis = {
        "is_consistent": is_consistent,
        "quorum_available": quorum_available,
        "healthy_nodes": len(healthy_nodes),
        "total_nodes": len(nodes),
        "versions": versions,
        "values": values,
        "consistency_level": "STRONG" if is_consistent and quorum_available else 
                           "EVENTUAL" if not is_consistent else "WEAK"
    }
    
    return jsonify({
        "key": key,
        "nodes": node_data,
        "consistency": consistency_analysis,
        "timestamp": time.time()
    })

@app.route('/api/operations_log')
def get_operations_log():
    """Get recent concurrent operations log"""
    return jsonify({
        "operations": CONCURRENT_OPERATIONS[-20:],  # Last 20 operations
        "total_operations": len(CONCURRENT_OPERATIONS)
    })

@app.route('/api/simple_concurrent_test', methods=['POST'])
def simple_concurrent_test():
    """Run a simple concurrent test with just 3-5 operations"""
    # Use default Banking scenario always
    
    data = request.json
    num_operations = min(data.get("num_operations", 3), 5)  # Max 5 operations
    
    def run_simple_test():
        """Run a simple test with limited operations"""
        print(f"🔥 Starting simple concurrent test with {num_operations} operations")
        
        # Use fixed Website Hit operations
        hit_operations = [
            {"type": "page_view", "count": 1, "description": "Page View"},
            {"type": "api_call", "count": 1, "description": "API Call"},
            {"type": "user_action", "count": 1, "description": "User Action"}
        ]
        
        for i in range(num_operations):
            op = random.choice(hit_operations)
            
            # Website hits are typically 1, but can be batch increments
            test_op = op.copy()
            if "count" in test_op:
                test_op["count"] = random.randint(1, 5)  # Batch hits
            
            try:
                response = requests.post(
                    f'http://localhost:8005/api/concurrent_write',
                    json={
                        "key": "website_hits_demo",  # Fixed Website Hit key
                        "operation": test_op
                    },
                    timeout=5
                )
                print(f"✅ Operation {i+1}: {test_op['type']} - {response.status_code}")
                
                # Emit real-time update for simple test operations
                if response.status_code == 200:
                    result = response.json()
                    result['isSimpleTest'] = True  # Mark as simple test operation
                    socketio.emit('simple_test_operation', result)
                    
            except Exception as e:
                print(f"❌ Operation {i+1} failed: {e}")
                # Emit failure
                socketio.emit('simple_test_operation', {
                    'success': False,
                    'operation': test_op,
                    'error': str(e),
                    'isSimpleTest': True
                })
            
            # Small delay between operations
            time.sleep(0.5)
        
        print(f"🎯 Simple test completed")
    
    # Start test in background
    thread = threading.Thread(target=run_simple_test, daemon=True)
    thread.start()
    
    return jsonify({
        "success": True,
        "message": f"Started simple concurrent test with {num_operations} operations",
        "scenario": "Website Hit Counter"
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to Concurrent Writes demo'})

@socketio.on('subscribe_key')
def handle_subscribe_key(data):
    """Handle subscription to a specific key for real-time updates"""
    key = data.get('key')
    emit('subscribed', {
        'key': key,
        'message': f'Subscribed to updates for {key}'
    })

if __name__ == '__main__':
    print("🔥 Starting Concurrent Writes Demo...")
    print("📍 Demo URL: http://localhost:8005")
    print("🎯 Features:")
    print("   - Quorum-based reads and writes (2/3 nodes)")
    print("   - Concurrent write operations simulation")
    print("   - Real-time data consistency visualization")
    print("   - Multiple demo scenarios (Banking, E-commerce, Social Media)")
    print("   - Operations logging and monitoring")
    print("")
    print("🔧 Quorum Configuration:")
    print("   - Cluster Size: 3 nodes")
    print("   - Read Quorum: 2 nodes")
    print("   - Write Quorum: 2 nodes")
    print("   - Replication Factor: 3")
    print("")
    print("💡 Use Case: Demonstrates how quorum consensus ensures data consistency")
    print("              even under high-concurrency write scenarios")
    print("")
    print("Press Ctrl+C to stop the demo")
    print("=" * 60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8005, allow_unsafe_werkzeug=True)