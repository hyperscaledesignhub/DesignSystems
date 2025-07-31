#!/usr/bin/env python3
"""
CRDT Counter Demo for Distributed Database
Demonstrates conflict-free counter operations that solve race condition problems
Shows how CRDT counters guarantee correctness even under high concurrency
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
app.config['SECRET_KEY'] = 'crdt-counter-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
DEMO_KEYS = []
CONCURRENT_OPERATIONS = []

# Current active scenario (auto-initialize to Website Hit Counter with CRDT)
CURRENT_SCENARIO = {
    "name": "Website Hit Counter (CRDT)",
    "key": "website_hits_crdt_demo", 
    "initial_value": 0,
    "operations": [
        {"type": "page_view", "amount": 1, "description": "Page View"},
        {"type": "api_call", "amount": 1, "description": "API Call"},
        {"type": "user_action", "amount": 1, "description": "User Action"}
    ]
}

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

def sync_crdt_counter_across_all_nodes(key):
    """Synchronize CRDT counter across all nodes using merge API"""
    nodes = get_cluster_nodes()
    all_node_contributions = {}
    
    try:
        # Collect contributions from all nodes
        for node in nodes:
            try:
                response = requests.get(f"http://{node}/counter/{key}", timeout=10)
                if response.status_code == 200:
                    node_data = response.json()
                    node_contributions = node_data.get("nodes", {})
                    # Merge contributions from this node
                    for node_id, contribution in node_contributions.items():
                        if node_id in all_node_contributions:
                            all_node_contributions[node_id] = max(all_node_contributions[node_id], contribution)
                        else:
                            all_node_contributions[node_id] = contribution
                elif response.status_code == 404:
                    continue  # Counter doesn't exist on this node yet
            except Exception as e:
                print(f"Failed to collect from {node}: {e}")
                continue
        
        if all_node_contributions:
            # Merge on ALL nodes to keep them consistent
            for node in nodes:
                try:
                    merge_response = requests.post(
                        f"http://{node}/counter/merge/{key}",
                        json={"nodes": all_node_contributions},
                        timeout=10
                    )
                    if merge_response.status_code != 200:
                        print(f"Failed to sync {node}: {merge_response.status_code}")
                except Exception as e:
                    print(f"Failed to sync {node}: {e}")
                    continue
        
        return all_node_contributions
    except Exception as e:
        print(f"Error syncing CRDT counter: {e}")
        return {}

@app.route('/')
def crdt_counter_demo():
    """CRDT counter demo UI"""
    # Auto-initialize the counter on first load
    auto_initialize_demo()
    
    return render_template('crdt_counter_demo.html', 
                         current_scenario=CURRENT_SCENARIO,
                         cluster_nodes=get_cluster_nodes())

def auto_initialize_demo():
    """Auto-initialize CRDT counter if not exists"""
    global DEMO_KEYS
    if not DEMO_KEYS:
        DEMO_KEYS.append("website_hits_crdt_demo")
        
    # Ensure counter exists - CRDT counters are auto-created on first increment
    # No need to pre-initialize like regular KV pairs

@app.route('/api/get_counter_value/<key>')
def get_counter_value(key):
    """Get current CRDT counter value by collecting from all nodes"""
    nodes = get_cluster_nodes()
    all_node_contributions = {}
    
    try:
        # Collect contributions from all nodes to get true CRDT value
        for node in nodes:
            try:
                response = requests.get(f"http://{node}/counter/{key}", timeout=10)
                if response.status_code == 200:
                    node_data = response.json()
                    node_contributions = node_data.get("nodes", {})
                    # Merge contributions from this node
                    for node_id, contribution in node_contributions.items():
                        if node_id in all_node_contributions:
                            all_node_contributions[node_id] = max(all_node_contributions[node_id], contribution)
                        else:
                            all_node_contributions[node_id] = contribution
                elif response.status_code == 404:
                    # Counter doesn't exist on this node yet
                    continue
            except Exception as e:
                print(f"Failed to get counter from {node}: {e}")
                continue
        
        # Calculate true CRDT value as sum of all node contributions
        total_value = sum(all_node_contributions.values())
        
        return jsonify({
            "success": True,
            "key": key,
            "current_value": total_value,
            "nodes": all_node_contributions,
            "total_nodes": len(all_node_contributions)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "current_value": 0
        })

@app.route('/api/cluster_status')
def get_cluster_status():
    """Get current cluster status"""
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
        "nodes": cluster_status,
        "crdt_features": {
            "conflict_free": "CRDT counters guarantee no lost increments",
            "concurrent_safe": "All concurrent operations are commutative",
            "eventually_consistent": "All nodes converge to the same state"
        }
    })

@app.route('/api/crdt_increment', methods=['POST'])
def perform_crdt_increment():
    """Perform CRDT counter increment operation"""
    data = request.json
    key = data.get("key")
    operation = data.get("operation")
    nodes = get_cluster_nodes()
    
    if not key or not operation:
        return jsonify({"success": False, "error": "Missing key or operation"}), 400
    
    # Choose a random node for this operation to simulate distributed writes
    node = random.choice(nodes)
    amount = operation.get("amount", 1)
    
    try:
        start_time = time.time()
        
        # Use CRDT counter increment API
        response = requests.post(
            f"http://{node}/counter/incr/{key}",
            json={"amount": amount},
            timeout=10
        )
        
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            
            # Synchronize CRDT counter across all nodes after increment
            print(f"🔄 Synchronizing CRDT counter across all nodes after increment...")
            all_contributions = sync_crdt_counter_across_all_nodes(key)
            
            # Get the synchronized state
            total_value = sum(all_contributions.values()) if all_contributions else result.get("new_value", 0)
            full_state = {"value": total_value, "nodes": all_contributions}
            
            operation_log = {
                "timestamp": time.time(),
                "operation": operation,
                "node_used": node,
                "old_value": max(0, total_value - amount),  # Calculate old value
                "new_value": total_value,
                "response_time": end_time - start_time,
                "counter_state": full_state,
                "success": True
            }
            
            CONCURRENT_OPERATIONS.append(operation_log)
            if len(CONCURRENT_OPERATIONS) > 100:  # Keep last 100 operations
                CONCURRENT_OPERATIONS.pop(0)
            
            # Emit real-time update
            socketio.emit('crdt_operation', {
                'key': key,
                'operation': operation,
                'success': True,
                'node_used': node,
                'old_value': max(0, total_value - amount),
                'new_value': total_value,
                'counter_state': full_state,
                'response_time': end_time - start_time,
                'timestamp': time.time()
            })
            
            return jsonify({
                "success": True,
                "operation": operation,
                "node_used": node,
                "old_value": max(0, total_value - amount),
                "new_value": total_value,
                "counter_state": full_state,
                "response_time": end_time - start_time,
                "message": "CRDT increment successful - synchronized across all nodes!"
            })
            
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            operation_log = {
                "timestamp": time.time(),
                "operation": operation,
                "node_used": node,
                "error": error_msg,
                "success": False
            }
            
            CONCURRENT_OPERATIONS.append(operation_log)
            
            return jsonify({
                "success": False,
                "error": error_msg,
                "node_used": node
            }), 500
            
    except Exception as e:
        error_msg = str(e)
        operation_log = {
            "timestamp": time.time(),
            "operation": operation,
            "node_used": node,
            "error": error_msg,
            "success": False
        }
        
        CONCURRENT_OPERATIONS.append(operation_log)
        
        return jsonify({
            "success": False,
            "error": error_msg,
            "node_used": node
        }), 500

@app.route('/api/mass_concurrent_crdt_test', methods=['POST'])
def mass_concurrent_crdt_test():
    """Run mass concurrent CRDT test to show no race conditions"""
    data = request.json
    num_operations = min(data.get("num_operations", 10), 20)  # Max 20 operations
    key = data.get("key", "website_hits_crdt_demo")
    
    def run_mass_test():
        """Run mass concurrent CRDT increments"""
        print(f"🚀 Starting mass CRDT test with {num_operations} concurrent operations")
        
        # Generate operations with random amounts
        operations = []
        total_expected = 0
        for i in range(num_operations):
            amount = random.randint(1, 5)
            total_expected += amount
            operations.append({
                "type": random.choice(["page_view", "api_call", "user_action"]),
                "amount": amount,
                "description": f"Concurrent operation {i+1}"
            })
        
        print(f"📊 Expected total increment: {total_expected}")
        
        # Get initial value
        try:
            response = requests.get(f"http://{get_cluster_nodes()[0]}/counter/{key}", timeout=10)
            if response.status_code == 200:
                initial_value = response.json().get("value", 0)
            else:
                initial_value = 0
        except:
            initial_value = 0
        
        print(f"📈 Initial value: {initial_value}")
        
        # Execute all operations truly simultaneously
        nodes = get_cluster_nodes()
        start_time = time.time()
        
        def single_increment(operation):
            node = random.choice(nodes)  # Random node for each operation
            try:
                response = requests.post(
                    f"http://{node}/counter/incr/{key}",
                    json={"amount": operation["amount"]},
                    timeout=10
                )
                return {
                    "success": response.status_code == 200,
                    "node": node,
                    "operation": operation,
                    "response": response.json() if response.status_code == 200 else None,
                    "error": None if response.status_code == 200 else response.text
                }
            except Exception as e:
                return {
                    "success": False,
                    "node": node,
                    "operation": operation,
                    "response": None,
                    "error": str(e)
                }
        
        # Execute all operations concurrently using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_operations) as executor:
            futures = [executor.submit(single_increment, op) for op in operations]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        # Wait a moment for all operations to complete and propagate
        time.sleep(2)
        
        # Get final value by collecting from ALL nodes and using CRDT merge API
        try:
            nodes = get_cluster_nodes()
            all_node_contributions = {}
            
            print(f"🔍 Collecting CRDT state from all nodes...")
            
            # Collect contributions from all nodes
            for i, node in enumerate(nodes):
                try:
                    response = requests.get(f"http://{node}/counter/{key}", timeout=10)
                    if response.status_code == 200:
                        node_data = response.json()
                        node_contributions = node_data.get("nodes", {})
                        print(f"   - Node {i+1} ({node}): {node_contributions}")
                        # Merge contributions from this node
                        for node_id, contribution in node_contributions.items():
                            if node_id in all_node_contributions:
                                all_node_contributions[node_id] = max(all_node_contributions[node_id], contribution)
                            else:
                                all_node_contributions[node_id] = contribution
                    elif response.status_code == 404:
                        print(f"   - Node {i+1} ({node}): No counter yet")
                except Exception as e:
                    print(f"   - Node {i+1} ({node}): Failed - {e}")
                    continue
            
            if all_node_contributions:
                # Use CRDT merge API on ALL nodes to keep them synchronized
                print(f"🔄 Using CRDT merge API to synchronize all nodes...")
                print(f"   - Merging contributions: {all_node_contributions}")
                
                # Merge on ALL nodes to keep them consistent
                merge_success = True
                for i, node in enumerate(nodes):
                    try:
                        merge_response = requests.post(
                            f"http://{node}/counter/merge/{key}",
                            json={"nodes": all_node_contributions},
                            timeout=10
                        )
                        
                        if merge_response.status_code == 200:
                            print(f"   - ✅ Node {i+1} ({node}): Merge successful")
                        else:
                            print(f"   - ❌ Node {i+1} ({node}): Merge failed - {merge_response.status_code}")
                            merge_success = False
                    except Exception as e:
                        print(f"   - ❌ Node {i+1} ({node}): Merge error - {e}")
                        merge_success = False
                
                if merge_success:
                    # Get the merged result from any node (they should all be the same now)
                    try:
                        final_response = requests.get(f"http://{nodes[0]}/counter/{key}", timeout=10)
                        if final_response.status_code == 200:
                            final_result = final_response.json()
                            final_value = final_result.get("value", 0)
                            node_breakdown = final_result.get("nodes", {})
                            print(f"   - ✅ All nodes synchronized! Total value: {final_value}")
                        else:
                            final_value = sum(all_node_contributions.values())
                            node_breakdown = all_node_contributions
                    except:
                        final_value = sum(all_node_contributions.values())
                        node_breakdown = all_node_contributions
                else:
                    # Fallback to manual sum if merge failed
                    final_value = sum(all_node_contributions.values())
                    node_breakdown = all_node_contributions
                    print(f"   - Manual sum fallback: {final_value}")
            else:
                final_value = 0
                node_breakdown = {}
                print(f"   - No contributions found")
            
            print(f"🎯 Final CRDT Analysis:")
            print(f"   - Node contributions: {node_breakdown}")
            print(f"   - True CRDT value: {final_value}")
            
        except Exception as e:
            print(f"❌ Error getting CRDT state: {e}")
            final_value = 0
            node_breakdown = {}
        
        actual_increment = final_value - initial_value
        expected_final = initial_value + total_expected
        
        print(f"✅ Mass CRDT test completed!")
        print(f"📊 Results:")
        print(f"   - Initial value: {initial_value}")
        print(f"   - Increments happened: {total_expected}")
        print(f"   - Final result: {final_value}")
        print(f"   - Expected final: {expected_final}")
        print(f"   - Success rate: {len([r for r in results if r['success']])}/{len(results)}")
        print(f"   - Total time: {end_time - start_time:.2f}s")
        
        # Emit batch header first
        socketio.emit('mass_crdt_batch_header', {
            'key': key,
            'num_operations': len(results),
            'timestamp': time.time()
        })
        
        # Emit individual operations for timeline logging
        print(f"🔄 Emitting individual operation logs for timeline...")
        for i, result in enumerate(results):
            if result.get('success') and result.get('response'):
                # Create operation data similar to single operations
                operation_data = {
                    'operation': result['operation'],
                    'success': True,
                    'node_used': result['node'],
                    'new_value': result['response'].get('new_value', 0),
                    'old_value': max(0, result['response'].get('new_value', 0) - result['operation']['amount']),
                    'response_time': 0.001,  # Very fast for concurrent
                    'isMassTest': True,
                    'concurrentBatch': time.time(),
                    'timestamp': time.time()
                }
                print(f"   - Emitting operation {i+1}: {result['operation']['type']} +{result['operation']['amount']} on {result['node']}")
                socketio.emit('crdt_operation', operation_data)
            else:
                # Emit failed operation
                operation_data = {
                    'operation': result['operation'],
                    'success': False,
                    'node_used': result['node'],
                    'error': result.get('error', 'Unknown error'),
                    'isMassTest': True,
                    'concurrentBatch': time.time(),
                    'timestamp': time.time()
                }
                print(f"   - Emitting FAILED operation {i+1}: {result['operation']['type']} on {result['node']}")
                socketio.emit('crdt_operation', operation_data)
        
        # Check if CRDT worked correctly (no lost increments)
        success = (actual_increment == total_expected)
        
        # Emit batch completion results
        socketio.emit('mass_crdt_test_complete', {
            'key': key,
            'num_operations': num_operations,
            'increments_happened': total_expected,
            'actual_increment': actual_increment,
            'initial_value': initial_value,
            'final_result': final_value,
            'expected_final': expected_final,
            'success': success,
            'operations': results,
            'node_breakdown': node_breakdown,
            'execution_time': end_time - start_time,
            'timestamp': time.time()
        })
        
        if success:
            print(f"🎉 CRDT SUCCESS: No lost increments! CRDT counters work perfectly under concurrency.")
        else:
            print(f"⚠️  CRDT Issue: Expected {total_expected} but got {actual_increment}")
    
    # Start test in background
    thread = threading.Thread(target=run_mass_test, daemon=True)
    thread.start()
    
    return jsonify({
        "success": True,
        "message": f"Started mass CRDT test with {num_operations} concurrent operations",
        "key": key
    })

@app.route('/api/simple_crdt_test', methods=['POST'])
def simple_crdt_test():
    """Run a simple sequential CRDT test"""
    data = request.json
    num_operations = min(data.get("num_operations", 3), 5)  # Max 5 operations
    key = data.get("key", "website_hits_crdt_demo")
    
    def run_simple_test():
        """Run a simple sequential CRDT test"""
        print(f"🔥 Starting simple CRDT test with {num_operations} operations")
        
        # Use fixed operations
        operations = [
            {"type": "page_view", "amount": 1, "description": "Page View"},
            {"type": "api_call", "amount": 2, "description": "API Call Batch"},
            {"type": "user_action", "amount": 1, "description": "User Action"},
            {"type": "api_call", "amount": 3, "description": "API Call Burst"},
            {"type": "page_view", "amount": 1, "description": "Another Page View"}
        ]
        
        nodes = get_cluster_nodes()
        
        for i in range(num_operations):
            op = operations[i % len(operations)]
            node = random.choice(nodes)  # Use different nodes
            
            try:
                response = requests.post(
                    f"http://{node}/counter/incr/{key}",
                    json={"amount": op["amount"]},
                    timeout=10
                )
                print(f"✅ Operation {i+1}: {op['type']} (+{op['amount']}) on {node} - {response.status_code}")
                
                # Synchronize after each operation and emit real-time update
                if response.status_code == 200:
                    result = response.json()
                    
                    # Sync across all nodes to show consistent state
                    all_contributions = sync_crdt_counter_across_all_nodes(key)
                    total_value = sum(all_contributions.values()) if all_contributions else result.get('new_value', 0)
                    
                    socketio.emit('simple_crdt_test_operation', {
                        'operation': op,
                        'success': True,
                        'node_used': node,
                        'new_value': total_value,
                        'counter_state': {'value': total_value, 'nodes': all_contributions},
                        'isSimpleTest': True,
                        'timestamp': time.time()
                    })
                    
            except Exception as e:
                print(f"❌ Operation {i+1} failed: {e}")
                # Emit failure
                socketio.emit('simple_crdt_test_operation', {
                    'operation': op,
                    'success': False,
                    'node_used': node,
                    'error': str(e),
                    'isSimpleTest': True,
                    'timestamp': time.time()
                })
            
            # Delay between operations
            time.sleep(0.5)
        
        print(f"🎯 Simple CRDT test completed")
    
    # Start test in background
    thread = threading.Thread(target=run_simple_test, daemon=True)
    thread.start()
    
    return jsonify({
        "success": True,
        "message": f"Started simple CRDT test with {num_operations} operations",
        "key": key
    })

@app.route('/api/operations_log')
def get_operations_log():
    """Get recent CRDT operations log"""
    return jsonify({
        "operations": CONCURRENT_OPERATIONS[-20:],  # Last 20 operations
        "total_operations": len(CONCURRENT_OPERATIONS)
    })

@app.route('/api/counter_consistency/<key>')
def check_counter_consistency(key):
    """Check CRDT counter consistency across all nodes"""
    nodes = get_cluster_nodes()
    node_data = {}
    
    def get_counter_from_node(node, node_id):
        try:
            response = requests.get(f"http://{node}/counter/{key}", timeout=10)
            if response.status_code == 200:
                counter_data = response.json()
                return {
                    "node": node,
                    "status": "healthy",
                    "value": counter_data.get("value", 0),
                    "node_contributions": counter_data.get("nodes", {}),
                    "timestamp": time.time()
                }
            elif response.status_code == 404:
                return {
                    "node": node,
                    "status": "healthy",
                    "value": 0,
                    "node_contributions": {},
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
        futures = {executor.submit(get_counter_from_node, node, f"node-{i+1}"): f"node-{i+1}" 
                  for i, node in enumerate(nodes)}
        
        for future in concurrent.futures.as_completed(futures):
            node_id = futures[future]
            node_data[node_id] = future.result()
    
    # Analyze CRDT consistency
    healthy_nodes = [data for data in node_data.values() if data["status"] == "healthy"]
    values = [node["value"] for node in healthy_nodes]
    
    # CRDT counters should be consistent (same value) or eventually consistent
    is_consistent = len(set(values)) <= 1
    max_value = max(values) if values else 0
    min_value = min(values) if values else 0
    
    consistency_analysis = {
        "is_consistent": is_consistent,
        "healthy_nodes": len(healthy_nodes),
        "total_nodes": len(nodes),
        "values": values,
        "max_value": max_value,
        "min_value": min_value,
        "consistency_level": "STRONG" if is_consistent else "CONVERGING",
        "crdt_guarantee": "CRDT counters guarantee eventual consistency and conflict-free merging"
    }
    
    return jsonify({
        "key": key,
        "nodes": node_data,
        "consistency": consistency_analysis,
        "timestamp": time.time()
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to CRDT Counter demo'})

@socketio.on('subscribe_key')
def handle_subscribe_key(data):
    """Handle subscription to a specific key for real-time updates"""
    key = data.get('key')
    emit('subscribed', {
        'key': key,
        'message': f'Subscribed to CRDT counter updates for {key}'
    })

if __name__ == '__main__':
    print("🚀 Starting CRDT Counter Demo...")
    print("📍 Demo URL: http://localhost:8006")
    print("🎯 Features:")
    print("   - CRDT (Conflict-free Replicated Data Type) counters")
    print("   - Guaranteed conflict-free concurrent operations")
    print("   - No race conditions or lost increments")
    print("   - Demonstrates solution to concurrent write problems")
    print("   - Real-time visualization of CRDT operations")
    print("")
    print("🔧 CRDT Configuration:")
    print("   - G-Counter implementation (increment-only)")
    print("   - Per-node contribution tracking")
    print("   - Automatic conflict resolution")
    print("   - Eventually consistent across all nodes")
    print("")
    print("💡 Use Case: Solves the race condition problem shown in quorum-based demo")
    print("              CRDT counters guarantee ALL increments are preserved")
    print("")
    print("Press Ctrl+C to stop the demo")
    print("=" * 60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8006, allow_unsafe_werkzeug=True)