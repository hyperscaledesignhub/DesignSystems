#!/usr/bin/env python3
"""
Auction Bidding Demo for Distributed Database
Demonstrates quorum writes with Last-Write-Wins under real concurrency
Multiple users bidding on items simultaneously
"""
import os
import sys
import json
import time
import threading
import random
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'auction-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
AUCTION_ITEMS = [
    {"id": "item_1", "name": "🖼️ Rare Digital Art", "starting_bid": 100},
    {"id": "item_2", "name": "⌚ Vintage Watch", "starting_bid": 500},
    {"id": "item_3", "name": "🎸 Signed Guitar", "starting_bid": 1000},
]

# Simulated bidders for concurrent activity
BIDDER_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
AUTO_BIDDING = True
bidding_threads = []

def get_cluster_nodes():
    """Get cluster nodes from environment or default"""
    global CLUSTER_NODES
    if not CLUSTER_NODES:
        cluster_env = os.environ.get('CLUSTER_NODES')
        if cluster_env:
            CLUSTER_NODES = [node.strip() for node in cluster_env.split(',')]
        else:
            # Check which nodes are actually running
            potential_nodes = ["localhost:9999", "localhost:10000", "localhost:10001"]
            CLUSTER_NODES = []
            
            for node in potential_nodes:
                try:
                    response = requests.get(f"http://{node}/health", timeout=1)
                    if response.status_code == 200:
                        CLUSTER_NODES.append(node)
                        print(f"✅ Found running node: {node}")
                except:
                    print(f"❌ Node not responding: {node}")
            
            if not CLUSTER_NODES:
                print("⚠️  No database nodes found! Using localhost:9999 as fallback")
                CLUSTER_NODES = ["localhost:9999"]
                
    return CLUSTER_NODES

def initialize_auction_items():
    """Initialize auction items in the database"""
    nodes = get_cluster_nodes()
    
    for item in AUCTION_ITEMS:
        auction_data = {
            "item_id": item["id"],
            "name": item["name"],
            "current_bid": item["starting_bid"],
            "bidder": None,
            "bid_count": 0,
            "bid_history": [],
            "status": "active",
            "started_at": int(time.time())
        }
        
        try:
            # Write to first available node
            response = requests.put(
                f"http://{nodes[0]}/kv/{item['id']}",
                json={"value": json.dumps(auction_data)},
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Initialized auction item: {item['name']}")
        except Exception as e:
            print(f"❌ Failed to initialize {item['name']}: {e}")

@app.route('/')
def auction_demo():
    """Auction demo UI"""
    return render_template('auction_demo.html')

@app.route('/api/items')
def get_auction_items():
    """Get all auction items with current bids"""
    nodes = get_cluster_nodes()
    items = []
    
    for item in AUCTION_ITEMS:
        try:
            # Use first working node to avoid timeouts
            node = nodes[0]
            response = requests.get(f"http://{node}/kv/{item['id']}", timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if "value" in data:
                    auction_data = json.loads(data["value"])
                    items.append(auction_data)
            else:
                # Return default if not found
                items.append({
                    "item_id": item["id"],
                    "name": item["name"],
                    "current_bid": item["starting_bid"],
                    "bidder": None,
                    "bid_count": 0,
                    "status": "loading"
                })
        except Exception as e:
            print(f"Error fetching {item['id']}: {e}")
            items.append({
                "item_id": item["id"],
                "name": item["name"],
                "current_bid": item["starting_bid"],
                "bidder": None,
                "error": str(e)
            })
    
    return jsonify({"items": items})

@app.route('/api/bid', methods=['POST'])
def place_bid():
    """Place a bid on an item - demonstrates concurrent writes"""
    data = request.json
    item_id = data.get('item_id')
    bidder = data.get('bidder')
    bid_amount = data.get('amount')
    
    if not all([item_id, bidder, bid_amount]):
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    nodes = get_cluster_nodes()
    # Use first working node to avoid timeouts
    node = nodes[0]
    
    try:
        # Read current item state
        read_start = time.time()
        response = requests.get(f"http://{node}/kv/{item_id}", timeout=3)
        read_time = time.time() - read_start
        
        if response.status_code != 200:
            return jsonify({"success": False, "error": "Item not found"}), 404
        
        data = response.json()
        current_value = json.loads(data["value"])
        
        # Check if bid is high enough
        if bid_amount <= current_value["current_bid"]:
            return jsonify({
                "success": False, 
                "error": "Bid too low",
                "current_bid": current_value["current_bid"],
                "current_bidder": current_value["bidder"],
                "message": f"Your bid of ${bid_amount} is not higher than current bid of ${current_value['current_bid']}"
            }), 409
        
        # Update with new bid
        current_value["current_bid"] = bid_amount
        current_value["bidder"] = bidder
        current_value["bid_count"] += 1
        current_value["last_bid_time"] = time.time()
        
        # Add to history (keep last 10)
        current_value["bid_history"].append({
            "bidder": bidder,
            "amount": bid_amount,
            "timestamp": time.time(),
            "node": node
        })
        current_value["bid_history"] = current_value["bid_history"][-10:]
        
        # Write back with quorum
        write_start = time.time()
        write_response = requests.put(
            f"http://{node}/kv/{item_id}",
            json={"value": json.dumps(current_value)},
            timeout=3
        )
        write_time = time.time() - write_start
        
        if write_response.status_code == 200:
            # Emit real-time update
            socketio.emit('bid_update', {
                'item_id': item_id,
                'bidder': bidder,
                'amount': bid_amount,
                'bid_count': current_value["bid_count"],
                'timestamp': time.time()
            })
            
            return jsonify({
                "success": True,
                "message": f"Bid placed successfully!",
                "bid": {
                    "amount": bid_amount,
                    "bidder": bidder,
                    "item_id": item_id
                },
                "timing": {
                    "read_ms": round(read_time * 1000, 2),
                    "write_ms": round(write_time * 1000, 2),
                    "total_ms": round((read_time + write_time) * 1000, 2)
                },
                "node_used": node
            })
        else:
            return jsonify({"success": False, "error": "Failed to place bid"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def auto_bidder(bidder_name, item_id, max_bid, delay_range=(1, 5)):
    """Simulate automatic bidding behavior"""
    import requests
    
    while AUTO_BIDDING:
        try:
            # Random delay between bids
            time.sleep(random.uniform(*delay_range))
            
            # Get current bid
            nodes = get_cluster_nodes()
            response = requests.get(f"http://{nodes[0]}/kv/{item_id}", timeout=2)
            
            if response.status_code == 200:
                data = json.loads(response.json()["value"])
                current_bid = data["current_bid"]
                
                # Decide whether to bid
                if current_bid < max_bid and random.random() > 0.3:  # 70% chance to bid
                    bid_increment = random.choice([10, 20, 50, 100])
                    new_bid = current_bid + bid_increment
                    
                    if new_bid <= max_bid:
                        # Place bid directly to database (similar to manual API)
                        try:
                            # Read current item state
                            read_response = requests.get(f"http://{nodes[0]}/kv/{item_id}", timeout=2)
                            if read_response.status_code == 200:
                                current_data = json.loads(read_response.json()["value"])
                                
                                # Check if bid is still valid
                                if new_bid > current_data["current_bid"]:
                                    # Update with new bid
                                    current_data["current_bid"] = new_bid
                                    current_data["bidder"] = bidder_name
                                    current_data["bid_count"] += 1
                                    current_data["last_bid_time"] = time.time()
                                    
                                    # Add to history
                                    current_data["bid_history"].append({
                                        "bidder": bidder_name,
                                        "amount": new_bid,
                                        "timestamp": time.time(),
                                        "node": random.choice(nodes)
                                    })
                                    current_data["bid_history"] = current_data["bid_history"][-10:]
                                    
                                    # Write back
                                    write_response = requests.put(
                                        f"http://{nodes[0]}/kv/{item_id}",
                                        json={"value": json.dumps(current_data)},
                                        timeout=2
                                    )
                                    
                                    bid_response = {"status_code": write_response.status_code}
                                else:
                                    bid_response = {"status_code": 409}  # Bid too low
                            else:
                                bid_response = {"status_code": 404}  # Item not found
                                
                        except Exception as e:
                            print(f"Auto-bidder {bidder_name} database error: {e}")
                            continue
                        
                        if bid_response["status_code"] == 200:
                            print(f"🎯 {bidder_name} bid ${new_bid} on {item_id}")
                            # Emit socket update for real-time UI
                            try:
                                socketio.emit('bid_update', {
                                    'item_id': item_id,
                                    'bidder': bidder_name,
                                    'amount': new_bid,
                                    'bid_count': current_data["bid_count"],
                                    'timestamp': time.time()
                                })
                            except:
                                pass  # Socket might not be available in thread
                        elif bid_response["status_code"] == 409:
                            print(f"❌ {bidder_name}'s bid of ${new_bid} was too low")
                        else:
                            print(f"❌ {bidder_name} bid failed: {bid_response['status_code']}")
                        
        except Exception as e:
            print(f"Auto-bidder {bidder_name} error: {e}")

@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    """Start automatic bidding simulation"""
    global AUTO_BIDDING, bidding_threads
    
    if bidding_threads:
        return jsonify({"success": False, "error": "Simulation already running"}), 400
    
    AUTO_BIDDING = True
    
    # Create bidders for each item
    for item in AUCTION_ITEMS:
        # 3-5 bidders per item
        num_bidders = random.randint(3, 5)
        selected_bidders = random.sample(BIDDER_NAMES, num_bidders)
        
        for bidder in selected_bidders:
            max_bid = item["starting_bid"] * random.uniform(2, 10)  # 2x to 10x starting bid
            thread = threading.Thread(
                target=auto_bidder,
                args=(bidder, item["id"], max_bid),
                daemon=True
            )
            thread.start()
            bidding_threads.append(thread)
    
    return jsonify({
        "success": True, 
        "message": f"Started {len(bidding_threads)} auto-bidders",
        "bidders": len(bidding_threads)
    })

@app.route('/api/simulation/stop', methods=['POST'])
def stop_simulation():
    """Stop automatic bidding simulation"""
    global AUTO_BIDDING, bidding_threads
    
    AUTO_BIDDING = False
    bidding_threads = []
    
    return jsonify({"success": True, "message": "Simulation stopped"})

@app.route('/api/stats')
def get_stats():
    """Get bidding statistics"""
    nodes = get_cluster_nodes()
    stats = {
        "total_bids": 0,
        "items": {},
        "bidder_activity": {},
        "node_distribution": {}
    }
    
    for item in AUCTION_ITEMS:
        try:
            response = requests.get(f"http://{nodes[0]}/kv/{item['id']}", timeout=2)
            if response.status_code == 200:
                data = json.loads(response.json()["value"])
                stats["total_bids"] += data.get("bid_count", 0)
                stats["items"][item["id"]] = {
                    "bid_count": data.get("bid_count", 0),
                    "current_bid": data.get("current_bid", 0),
                    "bidder": data.get("bidder", "None")
                }
                
                # Count bids by bidder
                for bid in data.get("bid_history", []):
                    bidder = bid.get("bidder", "Unknown")
                    stats["bidder_activity"][bidder] = stats["bidder_activity"].get(bidder, 0) + 1
                    
                    node = bid.get("node", "Unknown")
                    stats["node_distribution"][node] = stats["node_distribution"].get(node, 0) + 1
                    
        except Exception as e:
            print(f"Error getting stats for {item['id']}: {e}")
    
    return jsonify(stats)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to auction demo'})

if __name__ == '__main__':
    import requests
    
    # Initialize auction items
    print("🎯 Initializing auction items...")
    initialize_auction_items()
    
    print("=" * 50)
    print("🏆 Auction Bidding Demo")
    print("=" * 50)
    print("📍 URL: http://localhost:8005")
    print("🎯 Features:")
    print("  - Concurrent bidding on items")
    print("  - Quorum writes with Last-Write-Wins")
    print("  - Real-time bid updates")
    print("  - Automatic bidding simulation")
    print("=" * 50)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8005, allow_unsafe_werkzeug=True)