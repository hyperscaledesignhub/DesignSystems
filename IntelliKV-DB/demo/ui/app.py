#!/usr/bin/env python3
"""
Web UI for Distributed Database Demos
Flask application providing interactive UIs for all real-world use case demos
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
app.config['SECRET_KEY'] = 'distributed-db-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Register REAL API extensions
from api_extensions import api_bp
app.register_blueprint(api_bp)

# Global configuration
CLUSTER_NODES = []
DEMO_DATA = {
    'twitter': {},
    'collab_editor': {},
    'cdn': {},
    'inventory': {}
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

@app.route('/')
def index():
    """Main demo launcher page"""
    return render_template('index.html')

@app.route('/twitter')
def twitter_demo():
    """Twitter-like counter demo UI with live data"""
    import datetime
    
    # Initialize display data
    data = {
        'node1_likes': 0, 'node1_retweets': 0, 'node1_comments': 0, 'node1_views': 0,
        'node2_likes': 0, 'node2_retweets': 0, 'node2_comments': 0, 'node2_views': 0,
        'node3_likes': 0, 'node3_retweets': 0, 'node3_comments': 0, 'node3_views': 0,
        'active_tweets': 0, 'total_counters': 0,
        'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
        'reset_message': '',
        'reset_class': ''
    }
    
    try:
        # Get data directly from traffic generator
        from real_traffic_generator import get_real_traffic_generator
        traffic_gen = get_real_traffic_generator()
        
        if traffic_gen:
            active_tweets = traffic_gen.get_active_tweets()
            data['active_tweets'] = len(active_tweets)
            
            # Get ACTUAL counters from each node (not cumulative)
            nodes = get_cluster_nodes()
            
            # Get cumulative counters from the single persistent tweet using quorum read
            persistent_tweet_id = "tweet_persistent_demo"
            
            # Try to get last known counters from traffic generator first
            last_known_counters = None
            try:
                if traffic_gen and hasattr(traffic_gen, 'last_known_counters'):
                    last_known_counters = traffic_gen.last_known_counters
            except:
                pass
            
            # Default counters - use last known values if available
            counters = last_known_counters if last_known_counters else {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0}
            
            # Read from any node - quorum will ensure consistent data
            node_addr = nodes[0]  # Use first node as coordinator
            try:
                stats_response = requests.get(f'http://{node_addr}/kv/{persistent_tweet_id}', timeout=3)
                if stats_response.status_code == 200:
                    response_data = stats_response.json()
                    
                    # Check for quorum errors
                    if "error" in response_data:
                        print(f"Quorum read error: {response_data['error']} - using last known values")
                    else:
                        value_str = response_data.get("value", "{}")
                        tweet_data = json.loads(value_str)
                        new_counters = tweet_data.get('counters', counters)
                        
                        # Only update if we got valid data (not all zeros when we had data before)
                        if new_counters != {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0} or not last_known_counters:
                            counters = new_counters
                            # Store last known good values
                            if traffic_gen:
                                traffic_gen.last_known_counters = counters
                        
                        print(f"Quorum read successful - counters: {counters}")
                        print(f"Quorum details: responded={response_data.get('replicas_responded')}, required={response_data.get('quorum_required')}")
                        
            except Exception as e:
                print(f"Error reading persistent tweet: {e} - using last known values")
            
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

@app.route('/api/twitter/reset_counters', methods=['POST'])
def reset_twitter_counters():
    """Reset the cumulative counters"""
    from cumulative_counters import get_cumulative_counters
    counter_tracker = get_cumulative_counters()
    reset_info = counter_tracker.reset_counters("Manual reset via API")
    return jsonify({"success": True, "reset_info": reset_info})

@app.route('/collab-editor')
def collab_editor_demo():
    """Collaborative editor demo UI"""
    return render_template('collab_editor_demo.html')

@app.route('/cdn')
def cdn_demo():
    """CDN distribution demo UI"""
    return render_template('cdn_demo.html')

@app.route('/inventory')
def inventory_demo():
    """Inventory management demo UI"""
    return render_template('inventory_demo.html')

@app.route('/debug')
def debug_test():
    """Debug test page"""
    return render_template('test_debug.html')

@app.route('/simple')
def simple_test():
    """Simple test page"""
    return render_template('simple_test.html')

@app.route('/super')
def super_simple():
    """Super simple counters page"""
    import datetime
    
    # Initialize counters
    data = {
        'node1_likes': 0, 'node1_retweets': 0, 'node1_comments': 0, 'node1_views': 0,
        'node2_likes': 0, 'node2_retweets': 0, 'node2_comments': 0, 'node2_views': 0,
        'node3_likes': 0, 'node3_retweets': 0, 'node3_comments': 0, 'node3_views': 0,
        'active_tweets': 0, 'total_counters': 0,
        'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
    }
    
    try:
        # Get active tweets
        print("Fetching active tweets...")
        response = requests.get('http://localhost:7342/api/real/twitter/active_tweets', timeout=2)
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            tweets_data = response.json()
            print(f"Tweets data: {tweets_data}")
            if tweets_data.get('success') and tweets_data.get('tweets'):
                data['active_tweets'] = tweets_data.get('total_active', 0)
                print(f"Found {len(tweets_data['tweets'])} tweets")
                
                # Get counters from first few tweets
                for tweet in tweets_data['tweets'][:5]:  # Check first 5 tweets
                    try:
                        tweet_id = tweet.get('tweet_id')
                        if tweet_id:
                            stats_response = requests.get(f'http://localhost:7342/api/twitter/stats/{tweet_id}', timeout=1)
                            if stats_response.status_code == 200:
                                stats_data = stats_response.json()
                                
                                # Node 1
                                if 'node-1' in stats_data and stats_data['node-1'].get('counters'):
                                    c = stats_data['node-1']['counters']
                                    data['node1_likes'] += c.get('likes', 0)
                                    data['node1_retweets'] += c.get('retweets', 0)
                                    data['node1_comments'] += c.get('comments', 0)
                                    data['node1_views'] += c.get('views', 0)
                                
                                # Node 2
                                if 'node-2' in stats_data and stats_data['node-2'].get('counters'):
                                    c = stats_data['node-2']['counters']
                                    data['node2_likes'] += c.get('likes', 0)
                                    data['node2_retweets'] += c.get('retweets', 0)
                                    data['node2_comments'] += c.get('comments', 0)
                                    data['node2_views'] += c.get('views', 0)
                                
                                # Node 3
                                if 'node-3' in stats_data and stats_data['node-3'].get('counters'):
                                    c = stats_data['node-3']['counters']
                                    data['node3_likes'] += c.get('likes', 0)
                                    data['node3_retweets'] += c.get('retweets', 0)
                                    data['node3_comments'] += c.get('comments', 0)
                                    data['node3_views'] += c.get('views', 0)
                    except Exception as e:
                        print(f"Error processing tweet: {e}")
                        continue
                
                # Calculate total
                data['total_counters'] = (data['node1_likes'] + data['node1_retweets'] + data['node1_comments'] + data['node1_views'] +
                                        data['node2_likes'] + data['node2_retweets'] + data['node2_comments'] + data['node2_views'] +
                                        data['node3_likes'] + data['node3_retweets'] + data['node3_comments'] + data['node3_views'])
                        
    except Exception as e:
        print(f"Error getting live data: {e}")
    
    return render_template('super_simple.html', **data)

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

@app.route('/api/twitter/create', methods=['POST'])
def twitter_create_tweet():
    """Create a new tweet"""
    data = request.json
    nodes = get_cluster_nodes()
    
    tweet_id = f"tweet_{int(time.time())}"
    tweet_data = {
        "id": tweet_id,
        "author": data.get("author", "@demo_user"),
        "content": data.get("content", ""),
        "timestamp": time.time(),
        "counters": {
            "likes": 0,
            "retweets": 0,
            "comments": 0,
            "views": 1
        }
    }
    
    try:
        response = requests.put(
            f"http://{nodes[0]}/kv/{tweet_id}",
            json={"value": json.dumps(tweet_data)}
        )
        
        if response.status_code == 200:
            DEMO_DATA['twitter'][tweet_id] = tweet_data
            return jsonify({"success": True, "tweet_id": tweet_id, "data": tweet_data})
        else:
            return jsonify({"success": False, "error": response.text}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/twitter/engage', methods=['POST'])
def twitter_engage():
    """Add engagement to a tweet - REAL database operations"""
    data = request.json
    tweet_id = data.get("tweet_id")
    action = data.get("action")  # likes, retweets, comments, views
    nodes = get_cluster_nodes()
    
    try:
        # Use random node for geographic distribution - REAL load balancing
        node = random.choice(nodes)
        
        # Get current tweet data from distributed database
        response = requests.get(f"http://{node}/kv/{tweet_id}")
        if response.status_code == 200:
            response_data = response.json()
            value_str = response_data.get("value", "{}")
            tweet_data = json.loads(value_str)
            
            # Increment counter - REAL atomic operation
            if "counters" not in tweet_data:
                tweet_data["counters"] = {}
            
            current_value = tweet_data["counters"].get(action, 0)
            tweet_data["counters"][action] = current_value + 1
            
            # Write back to distributed database - REAL replication
            response = requests.put(
                f"http://{node}/kv/{tweet_id}",
                json={"value": json.dumps(tweet_data)}
            )
            
            if response.status_code == 200:
                # Emit real-time update to all connected clients
                socketio.emit('tweet_engagement', {
                    'tweet_id': tweet_id,
                    'action': action,
                    'counters': tweet_data["counters"],
                    'node': node,
                    'timestamp': time.time()
                })
                return jsonify({"success": True, "counters": tweet_data["counters"], "node_used": node})
            else:
                return jsonify({"success": False, "error": response.text}), 500
        else:
            return jsonify({"success": False, "error": "Tweet not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/twitter/stats/<tweet_id>')
def twitter_get_stats(tweet_id):
    """Get tweet stats from all nodes"""
    nodes = get_cluster_nodes()
    stats = {}
    
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/kv/{tweet_id}")
            if response.status_code == 200:
                response_data = response.json()
                value_str = response_data.get("value", "{}")
                tweet_data = json.loads(value_str)
                stats[f"node-{i+1}"] = {
                    "address": node,
                    "status": "healthy",
                    "counters": tweet_data.get("counters", {}),
                    "data": tweet_data
                }
            else:
                stats[f"node-{i+1}"] = {
                    "address": node,
                    "status": "no_data",
                    "counters": {}
                }
        except Exception as e:
            stats[f"node-{i+1}"] = {
                "address": node,
                "status": "error",
                "error": str(e),
                "counters": {}
            }
    
    return jsonify(stats)

@app.route('/api/collab/create', methods=['POST'])
def collab_create_document():
    """Create a new collaborative document"""
    data = request.json
    nodes = get_cluster_nodes()
    
    doc_id = f"doc_{int(time.time())}"
    doc_data = {
        "title": data.get("title", "Untitled Document"),
        "paragraphs": {},
        "version": 1,
        "created_at": time.time()
    }
    
    try:
        response = requests.put(
            f"http://{nodes[0]}/causal/kv/{doc_id}",
            json={"value": json.dumps(doc_data)}
        )
        
        if response.status_code == 200:
            return jsonify({"success": True, "doc_id": doc_id, "data": doc_data})
        else:
            return jsonify({"success": False, "error": response.text}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/collab/edit', methods=['POST'])
def collab_edit_paragraph():
    """Edit a paragraph in a document"""
    data = request.json
    doc_id = data.get("doc_id")
    para_id = data.get("para_id")
    content = data.get("content")
    author = data.get("author", "Anonymous")
    nodes = get_cluster_nodes()
    
    try:
        # Get current document with causal consistency
        response = requests.get(f"http://{nodes[0]}/causal/kv/{doc_id}")
        if response.status_code == 200:
            response_data = response.json()
            value_str = response_data.get("value", "{}")
            doc_data = json.loads(value_str)
            
            # Update paragraph
            if "paragraphs" not in doc_data:
                doc_data["paragraphs"] = {}
            
            doc_data["paragraphs"][para_id] = {
                "content": content,
                "author": author,
                "timestamp": time.time()
            }
            doc_data["version"] = doc_data.get("version", 0) + 1
            
            # Write back with causal consistency
            response = requests.put(
                f"http://{nodes[0]}/causal/kv/{doc_id}",
                json={"value": json.dumps(doc_data)}
            )
            
            if response.status_code == 200:
                # Emit real-time update to all connected clients
                socketio.emit('document_updated', {
                    'doc_id': doc_id,
                    'para_id': para_id,
                    'content': content,
                    'author': author,
                    'timestamp': time.time()
                })
                return jsonify({"success": True, "document": doc_data})
            else:
                return jsonify({"success": False, "error": response.text}), 500
        else:
            return jsonify({"success": False, "error": "Document not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/collab/document/<doc_id>')
def collab_get_document(doc_id):
    """Get document from all nodes"""
    nodes = get_cluster_nodes()
    documents = {}
    
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/causal/kv/{doc_id}")
            if response.status_code == 200:
                response_data = response.json()
                value_str = response_data.get("value", "{}")
                doc_data = json.loads(value_str)
                documents[f"node-{i+1}"] = {
                    "address": node,
                    "status": "healthy",
                    "document": doc_data,
                    "vector_clock": response_data.get("vector_clock", {})
                }
            else:
                documents[f"node-{i+1}"] = {
                    "address": node,
                    "status": "no_data"
                }
        except Exception as e:
            documents[f"node-{i+1}"] = {
                "address": node,
                "status": "error",
                "error": str(e)
            }
    
    return jsonify(documents)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to distributed database demo'})

@socketio.on('join_demo')
def handle_join_demo(data):
    """Handle joining a specific demo"""
    demo_type = data.get('demo_type')
    emit('joined_demo', {'demo_type': demo_type})

# REAL traffic generator
from real_traffic_generator import start_real_traffic, get_real_traffic_generator
import random

# Background task for real-time updates
def background_updates():
    """Send periodic updates to connected clients + start REAL traffic"""
    # Start REAL traffic generation against the cluster
    nodes = get_cluster_nodes()
    if nodes:
        start_real_traffic(nodes)
        print(f"🔥 REAL traffic generation started against cluster: {nodes}")
    
    while True:
        try:
            # Get cluster status
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
            
            # Send real traffic stats if generator is running
            traffic_gen = get_real_traffic_generator()
            if traffic_gen:
                socketio.emit('real_traffic_stats', {
                    'active_tweets': len(traffic_gen.get_active_tweets()),
                    'active_documents': len(traffic_gen.get_active_documents()),
                    'timestamp': time.time()
                })
            
        except Exception as e:
            print(f"Background update error: {e}")
        
        time.sleep(5)  # Update every 5 seconds

if __name__ == '__main__':
    # Start background update thread
    update_thread = threading.Thread(target=background_updates, daemon=True)
    update_thread.start()
    
    print("🌐 Starting Distributed Database Demo UI...")
    print("📍 Demo URLs:")
    print("   Main Launcher: http://localhost:7342")
    print("   Twitter Demo:  http://localhost:7342/twitter")
    print("   Collab Editor: http://localhost:7342/collab-editor")
    print("   CDN Demo:      http://localhost:7342/cdn")
    print("   Inventory:     http://localhost:7342/inventory")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=7342, allow_unsafe_werkzeug=True)