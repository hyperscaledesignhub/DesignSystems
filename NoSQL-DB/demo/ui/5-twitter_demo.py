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

# Global variable to store last known good state
LAST_KNOWN_STATE = {
    'counters': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0},
    'last_update': None
}

@app.route('/')
def twitter_demo():
    """Twitter-like counter demo UI with live data"""
    global LAST_KNOWN_STATE
    import datetime
    
    # Initialize display data with last known values
    data = {
        'node1_likes': LAST_KNOWN_STATE['counters']['likes'], 
        'node1_retweets': LAST_KNOWN_STATE['counters']['retweets'], 
        'node1_comments': LAST_KNOWN_STATE['counters']['comments'], 
        'node1_views': LAST_KNOWN_STATE['counters']['views'],
        'node2_likes': LAST_KNOWN_STATE['counters']['likes'], 
        'node2_retweets': LAST_KNOWN_STATE['counters']['retweets'], 
        'node2_comments': LAST_KNOWN_STATE['counters']['comments'], 
        'node2_views': LAST_KNOWN_STATE['counters']['views'],
        'node3_likes': LAST_KNOWN_STATE['counters']['likes'], 
        'node3_retweets': LAST_KNOWN_STATE['counters']['retweets'], 
        'node3_comments': LAST_KNOWN_STATE['counters']['comments'], 
        'node3_views': LAST_KNOWN_STATE['counters']['views'],
        'active_tweets': 1, 'total_counters': 0,
        'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
        'reset_message': '',
        'reset_class': '',
        'read_status': 'cached' if LAST_KNOWN_STATE['last_update'] else 'initial'
    }
    
    try:
        nodes = get_cluster_nodes()
        
        # Get cumulative counters from the single persistent tweet using quorum read
        counters = LAST_KNOWN_STATE['counters'].copy()  # Start with last known values
        
        # Read from any node - quorum will ensure consistent data
        node_addr = nodes[0]  # Use first node as coordinator
        try:
            stats_response = requests.get(f'http://{node_addr}/kv/{PERSISTENT_TWEET_ID}', timeout=3)
            if stats_response.status_code == 200:
                response_data = stats_response.json()
                
                # Check for quorum errors
                if "error" in response_data:
                    print(f"Quorum read error: {response_data['error']} - using defaults")
                else:
                    value_str = response_data.get("value", "{}")
                    tweet_data = json.loads(value_str)
                    new_counters = tweet_data.get('counters', counters)
                    
                    # Only update if we got valid data
                    if new_counters != {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0}:
                        counters = new_counters
                        # Update global last known state
                        LAST_KNOWN_STATE['counters'] = counters.copy()
                        LAST_KNOWN_STATE['last_update'] = datetime.datetime.now()
                        data['read_status'] = 'live'
                    
                    print(f"Quorum read successful - counters: {counters}")
                    print(f"Quorum details: responded={response_data.get('replicas_responded')}, required={response_data.get('quorum_required')}")
                    
        except Exception as e:
            print(f"Error reading persistent tweet: {e} - using last known state")
            if LAST_KNOWN_STATE['last_update']:
                data['reset_message'] = f"⚠️ Using cached data from {LAST_KNOWN_STATE['last_update'].strftime('%H:%M:%S')} (read timeout)"
                data['reset_class'] = 'warning'
        
        # Display same counters across all nodes (since they should be consistent via quorum)
        node_counters = {
            1: counters.copy(),
            2: counters.copy(), 
            3: counters.copy()
        }
        
        # Update display data
        data['node1_likes'] = node_counters[1]['likes']
        data['node1_retweets'] = node_counters[1]['retweets']
        data['node1_comments'] = node_counters[1]['comments']
        data['node1_views'] = node_counters[1]['views']
        
        data['node2_likes'] = node_counters[2]['likes']
        data['node2_retweets'] = node_counters[2]['retweets']
        data['node2_comments'] = node_counters[2]['comments']
        data['node2_views'] = node_counters[2]['views']
        
        data['node3_likes'] = node_counters[3]['likes']
        data['node3_retweets'] = node_counters[3]['retweets']
        data['node3_comments'] = node_counters[3]['comments']
        data['node3_views'] = node_counters[3]['views']
        
        # Calculate total
        data['total_counters'] = (data['node1_likes'] + data['node1_retweets'] + data['node1_comments'] + data['node1_views'] +
                                data['node2_likes'] + data['node2_retweets'] + data['node2_comments'] + data['node2_views'] +
                                data['node3_likes'] + data['node3_retweets'] + data['node3_comments'] + data['node3_views'])
                    
    except Exception as e:
        print(f"Error getting live data for Twitter demo: {e}")
    
    return render_template('twitter_demo.html', **data)

@app.route('/api/engage', methods=['POST'])
def engage_with_tweet():
    """Manual engagement with the persistent tweet"""
    data = request.json
    action = data.get("action", "views")  # likes, retweets, comments, views
    nodes = get_cluster_nodes()
    
    try:
        # Use random node for geographic distribution
        import random
        node = random.choice(nodes)
        
        # Get current tweet data
        response = requests.get(f"http://{node}/kv/{PERSISTENT_TWEET_ID}", timeout=3)
        if response.status_code == 200:
            response_data = response.json()
            
            if "error" in response_data:
                return jsonify({"success": False, "error": response_data["error"]}), 500
            
            value_str = response_data.get("value", "{}")
            tweet_data = json.loads(value_str)
            
            # Increment counter
            if "counters" not in tweet_data:
                tweet_data["counters"] = {}
            
            current_value = tweet_data["counters"].get(action, 0)
            tweet_data["counters"][action] = current_value + 1
            
            # Write back to database
            write_response = requests.put(
                f"http://{node}/kv/{PERSISTENT_TWEET_ID}",
                json={"value": json.dumps(tweet_data)},
                timeout=3
            )
            
            if write_response.status_code == 200:
                write_data = write_response.json()
                
                if "error" in write_data:
                    return jsonify({"success": False, "error": write_data["error"]}), 500
                
                # Emit real-time update
                socketio.emit('tweet_engagement', {
                    'action': action,
                    'counters': tweet_data["counters"],
                    'node': node,
                    'timestamp': time.time()
                })
                
                return jsonify({"success": True, "counters": tweet_data["counters"], "node_used": node})
            else:
                return jsonify({"success": False, "error": f"Write failed: {write_response.text}"}), 500
        else:
            return jsonify({"success": False, "error": "Tweet not found"}), 404
            
    except Exception as e:
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
            
            # 1. Simulate realistic engagement activity
            if random.random() < 0.7:  # 70% chance of engagement per cycle
                actions = []
                for action, weight in engagement_weights.items():
                    actions.extend([action] * weight)
                
                selected_action = random.choice(actions)
                
                # Simulate engagement with random node (geographic distribution)
                node = random.choice(nodes)
                
                try:
                    # Get current tweet data
                    response = requests.get(f"http://{node}/kv/{PERSISTENT_TWEET_ID}", timeout=2)
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        if "error" not in response_data:
                            value_str = response_data.get("value", "{}")
                            tweet_data = json.loads(value_str)
                            
                            # Increment counter
                            if "counters" not in tweet_data:
                                tweet_data["counters"] = {}
                            
                            current_value = tweet_data["counters"].get(selected_action, 0)
                            tweet_data["counters"][selected_action] = current_value + 1
                            
                            # Write back to database
                            write_response = requests.put(
                                f"http://{node}/kv/{PERSISTENT_TWEET_ID}",
                                json={"value": json.dumps(tweet_data)},
                                timeout=2
                            )
                            
                            if write_response.status_code == 200:
                                write_data = write_response.json()
                                
                                if "error" not in write_data:
                                    # Update global last known state
                                    global LAST_KNOWN_STATE
                                    LAST_KNOWN_STATE['counters'] = tweet_data["counters"].copy()
                                    LAST_KNOWN_STATE['last_update'] = datetime.now()
                                    
                                    # Emit real-time update
                                    socketio.emit('tweet_engagement', {
                                        'action': selected_action,
                                        'counters': tweet_data["counters"],
                                        'node': node,
                                        'timestamp': time.time(),
                                        'automatic': True
                                    })
                                    
                                    print(f"🤖 Auto-engagement: +1 {selected_action} via {node} (total: {tweet_data['counters']})")
                                
                except Exception as e:
                    print(f"Auto-engagement error: {e}")
            
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

def init_persistent_tweet():
    """Initialize the persistent tweet if it doesn't exist"""
    nodes = get_cluster_nodes()
    
    try:
        # Check if tweet exists
        response = requests.get(f"http://{nodes[0]}/kv/{PERSISTENT_TWEET_ID}", timeout=3)
        if response.status_code == 200:
            data = response.json()
            if "value" in data and "error" not in data:
                print(f"✅ Persistent tweet {PERSISTENT_TWEET_ID} already exists")
                return True
    except:
        pass
    
    # Create tweet if it doesn't exist
    tweet_data = {
        "id": PERSISTENT_TWEET_ID,
        "author": "@twitter_demo", 
        "content": "🐦 Real-time Twitter engagement demo with distributed counters",
        "timestamp": int(time.time()),
        "counters": {"likes": 0, "retweets": 0, "comments": 0, "views": 0}
    }
    
    try:
        response = requests.put(
            f"http://{nodes[0]}/kv/{PERSISTENT_TWEET_ID}",
            json={"value": json.dumps(tweet_data)},
            timeout=5
        )
        if response.status_code == 200:
            print(f"✅ Created persistent tweet {PERSISTENT_TWEET_ID}")
            return True
        else:
            print(f"❌ Failed to create tweet: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating tweet: {e}")
        return False

if __name__ == '__main__':
    # Initialize persistent tweet
    init_persistent_tweet()
    
    # Start background update thread
    update_thread = threading.Thread(target=background_updates, daemon=True)
    update_thread.start()
    
    print("🐦 Starting Twitter Demo...")
    print("📍 URL: http://localhost:8001")
    print("🎯 Features: Real-time engagement tracking, persistent counters")
    print("📊 Tweet ID: tweet_persistent_demo")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8001, allow_unsafe_werkzeug=True)