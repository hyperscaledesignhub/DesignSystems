#!/usr/bin/env python3
"""
Node Failure Demo for Distributed Database
Demonstrates cluster resilience, node failure handling, and automatic recovery
Shows how the system handles node failures and synchronization
"""
import os
import sys
import json
import time
import threading
import requests
import random
import subprocess
import signal
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import concurrent.futures

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from demo.demo_utils import DemoLogger, check_cluster_status

app = Flask(__name__)
app.config['SECRET_KEY'] = 'node-failure-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
OPERATIONS_LOG = []
NODE_PROCESSES = {}  # Track node processes for start/stop
SIMULATED_FAILURES = {}  # Track simulated failures
CONTINUOUS_TRAFFIC = False

# Predefined data scenarios for testing
TEST_SCENARIOS = [
    {"key": "user_sessions", "value": 1250, "description": "Active user sessions"},
    {"key": "order_count", "value": 847, "description": "Daily order count"},
    {"key": "page_views", "value": 15670, "description": "Website page views"},
    {"key": "api_requests", "value": 9834, "description": "API request count"},
    {"key": "downloads", "value": 2156, "description": "File downloads"},
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

def get_node_id_from_address(address):
    """Convert node address to actual node ID"""
    if address == "localhost:9999":
        return "db-node-1"
    elif address == "localhost:10000":
        return "db-node-2"
    elif address == "localhost:10001":
        return "db-node-3"
    else:
        return f"db-node-{address.split(':')[1]}"

def increment_ui_counter():
    """Increment CRDT counter on all healthy nodes for UI display tracking"""
    nodes = get_cluster_nodes()
    healthy_nodes = []
    
    # Find healthy nodes
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                response = requests.get(f"http://{node}/health", timeout=1)
                if response.status_code == 200:
                    healthy_nodes.append(node)
            except:
                continue
    
    # Increment counter on all healthy nodes
    for node in healthy_nodes:
        try:
            requests.post(
                f"http://{node}/counter/incr/ui_write_count", 
                json={"amount": 1},
                timeout=2
            )
        except Exception as e:
            # Silently continue - counter increment is for UI only
            pass

def reset_ui_counters():
    """Reset CRDT counters on all nodes for fresh start"""
    nodes = get_cluster_nodes()
    
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                # Reset by setting to 0 (no direct reset endpoint)
                requests.post(
                    f"http://{node}/counter/merge/ui_write_count", 
                    json={"nodes": {get_node_id_from_address(node): 0}},
                    timeout=2
                )
            except Exception as e:
                # Silently continue - counter reset is for UI only
                pass

def sync_crdt_counter_to_db(node_address, actual_count):
    """Sync CRDT counter to match actual database count"""
    try:
        # Set counter using merge (no direct set endpoint)
        node_id = get_node_id_from_address(node_address)
        requests.post(
            f"http://{node_address}/counter/merge/ui_write_count", 
            json={"nodes": {node_id: actual_count}},
            timeout=2
        )
    except Exception as e:
        # Silently continue - counter sync is for UI only
        pass

def sync_ui_counter_to_restored_node(restored_address):
    """Sync CRDT counter to match the current cluster state"""
    try:
        nodes = get_cluster_nodes()
        max_counter_value = 0
        
        # Find the highest counter value from healthy nodes
        for node in nodes:
            node_id = get_node_id_from_address(node)
            if node_id not in SIMULATED_FAILURES and node != restored_address:
                try:
                    counter_response = requests.get(f"http://{node}/counter/ui_write_count", timeout=3)
                    if counter_response.status_code == 200:
                        counter_data = counter_response.json()
                        current_value = counter_data.get("value", 0)
                        max_counter_value = max(max_counter_value, current_value)
                except:
                    continue
        
        # Set the restored node's counter to match the cluster maximum
        if max_counter_value > 0:
            restored_node_id = get_node_id_from_address(restored_address)
            try:
                # Set the restored node's contribution to match the cluster
                requests.post(
                    f"http://{restored_address}/counter/merge/ui_write_count", 
                    json={"nodes": {restored_node_id: max_counter_value}},
                    timeout=3
                )
                print(f"✅ Synced {restored_node_id} CRDT counter to match cluster: {max_counter_value}")
            except Exception as e:
                print(f"⚠️ Failed to sync CRDT counter: {e}")
        else:
            print(f"⚠️ No counter values found to sync for restored node")
            
    except Exception as e:
        print(f"⚠️ Failed to sync CRDT counter for restored node: {e}")

def recover_all_crdt_counters():
    """Recover all CRDT counters by syncing to actual DB values"""
    nodes = get_cluster_nodes()
    print("🔧 Recovering all CRDT counters from database...")
    
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                # Get actual DB count (try multiple endpoints)
                stats_response = None
                actual_db_count = 0
                
                for stats_path in ["/stats", "/admin/stats"]:
                    try:
                        stats_response = requests.get(f"http://{node}{stats_path}", timeout=3)
                        if stats_response.status_code == 200:
                            stats_data = stats_response.json()
                            actual_db_count = stats_data.get("total_keys", 0)
                            break
                    except:
                        continue
                
                if stats_response and stats_response.status_code == 200:
                    
                    # Sync CRDT counter to DB reality
                    sync_crdt_counter_to_db(node, actual_db_count)
                    print(f"✅ {node_id} CRDT counter synced to DB: {actual_db_count}")
            except Exception as e:
                print(f"⚠️ Failed to recover CRDT counter for {node_id}: {e}")

def get_address_from_node_id(node_id):
    """Convert node ID to address"""
    if node_id == "db-node-1":
        return "localhost:9999"
    elif node_id == "db-node-2":
        return "localhost:10000"
    elif node_id == "db-node-3":
        return "localhost:10001"
    else:
        return None

@app.route('/')
def node_failure_demo():
    """Node failure demo UI"""
    # Don't auto-initialize data - let user do it manually via "Generate Data" button
    
    return render_template('node_failure_demo.html', 
                         cluster_nodes=get_cluster_nodes(),
                         test_scenarios=TEST_SCENARIOS)

def initialize_test_data():
    """Initialize test data across the cluster"""
    nodes = get_cluster_nodes()
    
    print("🔄 Initializing test data...")
    
    # Check if any nodes are healthy
    healthy_nodes = []
    for node in nodes:
        try:
            response = requests.get(f"http://{node}/health", timeout=2)
            if response.status_code == 200:
                healthy_nodes.append(node)
        except:
            continue
    
    if len(healthy_nodes) == 0:
        print("⚠️ No healthy nodes found - skipping test data initialization")
        return
        
    print(f"✅ Found {len(healthy_nodes)} healthy nodes")
    
    # Initialize each test scenario
    initialized_count = 0
    for scenario in TEST_SCENARIOS:
        key = scenario["key"]
        value = scenario["value"]
        
        try:
            # Write using a single node (it will replicate automatically)
            coordinator = healthy_nodes[0]
            response = requests.put(
                f"http://{coordinator}/kv/{key}",
                json={"value": value},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                initialized_count += 1
                print(f"  ✅ {key} = {value}")
            else:
                print(f"  ❌ Failed to write {key}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Failed to write {key}: {e}")
            continue
            
    print(f"🎯 Initialized {initialized_count}/{len(TEST_SCENARIOS)} test scenarios")

@app.route('/api/generate_test_data', methods=['POST'])
def generate_test_data():
    """Generate test data for the demo"""
    nodes = get_cluster_nodes()
    
    print("📝 Generating test data...")
    
    # Find healthy nodes
    healthy_nodes = []
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                response = requests.get(f"http://{node}/health", timeout=3)
                if response.status_code == 200:
                    healthy_nodes.append(node)
            except:
                continue
    
    if len(healthy_nodes) == 0:
        print("❌ No healthy nodes available for data generation")
        return jsonify({"success": False, "error": "No healthy nodes available"})
    
    print(f"✅ Found {len(healthy_nodes)} healthy nodes")
    
    # Generate 5 test key-value pairs with backoff on failures
    generated_data = []
    consecutive_failures = 0
    
    for i in range(5):
        key = f"demo_data_{int(time.time())}_{i}"
        value = f"value_{random.randint(1000, 9999)}"
        
        # Add backoff if we've had failures
        if consecutive_failures > 0:
            backoff = min(5, (1.5 ** consecutive_failures) + random.uniform(0.5, 1.5))
            print(f"  ⏳ Backing off {backoff:.1f}s after failures...")
            time.sleep(backoff)
        
        try:
            # Write to first healthy node
            coordinator = healthy_nodes[0]
            response = requests.put(
                f"http://{coordinator}/kv/{key}",
                json={"value": value},
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                generated_data.append({"key": key, "value": value})
                print(f"  ✅ Generated: {key} = {value}")
                consecutive_failures = 0
                
                # Track this as a successful write for data count
                OPERATIONS_LOG.append({
                    "timestamp": time.time(),
                    "type": "write", 
                    "key": key,
                    "value": value,
                    "success": True,
                    "data_written": True,
                    "source": "data_generation"
                })
            else:
                print(f"  ❌ Failed to write {key}: HTTP {response.status_code}")
                consecutive_failures += 1
                
        except Exception as e:
            print(f"  ❌ Failed to write {key}: {e}")
            consecutive_failures += 1
            continue
        
        # Small delay between writes to be gentle on cluster
        if i < 4:  # Don't delay after last write
            time.sleep(random.uniform(0.2, 0.5))
    
    print(f"🎯 Generated {len(generated_data)}/5 test data items")
    
    # Increment CRDT counters for successful data generation
    if len(generated_data) > 0:
        for _ in range(len(generated_data)):
            increment_ui_counter()
    
    return jsonify({
        "success": True,
        "generated_count": len(generated_data),
        "data": generated_data,
        "message": f"Generated {len(generated_data)} test data items"
    })

@app.route('/api/clear_stale_errors', methods=['POST'])
def clear_stale_errors():
    """Clear stale error responses and reinitialize data"""
    nodes = get_cluster_nodes()
    cleared_count = 0
    
    print("🧹 Clearing stale error responses and reinitializing data...")
    
    # Step 1: Trigger anti-entropy on all nodes first
    print("⚡ Triggering anti-entropy...")
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                # Try to trigger anti-entropy on each node
                response = requests.post(
                    f"http://{node}/admin/trigger_anti_entropy",
                    timeout=3
                )
                if response.status_code == 200:
                    cleared_count += 1
                    print(f"✅ Triggered anti-entropy on {node_id}")
            except Exception as e:
                print(f"⚠️ Failed to trigger anti-entropy on {node_id}: {e}")
                continue
    
    # Step 2: Wait a bit for anti-entropy to work
    time.sleep(2)
    
    # Step 3: Reinitialize test data to overwrite stale errors
    print("🔄 Reinitializing test data to fix stale errors...")
    healthy_nodes = []
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                response = requests.get(f"http://{node}/health", timeout=2)
                if response.status_code == 200:
                    healthy_nodes.append(node)
            except:
                continue
    
    reinit_count = 0
    if healthy_nodes:
        coordinator = healthy_nodes[0]
        print(f"🎯 Using {get_node_id_from_address(coordinator)} as coordinator for reinitialization")
        
        for scenario in TEST_SCENARIOS:
            try:
                # Force write each test scenario to overwrite stale errors
                response = requests.put(
                    f"http://{coordinator}/kv/{scenario['key']}",
                    json={"value": scenario["value"], "force_overwrite": True},
                    timeout=5
                )
                if response.status_code in [200, 201]:
                    reinit_count += 1
                    print(f"  ✅ Reinitialized: {scenario['key']} = {scenario['value']}")
                    time.sleep(0.2)  # Small delay between writes
            except Exception as e:
                print(f"  ❌ Failed to reinitialize {scenario['key']}: {e}")
    
    # Step 4: Recover all CRDT counters from actual DB data
    print("🔧 Recovering CRDT counters from database...")
    recover_all_crdt_counters()
    
    return jsonify({
        "success": True,
        "cleared_nodes": cleared_count,
        "reinitialized_keys": reinit_count,
        "total_nodes": len(nodes),
        "message": f"Cleared errors on {cleared_count} nodes, reinitialized {reinit_count} keys, synced CRDT counters"
    })

@app.route('/api/debug_processes')
def debug_processes():
    """Debug endpoint to check running processes"""
    nodes = get_cluster_nodes()
    debug_info = {}
    
    for node in nodes:
        node_id = get_node_id_from_address(node)
        port = node.split(":")[1]
        
        # Check processes on this port
        find_process = subprocess.run(
            f"lsof -ti :{port}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        pids = find_process.stdout.strip().split('\n') if find_process.stdout.strip() else []
        
        process_details = []
        for pid in pids:
            if pid.strip():
                check_process = subprocess.run(
                    f"ps -p {pid} -o pid,command",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                process_details.append({
                    "pid": pid,
                    "command": check_process.stdout.strip(),
                    "is_node": "distributed/node.py" in check_process.stdout
                })
        
        debug_info[node_id] = {
            "port": port,
            "pids": pids,
            "process_details": process_details,
            "failed": node_id in SIMULATED_FAILURES
        }
    
    return jsonify(debug_info)

@app.route('/api/cluster_status')
def get_detailed_cluster_status():
    """Get detailed cluster status with lag detection"""
    nodes = get_cluster_nodes()
    cluster_status = {}
    
    def check_node_status(node, node_id):
        try:
            # Check if node is actually failed (process killed)
            if node_id in SIMULATED_FAILURES:
                return {
                    "address": node,
                    "status": "failed",
                    "message": "Process killed",
                    "data_count": 0,
                    "last_seen": SIMULATED_FAILURES[node_id].get("failed_at", time.time()),
                    "is_simulated": False  # It's actually killed now
                }
            
            response = requests.get(f"http://{node}/health", timeout=2)
            if response.status_code == 200:
                health_data = response.json()
                
                # Get actual data count - trust DB over cache
                data_count = 0
                node_id = get_node_id_from_address(node)
                
                # Initialize display cache if not exists
                if not hasattr(check_node_status, 'display_cache'):
                    check_node_status.display_cache = {}
                
                try:
                    # Try to get data count - prefer CRDT but fallback gracefully
                    crdt_available = False
                    data_count = 0
                    
                    # Primary: Try CRDT counter endpoint (correct path)
                    try:
                        counter_response = requests.get(f"http://{node}/counter/ui_write_count", timeout=2)
                        if counter_response.status_code == 200:
                            counter_data = counter_response.json()
                            data_count = counter_data.get("value", 0)
                            crdt_available = True
                    except:
                        crdt_available = False
                    
                    # If CRDT unavailable, use cached value
                    if not crdt_available:
                        data_count = check_node_status.display_cache.get(node_id, 0)
                    
                    # Update display cache
                    check_node_status.display_cache[node_id] = data_count
                        
                except Exception as e:
                    # Total fallback - use cached display value
                    data_count = check_node_status.display_cache.get(node_id, 0)
                
                return {
                    "address": node,
                    "status": "healthy",
                    "data": health_data,
                    "data_count": data_count,
                    "last_seen": time.time(),
                    "is_simulated": False
                }
            else:
                return {
                    "address": node,
                    "status": "error",
                    "message": f"HTTP {response.status_code}",
                    "data_count": 0,
                    "last_seen": time.time(),
                    "is_simulated": False
                }
        except Exception as e:
            return {
                "address": node,
                "status": "offline",
                "message": str(e),
                "data_count": 0,
                "last_seen": time.time(),
                "is_simulated": False
            }
    
    # Check nodes sequentially to reduce cluster load
    for node in nodes:
        node_id = get_node_id_from_address(node)
        cluster_status[node_id] = check_node_status(node, node_id)
    
    # Skip lag detection for CRDT counter-based display
    # CRDT counters may have temporary differences during sync, which is normal
    # We rely on CRDT eventual consistency instead of forcing "syncing" status
    
    return jsonify({
        "cluster_size": len(nodes),
        "nodes": cluster_status,
        "timestamp": time.time(),
        "fault_tolerance": {
            "healthy_nodes": len([s for s in cluster_status.values() if s["status"] == "healthy"]),
            "failed_nodes": len([s for s in cluster_status.values() if s["status"] in ["failed", "offline"]]),
            "syncing_nodes": len([s for s in cluster_status.values() if s["status"] == "syncing"]),
            "quorum_available": len([s for s in cluster_status.values() if s["status"] in ["healthy", "syncing"]]) >= 2
        }
    })

@app.route('/api/simulate_node_failure', methods=['POST'])
def simulate_node_failure():
    """Actually kill a node process to simulate failure"""
    data = request.json
    node_id = data.get("node_id")
    
    if not node_id:
        return jsonify({"success": False, "error": "Missing node_id"}), 400
    
    # Get the node address and port
    address = get_address_from_node_id(node_id)
    if not address:
        return jsonify({"success": False, "error": "Invalid node_id"}), 400
    
    port = address.split(":")[1]
    
    try:
        # Actually kill the node process - more precise approach
        print(f"🔴 Attempting to kill {node_id} process on port {port}")
        
        # First, find the specific process ID for this port
        find_process = subprocess.run(
            f"lsof -ti :{port}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if find_process.returncode != 0 or not find_process.stdout.strip():
            print(f"⚠️ No process found on port {port} for {node_id}")
            return jsonify({
                "success": False, 
                "error": f"No process found on port {port}"
            }), 400
        
        pids = find_process.stdout.strip().split('\n')
        print(f"🔍 Found PIDs on port {port}: {pids}")
        
        # Kill each PID individually and verify it's a node process
        killed_pids = []
        for pid in pids:
            if pid.strip():
                # Check if this PID is actually a node process
                check_process = subprocess.run(
                    f"ps -p {pid} -o command=",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if "distributed/node.py" in check_process.stdout:
                    # Since we can't easily see env vars, we'll be more careful about which port we kill
                    # Only kill if this is the ONLY node process on this specific port
                    kill_result = subprocess.run(
                        f"kill -9 {pid}",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    
                    if kill_result.returncode == 0:
                        killed_pids.append(pid)
                        print(f"✅ Killed {node_id} process PID {pid} on port {port}")
                    else:
                        print(f"❌ Failed to kill PID {pid}")
                else:
                    print(f"⚠️ PID {pid} is not a node process, skipping")
        
        if not killed_pids:
            return jsonify({
                "success": False, 
                "error": f"No node processes found to kill on port {port}"
            }), 400
        
        # Mark node as failed
        SIMULATED_FAILURES[node_id] = {
            "failed_at": time.time(),
            "reason": "Process killed for demo",
            "port": port,
            "killed_pids": killed_pids
        }
        
        print(f"✅ Successfully killed {node_id} process(es): {killed_pids}")
        
        # Emit real-time update
        socketio.emit('node_status_change', {
            'node_id': node_id,
            'status': 'failed',
            'message': 'Node process killed',
            'timestamp': time.time()
        })
        
        return jsonify({
            "success": True,
            "message": f"Killed {node_id} process (PIDs: {killed_pids})",
            "failed_at": time.time()
        })
        
    except Exception as e:
        print(f"❌ Failed to kill {node_id}: {e}")
        return jsonify({
            "success": False, 
            "error": f"Failed to kill node: {str(e)}"
        }), 500

@app.route('/api/restore_node', methods=['POST'])
def restore_node():
    """Actually restart the failed node process"""
    data = request.json
    node_id = data.get("node_id")
    
    if not node_id:
        return jsonify({"success": False, "error": "Missing node_id"}), 400
    
    if node_id not in SIMULATED_FAILURES:
        return jsonify({"success": False, "error": "Node is not failed"}), 400
    
    # Determine the correct SEED_NODE_ID based on node
    seed_node_map = {
        "db-node-1": "db-node-1",
        "db-node-2": "db-node-2", 
        "db-node-3": "db-node-3"
    }
    
    seed_node_id = seed_node_map.get(node_id)
    if not seed_node_id:
        return jsonify({"success": False, "error": "Invalid node_id"}), 400
    
    try:
        print(f"🟢 Restarting {node_id} process...")
        
        # Start the node process
        process = subprocess.Popen(
            f"CONFIG_FILE=yaml/config-node-failure.yaml SEED_NODE_ID={seed_node_id} python distributed/node.py",
            shell=True,
            cwd="/Users/vijayabhaskarv/hyper-scale/kvdb/DesignSystems/NoSQL-DB"
        )
        
        # Store process reference
        NODE_PROCESSES[node_id] = {
            "process": process,
            "pid": process.pid,
            "started_at": time.time()
        }
        
        print(f"🟢 Started {node_id} with PID {process.pid}")
        
        # Wait a bit for node to start
        time.sleep(3)
        
        # Remove from failed nodes
        del SIMULATED_FAILURES[node_id]
        
        print(f"✅ Restarted {node_id} successfully")
        
        # Emit real-time update
        socketio.emit('node_status_change', {
            'node_id': node_id,
            'status': 'syncing',
            'message': 'Node process restarted - syncing data',
            'timestamp': time.time()
        })
        
        # Trigger data sync and error clearing after a short delay
        def trigger_sync_and_clear():
            time.sleep(5)  # Give node time to fully start
            
            # First clear stale errors from all nodes
            print(f"🧹 Clearing stale errors after {node_id} restart...")
            try:
                requests.post("http://localhost:8007/api/clear_stale_errors", timeout=10)
            except Exception as e:
                print(f"⚠️ Failed to clear stale errors: {e}")
            
            # Then sync data
            sync_node_data(node_id)
            
            # Finally sync CRDT counter
            address = get_address_from_node_id(node_id)
            if address:
                sync_ui_counter_to_restored_node(address)
        
        thread = threading.Thread(target=trigger_sync_and_clear, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "message": f"Restarted {node_id} process - syncing data",
            "restored_at": time.time()
        })
        
    except Exception as e:
        print(f"❌ Failed to restart {node_id}: {e}")
        return jsonify({
            "success": False, 
            "error": f"Failed to restart node: {str(e)}"
        }), 500

def sync_node_data(node_id):
    """Synchronize data for a restored node"""
    address = get_address_from_node_id(node_id)
    if not address:
        return
    
    nodes = get_cluster_nodes()
    healthy_nodes = []
    
    # Find healthy nodes to sync from
    for node in nodes:
        if node == address:
            continue  # Skip the node being restored
        try:
            if get_node_id_from_address(node) not in SIMULATED_FAILURES:
                response = requests.get(f"http://{node}/health", timeout=2)
                if response.status_code == 200:
                    healthy_nodes.append(node)
        except:
            continue
    
    if not healthy_nodes:
        print(f"❌ No healthy nodes available to sync {node_id}")
        return
    
    print(f"🔄 Syncing {node_id} from {len(healthy_nodes)} healthy nodes...")
    
    # Get known test data from healthy nodes for sync
    print(f"📊 Collecting test data from healthy nodes for sync...")
    
    # Use known test scenarios plus any generated test data
    all_test_keys = []
    
    # Add predefined test scenarios
    for scenario in TEST_SCENARIOS:
        all_test_keys.append(scenario["key"])
    
    # Add some recently generated test keys (find from operations log)
    for op in OPERATIONS_LOG[-10:]:  # Last 10 operations
        if op.get("type") == "write" and op.get("key"):
            if op["key"] not in [s["key"] for s in TEST_SCENARIOS]:
                all_test_keys.append(op["key"])
    
    print(f"🔍 Found {len(all_test_keys)} keys to sync: {all_test_keys}")
    
    try:
        # Sync each key to the restored node
        synced_count = 0
        source_node = healthy_nodes[0]
        
        for key in all_test_keys:
            try:
                # Get value from source node
                source_response = requests.get(f"http://{source_node}/kv/{key}", timeout=5)
                if source_response.status_code == 200:
                    source_data = source_response.json()
                    # Extract value from response
                    if isinstance(source_data, dict) and "value" in source_data:
                        value_to_sync = source_data["value"]
                    else:
                        value_to_sync = source_data
                    
                    # Sync to restored node
                    sync_response = requests.put(
                        f"http://{address}/kv/{key}",
                        json={"value": value_to_sync},
                        timeout=5
                    )
                    if sync_response.status_code in [200, 201]:
                        synced_count += 1
                        # Emit sync progress
                        socketio.emit('sync_progress', {
                            'node_id': node_id,
                            'synced_count': synced_count,
                            'total_count': len(all_test_keys),
                            'current_key': key,
                            'current_value': str(value_to_sync)[:50],  # Truncate long values
                            'timestamp': time.time()
                        })
                        
                        time.sleep(0.5)  # Longer delay to make progress visible
                    
            except Exception as e:
                print(f"Failed to sync {key} to {node_id}: {e}")
                continue
        
        print(f"✅ {node_id} sync completed: {synced_count}/{len(all_test_keys)} keys")
        
        # Mark sync as complete
        socketio.emit('sync_complete', {
            'node_id': node_id,
            'synced_count': synced_count,
            'total_count': len(all_test_keys),
            'timestamp': time.time()
        })
            
    except Exception as e:
        print(f"❌ Failed to sync {node_id}: {e}")
        socketio.emit('sync_failed', {
            'node_id': node_id,
            'error': str(e),
            'timestamp': time.time()
        })

@app.route('/api/test_writes_reads', methods=['POST'])
def test_writes_reads():
    """Test writes and reads during node failures"""
    data = request.json
    operation_type = data.get("type", "write")
    
    if operation_type == "write":
        return perform_test_write()
    else:
        return perform_test_read()

def perform_test_write():
    """Perform a test write operation with retry logic"""
    nodes = get_cluster_nodes()
    available_nodes = []
    
    # Find available nodes (not simulated as failed)
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                response = requests.get(f"http://{node}/health", timeout=2)
                if response.status_code == 200:
                    available_nodes.append(node)
            except:
                continue
    
    if len(available_nodes) < 2:
        # If cluster is degraded, wait before failing
        time.sleep(random.uniform(1, 3))
        return jsonify({
            "success": False,
            "error": "Insufficient nodes for quorum write",
            "available_nodes": len(available_nodes),
            "required": 2
        })
    
    # Perform write to multiple nodes for fault tolerance
    test_key = f"test_write_{int(time.time())}"
    test_value = random.randint(1000, 9999)
    
    write_results = []
    write_nodes = random.sample(available_nodes, min(2, len(available_nodes)))
    
    # Try writes with exponential backoff on failures
    retry_count = 0
    max_retries = 3
    
    for node in write_nodes:
        success = False
        node_id = get_node_id_from_address(node)
        
        for attempt in range(max_retries):
            try:
                # Add jitter to prevent thundering herd
                if attempt > 0:
                    backoff_time = min(5, (2 ** attempt) + random.uniform(0, 1))
                    print(f"⏳ Backing off {backoff_time:.1f}s before retry for {node_id}")
                    time.sleep(backoff_time)
                
                response = requests.put(
                    f"http://{node}/kv/{test_key}",
                    json={"value": test_value},
                    timeout=5
                )
                
                if response.status_code in [200, 201]:
                    success = True
                    write_results.append({
                        "node": node_id,
                        "success": True,
                        "status_code": response.status_code,
                        "attempts": attempt + 1
                    })
                    break
                else:
                    # Non-success response, might retry
                    if attempt == max_retries - 1:
                        write_results.append({
                            "node": node_id,
                            "success": False,
                            "status_code": response.status_code,
                            "attempts": attempt + 1
                        })
            except Exception as e:
                # Connection error, definitely retry
                if attempt == max_retries - 1:
                    write_results.append({
                        "node": node_id,
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1
                    })
        
        # Small delay between different nodes to reduce load
        if not success and len(write_nodes) > 1:
            time.sleep(random.uniform(0.5, 1.5))
    
    successful_writes = len([r for r in write_results if r["success"]])
    
    # Log operation
    operation_log = {
        "timestamp": time.time(),
        "type": "write",
        "key": test_key,
        "value": test_value,
        "nodes_attempted": len(write_nodes),
        "successful_writes": successful_writes,
        "results": write_results,
        "quorum_achieved": successful_writes >= 2,
        "success": successful_writes >= 1
    }
    
    # If write was successful, also track it for data count estimation
    if successful_writes >= 1:
        operation_log["data_written"] = True
        
        # Increment CRDT counter on all healthy nodes for stable UI display
        increment_ui_counter()
    
    OPERATIONS_LOG.append(operation_log)
    if len(OPERATIONS_LOG) > 50:
        OPERATIONS_LOG.pop(0)
    
    # Emit real-time update
    socketio.emit('operation_result', operation_log)
    
    return jsonify({
        "success": successful_writes >= 1,
        "operation": "write",
        "key": test_key,
        "value": test_value,
        "successful_writes": successful_writes,
        "total_attempts": len(write_nodes),
        "quorum_achieved": successful_writes >= 2,
        "results": write_results
    })

def perform_test_read():
    """Perform a test read operation"""
    nodes = get_cluster_nodes()
    available_nodes = []
    
    # Find available nodes
    for node in nodes:
        node_id = get_node_id_from_address(node)
        if node_id not in SIMULATED_FAILURES:
            try:
                response = requests.get(f"http://{node}/health", timeout=3)
                if response.status_code == 200:
                    available_nodes.append(node)
            except:
                continue
    
    if not available_nodes:
        return jsonify({
            "success": False,
            "error": "No nodes available for read",
            "available_nodes": 0
        })
    
    # Pick a random key to read
    test_key = random.choice(TEST_SCENARIOS)["key"]
    read_results = []
    
    # Try reading from available nodes
    for node in available_nodes:
        try:
            response = requests.get(f"http://{node}/kv/{test_key}", timeout=5)
            value = None
            if response.status_code == 200:
                response_data = response.json()
                # Handle both direct value and nested value structure
                if isinstance(response_data, dict) and "value" in response_data:
                    value = response_data["value"]
                else:
                    value = response_data
            
            read_results.append({
                "node": get_node_id_from_address(node),
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "value": value
            })
        except Exception as e:
            read_results.append({
                "node": get_node_id_from_address(node),
                "success": False,
                "error": str(e)
            })
    
    successful_reads = [r for r in read_results if r["success"]]
    
    # Log operation
    operation_log = {
        "timestamp": time.time(),
        "type": "read",
        "key": test_key,
        "nodes_attempted": len(available_nodes),
        "successful_reads": len(successful_reads),
        "results": read_results,
        "values": [r["value"] for r in successful_reads],
        "success": len(successful_reads) > 0  # Consider success if at least one read succeeded
    }
    
    OPERATIONS_LOG.append(operation_log)
    if len(OPERATIONS_LOG) > 50:
        OPERATIONS_LOG.pop(0)
    
    # Emit real-time update
    socketio.emit('operation_result', operation_log)
    
    return jsonify({
        "success": len(successful_reads) > 0,
        "operation": "read",
        "key": test_key,
        "successful_reads": len(successful_reads),
        "total_attempts": len(available_nodes),
        "results": read_results,
        "consistent": len(set(r["value"] for r in successful_reads)) <= 1
    })

@app.route('/api/start_continuous_traffic', methods=['POST'])
def start_continuous_traffic():
    """Start continuous read/write traffic"""
    global CONTINUOUS_TRAFFIC
    
    if CONTINUOUS_TRAFFIC:
        return jsonify({"success": False, "error": "Traffic already running"})
    
    CONTINUOUS_TRAFFIC = True
    
    def generate_traffic():
        print("🚀 Starting continuous traffic generation...")
        consecutive_failures = 0
        
        with app.app_context():
            while CONTINUOUS_TRAFFIC:
                try:
                    # Check cluster health before generating traffic
                    healthy_nodes = 0
                    for node in get_cluster_nodes():
                        node_id = get_node_id_from_address(node)
                        if node_id not in SIMULATED_FAILURES:
                            try:
                                resp = requests.get(f"http://{node}/health", timeout=1)
                                if resp.status_code == 200:
                                    healthy_nodes += 1
                            except:
                                pass
                    
                    # If cluster is degraded, back off more aggressively
                    if healthy_nodes < 2:
                        print(f"⚠️ Cluster degraded ({healthy_nodes} healthy nodes), backing off...")
                        time.sleep(random.uniform(5, 10))
                        continue
                    
                    # Alternate between reads and writes
                    if random.choice([True, False]):
                        result = perform_test_write()
                    else:
                        result = perform_test_read()
                    
                    # Check if operation succeeded
                    if result and hasattr(result, 'json'):
                        result_data = result.json
                        if isinstance(result_data, dict) and result_data.get('success'):
                            consecutive_failures = 0
                            # Normal delay for successful operations
                            time.sleep(random.uniform(2, 5))
                        else:
                            consecutive_failures += 1
                            # Exponential backoff for failures
                            backoff = min(30, (2 ** consecutive_failures) + random.uniform(1, 3))
                            print(f"⏳ Operation failed, backing off {backoff:.1f}s...")
                            time.sleep(backoff)
                    else:
                        # Default delay
                        time.sleep(random.uniform(3, 6))
                    
                except Exception as e:
                    print(f"Traffic generation error: {e}")
                    consecutive_failures += 1
                    # Error backoff
                    backoff = min(30, (2 ** consecutive_failures) + random.uniform(2, 5))
                    print(f"⏳ Error occurred, backing off {backoff:.1f}s...")
                    time.sleep(backoff)
        
        print("🛑 Continuous traffic stopped")
    
    thread = threading.Thread(target=generate_traffic, daemon=True)
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Continuous traffic started"
    })

@app.route('/api/stop_continuous_traffic', methods=['POST'])
def stop_continuous_traffic():
    """Stop continuous traffic"""
    global CONTINUOUS_TRAFFIC
    CONTINUOUS_TRAFFIC = False
    
    return jsonify({
        "success": True,
        "message": "Continuous traffic stopped"
    })

@app.route('/api/operations_log')
def get_operations_log():
    """Get recent operations log"""
    return jsonify({
        "operations": OPERATIONS_LOG[-20:],  # Last 20 operations
        "total_operations": len(OPERATIONS_LOG)
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to Node Failure demo'})

@socketio.on('subscribe_cluster')
def handle_subscribe_cluster():
    """Handle subscription to cluster updates"""
    emit('subscribed', {
        'message': 'Subscribed to cluster status updates'
    })

if __name__ == '__main__':
    import os
    import logging
    
    # Reduce Flask/socketio logging to minimum
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)
    
    print("🚀 Node Failure Demo started")
    print("📍 URL: http://localhost:8007")
    print("=" * 40)
    
    socketio.run(app, debug=False, host='0.0.0.0', port=8007, log_output=False, allow_unsafe_werkzeug=True)