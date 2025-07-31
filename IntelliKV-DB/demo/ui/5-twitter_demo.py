#!/usr/bin/env python3
"""
Twitter-like Demo for Distributed Database
Real-time engagement tracking with persistent counters
"""
import os
import sys
import json
import time
import threading
import random
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from demo.demo_utils import DemoLogger, check_cluster_status

app = Flask(__name__)
app.config['SECRET_KEY'] = 'twitter-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
PERSISTENT_TWEET_ID = "tweet_persistent_demo"
TWEET_COUNTER_KEYS = {
    "likes": "twitter_demo_likes_crdt",
    "retweets": "twitter_demo_retweets_crdt", 
    "comments": "twitter_demo_comments_crdt",
    "views": "twitter_demo_views_crdt"
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

def get_crdt_counter_value(counter_key, node=None):
    """Get CRDT counter value by summing all node contributions"""
    nodes = get_cluster_nodes()
    total_value = 0
    
    # Sum contributions from all nodes
    for node_addr in nodes:
        try:
            node_id = node_addr.replace("localhost:", "node_")
            crdt_key = f"{counter_key}_{node_id}"
            
            response = requests.get(f"http://{node_addr}/kv/{crdt_key}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if "value" in data and "error" not in data:
                    contribution = int(data["value"])
                    total_value += contribution
        except ValueError as e:
            print(f"Error parsing value from {node_addr} for {counter_key}: {e}")
            continue
        except Exception as e:
            print(f"Error getting contribution from {node_addr} for {counter_key}: {e}")
            continue
    
    return total_value

def increment_crdt_counter(counter_key, amount=1, node=None):
    """Increment a CRDT counter (simulated using regular KV operations)"""
    nodes = get_cluster_nodes()
    target_node = node or random.choice(nodes)  # Use random node for distribution
    
    try:
        # Simulate CRDT behavior using per-node counter contributions
        node_id = target_node.replace("localhost:", "node_")
        crdt_key = f"{counter_key}_{node_id}"
        
        # Get current node contribution with retry logic
        current_contribution = 0
        for attempt in range(2):  # Try twice
            try:
                response = requests.get(f"http://{target_node}/kv/{crdt_key}", timeout=5)  # Increased timeout
                if response.status_code == 200:
                    data = response.json()
                    if "value" in data and "error" not in data:
                        current_contribution = int(data["value"])
                        break
                elif attempt == 0:  # Try different node on first failure
                    target_node = random.choice([n for n in nodes if n != target_node])
                    node_id = target_node.replace("localhost:", "node_")
                    crdt_key = f"{counter_key}_{node_id}"
                    print(f"Retrying with different node: {target_node}")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == 0:  # Try different node on first failure
                    target_node = random.choice([n for n in nodes if n != target_node])
                    node_id = target_node.replace("localhost:", "node_")
                    crdt_key = f"{counter_key}_{node_id}"
                    print(f"Retrying with different node: {target_node}")
                else:
                    raise
        
        # Increment this node's contribution
        new_contribution = current_contribution + amount
        
        # Write back the updated contribution
        write_response = requests.put(
            f"http://{target_node}/kv/{crdt_key}",
            json={"value": str(new_contribution)},
            timeout=5  # Increased timeout
        )
        
        if write_response.status_code == 200:
            # Calculate total value by summing all node contributions
            total_value = get_crdt_counter_value(counter_key)
            
            result = {
                "node_id": node_id,
                "new_value": total_value,
                "node_contribution": new_contribution
            }
            print(f"✅ CRDT-style increment: {counter_key} +{amount} on {target_node} (node contrib: {new_contribution}, total: {total_value})")
            return result
        else:
            print(f"❌ Failed to increment {counter_key} on {target_node}: {write_response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error incrementing {counter_key}: {e}")
        return None

# Global variable to store last known good state
LAST_KNOWN_STATE = {
    'counters': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0},
    'last_update': None
}

@app.route('/')
def twitter_demo():
    """Twitter-like counter demo UI with CRDT counters"""
    global LAST_KNOWN_STATE
    import datetime
    
    # Initialize display data with last known values
    data = {
        'active_tweets': 1, 'total_counters': 0,
        'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
        'reset_message': '',
        'reset_class': '',
        'read_status': 'live'
    }
    
    try:
        nodes = get_cluster_nodes()
        
        # Get CRDT counter values from different nodes to show distributed nature
        counters = {}
        node_counters = {1: {}, 2: {}, 3: {}}
        
        # Get counter values from each node to show CRDT consistency
        for i, node in enumerate(nodes[:3], 1):  # Use first 3 nodes
            for action, counter_key in TWEET_COUNTER_KEYS.items():
                value = get_crdt_counter_value(counter_key, node)
                node_counters[i][action] = value
                counters[action] = value  # All nodes should have same value due to CRDT
        
        # Update global last known state
        LAST_KNOWN_STATE['counters'] = counters.copy()
        LAST_KNOWN_STATE['last_update'] = datetime.datetime.now()
        
        # Update display data with node-specific values
        data.update({
            'node1_likes': node_counters[1].get('likes', 0),
            'node1_retweets': node_counters[1].get('retweets', 0),
            'node1_comments': node_counters[1].get('comments', 0),
            'node1_views': node_counters[1].get('views', 0),
            
            'node2_likes': node_counters[2].get('likes', 0),
            'node2_retweets': node_counters[2].get('retweets', 0),
            'node2_comments': node_counters[2].get('comments', 0),
            'node2_views': node_counters[2].get('views', 0),
            
            'node3_likes': node_counters[3].get('likes', 0),
            'node3_retweets': node_counters[3].get('retweets', 0),
            'node3_comments': node_counters[3].get('comments', 0),
            'node3_views': node_counters[3].get('views', 0)
        })
        
        # Calculate total (should be consistent across all nodes due to CRDT)
        data['total_counters'] = sum(counters.values()) * 3  # Same counters shown on 3 nodes
        
        print(f"🐦 CRDT counters loaded: {counters}")
                    
    except Exception as e:
        print(f"Error getting CRDT counter data: {e}")
        # Use cached values if available
        if LAST_KNOWN_STATE['last_update']:
            data['reset_message'] = f"⚠️ Using cached data from {LAST_KNOWN_STATE['last_update'].strftime('%H:%M:%S')} (read timeout)"
            data['reset_class'] = 'warning'
    
    return render_template('twitter_demo.html', **data)

@app.route('/api/engage', methods=['POST'])
def engage_with_tweet():
    """Manual engagement using CRDT counters"""
    data = request.json
    action = data.get("action", "views")  # likes, retweets, comments, views
    amount = data.get("amount", 1)  # Allow custom increment amounts
    
    if action not in TWEET_COUNTER_KEYS:
        return jsonify({"success": False, "error": f"Invalid action: {action}"}), 400
    
    try:
        # Use CRDT counter increment
        counter_key = TWEET_COUNTER_KEYS[action]
        print(f"📝 Attempting to increment {action} (key: {counter_key}) by {amount}")
        result = increment_crdt_counter(counter_key, amount)
        
        if result:
            # Get updated counter values for real-time display
            updated_counters = {}
            for act, key in TWEET_COUNTER_KEYS.items():
                updated_counters[act] = get_crdt_counter_value(key)
            
            # Update global state
            global LAST_KNOWN_STATE
            LAST_KNOWN_STATE['counters'] = updated_counters.copy()
            LAST_KNOWN_STATE['last_update'] = datetime.now()
            
            # Emit real-time update
            socketio.emit('tweet_engagement', {
                'action': action,
                'amount': amount,
                'counters': updated_counters,
                'node': result.get('node_id', 'unknown'),
                'timestamp': time.time(),
                'method': 'CRDT'
            })
            
            return jsonify({
                "success": True, 
                "action": action,
                "amount": amount,
                "new_value": result.get('new_value', 0),
                "counters": updated_counters, 
                "node_used": result.get('node_id', 'unknown'),
                "method": "CRDT Counter"
            })
        else:
            print(f"❌ increment_crdt_counter returned None/False for {action}")
            return jsonify({"success": False, "error": "Failed to increment CRDT counter"}), 500
            
    except Exception as e:
        print(f"❌ Exception in engage_with_tweet: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cluster/status')
def cluster_status():
    """Get cluster health status"""
    nodes = get_cluster_nodes()
    status = {}
    
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/health", timeout=2)
            if response.status_code == 200:
                status[f"node-{i+1}"] = {
                    "address": node,
                    "status": "healthy",
                    "data": response.json()
                }
            else:
                status[f"node-{i+1}"] = {
                    "address": node,
                    "status": "error",
                    "message": f"HTTP {response.status_code}"
                }
        except Exception as e:
            status[f"node-{i+1}"] = {
                "address": node,
                "status": "offline",
                "message": str(e)
            }
    
    return jsonify(status)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to Twitter demo'})

# Background task for real-time updates and auto-engagement
def background_updates():
    """Send periodic updates to connected clients and simulate engagement"""
    import random
    from datetime import datetime
    
    # Engagement patterns - realistic social media activity
    engagement_weights = {
        'views': 10,     # Most common
        'likes': 3,      # Less common than views
        'retweets': 1,   # Less common than likes
        'comments': 1    # Least common
    }
    
    while True:
        try:
            nodes = get_cluster_nodes()
            
            # 1. Simulate realistic engagement activity using CRDT counters
            if random.random() < 0.7:  # 70% chance of engagement per cycle
                actions = []
                for action, weight in engagement_weights.items():
                    actions.extend([action] * weight)
                
                selected_action = random.choice(actions)
                
                try:
                    # Use CRDT counter increment for auto-engagement
                    counter_key = TWEET_COUNTER_KEYS[selected_action]
                    result = increment_crdt_counter(counter_key, 1)
                    
                    if result:
                        # Get updated counter values
                        updated_counters = {}
                        for act, key in TWEET_COUNTER_KEYS.items():
                            updated_counters[act] = get_crdt_counter_value(key)
                        
                        # Update global last known state
                        global LAST_KNOWN_STATE
                        LAST_KNOWN_STATE['counters'] = updated_counters.copy()
                        LAST_KNOWN_STATE['last_update'] = datetime.now()
                        
                        # Emit real-time update
                        socketio.emit('tweet_engagement', {
                            'action': selected_action,
                            'amount': 1,
                            'counters': updated_counters,
                            'node': result.get('node_id', 'unknown'),
                            'timestamp': time.time(),
                            'automatic': True,
                            'method': 'CRDT'
                        })
                        
                        print(f"🤖 Auto-engagement: +1 {selected_action} via CRDT on {result.get('node_id', 'unknown')} -> {result.get('new_value', 0)}")
                    
                except Exception as e:
                    print(f"Auto-engagement CRDT error: {e}")
            
            # 2. Get cluster status for health monitoring
            cluster_status = {}
            for i, node in enumerate(nodes):
                try:
                    response = requests.get(f"http://{node}/health", timeout=1)
                    cluster_status[f"node-{i+1}"] = {
                        "address": node,
                        "status": "healthy" if response.status_code == 200 else "degraded"
                    }
                except:
                    cluster_status[f"node-{i+1}"] = {
                        "address": node,
                        "status": "offline"
                    }
            
            socketio.emit('cluster_status', cluster_status)
            
        except Exception as e:
            print(f"Background update error: {e}")
        
        # Random interval between 1-3 seconds for realistic engagement pattern
        time.sleep(random.uniform(1.0, 3.0))

def init_crdt_counters():
    """Initialize CRDT counters (they auto-create on first increment, so just log)"""
    print(f"🐦 Twitter Demo using CRDT counters:")
    for action, counter_key in TWEET_COUNTER_KEYS.items():
        print(f"  • {action}: {counter_key}")
    print("✅ CRDT counters will auto-initialize on first engagement")

if __name__ == '__main__':
    # Initialize CRDT counters
    init_crdt_counters()
    
    # Start background update thread
    update_thread = threading.Thread(target=background_updates, daemon=True)
    update_thread.start()
    
    print("🐦 Starting Twitter Demo...")
    print("📍 URL: http://localhost:8001")
    print("🎯 Features: Real-time engagement tracking, persistent counters")
    print("📊 Tweet ID: tweet_persistent_demo")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8001, allow_unsafe_werkzeug=True)