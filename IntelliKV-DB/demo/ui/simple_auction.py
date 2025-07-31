#!/usr/bin/env python3
"""
Simple Auction Demo - Direct HTML without templates
"""
import os
import json
import time
import threading
import random
import requests
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'auction-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = ["localhost:9999", "localhost:10000", "localhost:10001"]
AUCTION_ITEMS = [
    {"id": "item_1", "name": "🖼️ Rare Digital Art", "starting_bid": 100},
    {"id": "item_2", "name": "⌚ Vintage Watch", "starting_bid": 500},
    {"id": "item_3", "name": "🎸 Signed Guitar", "starting_bid": 1000},
]

@app.route('/')
def auction_demo():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🏆 Auction Demo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            h1 {
                text-align: center;
                color: #2563eb;
                margin-bottom: 30px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #f8fafc;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                border-left: 4px solid #2563eb;
            }
            .stat-value {
                font-size: 2rem;
                font-weight: bold;
                color: #1f2937;
                margin-bottom: 5px;
            }
            .stat-label {
                color: #6b7280;
                font-size: 0.9rem;
                text-transform: uppercase;
            }
            .auction-items {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .auction-item {
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 20px;
                transition: transform 0.3s ease;
            }
            .auction-item:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            }
            .item-name {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #1f2937;
            }
            .current-bid {
                text-align: center;
                margin: 20px 0;
            }
            .bid-amount {
                font-size: 36px;
                font-weight: bold;
                color: #10b981;
                margin-bottom: 5px;
            }
            .bid-label {
                font-size: 14px;
                color: #6b7280;
            }
            .bidder-info {
                text-align: center;
                margin: 15px 0;
                color: #16a34a;
                font-weight: 600;
            }
            .btn {
                background: #2563eb;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: background 0.3s ease;
                margin: 5px;
            }
            .btn:hover {
                background: #1d4ed8;
            }
            .btn-success {
                background: #10b981;
            }
            .btn-success:hover {
                background: #059669;
            }
            .btn-danger {
                background: #ef4444;
            }
            .btn-danger:hover {
                background: #dc2626;
            }
            .form-section {
                background: #f8fafc;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            .form-group {
                margin: 10px;
                display: inline-block;
            }
            .form-input {
                padding: 10px;
                border: 2px solid #e5e7eb;
                border-radius: 6px;
                margin-left: 10px;
            }
            .activity-log {
                background: #f8fafc;
                border-radius: 8px;
                padding: 15px;
                max-height: 300px;
                overflow-y: auto;
                margin-top: 20px;
            }
            .activity-entry {
                padding: 8px;
                margin: 5px 0;
                background: white;
                border-radius: 6px;
                border-left: 4px solid #2563eb;
            }
            .live-indicator {
                background: #10b981;
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 10px;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .message {
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                font-weight: 600;
            }
            .success-message {
                background: rgba(34, 197, 94, 0.1);
                color: #16a34a;
                border-left: 4px solid #16a34a;
            }
            .error-message {
                background: rgba(239, 68, 68, 0.1);
                color: #dc2626;
                border-left: 4px solid #dc2626;
            }
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    </head>
    <body>
        <div class="container">
            <h1>🏆 Live Auction Platform <span class="live-indicator">LIVE</span></h1>
            
            <!-- Stats -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="totalBids">0</div>
                    <div class="stat-label">Total Bids</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="activeBidders">0</div>
                    <div class="stat-label">Active Bidders</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="highestBid">$0</div>
                    <div class="stat-label">Highest Bid</div>
                </div>
            </div>
            
            <!-- Auction Items -->
            <div id="auctionItems" class="auction-items">
                <p>Loading auction items...</p>
            </div>
            
            <!-- Manual Bidding -->
            <div class="form-section">
                <h3>🎲 Place Your Bid</h3>
                <div class="form-group">
                    <label>Item:</label>
                    <select id="bidItemSelect" class="form-input">
                        <option value="item_1">🖼️ Rare Digital Art</option>
                        <option value="item_2">⌚ Vintage Watch</option>
                        <option value="item_3">🎸 Signed Guitar</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Name:</label>
                    <input type="text" id="bidderName" class="form-input" placeholder="Your name" value="Manual User">
                </div>
                <div class="form-group">
                    <label>Amount ($):</label>
                    <input type="number" id="bidAmount" class="form-input" placeholder="Bid amount" min="1">
                </div>
                <button class="btn" onclick="placeBid()">💰 Place Bid</button>
            </div>
            
            <!-- Simulation Control -->
            <div class="form-section">
                <h3>🤖 Auto-Bidding Simulation</h3>
                <button class="btn btn-success" onclick="startSimulation()" id="startBtn">▶️ Start Auto-Bidding</button>
                <button class="btn btn-danger" onclick="stopSimulation()" id="stopBtn" disabled>⏹️ Stop Auto-Bidding</button>
                <button class="btn" onclick="loadAuctionItems()">🔄 Refresh</button>
                <div id="simulationStatus" style="margin-top: 15px; display: none;">
                    <strong>Simulation Active:</strong> <span id="simBidders">0</span> automated bidders competing
                </div>
            </div>
            
            <!-- Activity Log -->
            <div class="activity-log" id="activityLog">
                <div style="text-align: center; color: #6b7280;">
                    Auction activity will appear here...
                </div>
            </div>
        </div>

        <script>
            console.log('🏆 Auction demo starting...');
            
            // Initialize Socket.IO
            const socket = io();
            let stats = { totalBids: 0, conflicts: 0 };
            
            // Helper function to show messages
            function showMessage(message, type = 'info') {
                const messageClass = type === 'success' ? 'success-message' : 'error-message';
                const alertDiv = document.createElement('div');
                alertDiv.className = `message ${messageClass}`;
                alertDiv.textContent = message;
                
                const container = document.querySelector('.container');
                container.insertBefore(alertDiv, container.firstChild);
                
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.remove();
                    }
                }, 4000);
            }
            
            // Load auction items
            function loadAuctionItems() {
                console.log('Loading auction items...');
                fetch('/api/items')
                    .then(response => {
                        console.log('Response status:', response.status);
                        return response.json();
                    })
                    .then(data => {
                        console.log('Received data:', data);
                        displayAuctionItems(data.items);
                        updateStats(data.items);
                    })
                    .catch(error => {
                        console.error('Error loading items:', error);
                        document.getElementById('auctionItems').innerHTML = 
                            '<div class="error-message">Error loading auction items: ' + error.message + '</div>';
                    });
            }
            
            // Display auction items
            function displayAuctionItems(items) {
                const container = document.getElementById('auctionItems');
                container.innerHTML = '';
                
                items.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'auction-item';
                    itemDiv.innerHTML = `
                        <div class="item-name">${item.name}</div>
                        <div class="current-bid">
                            <div class="bid-amount">$${item.current_bid || 0}</div>
                            <div class="bid-label">Current Bid</div>
                        </div>
                        <div class="bidder-info">
                            ${item.bidder ? `👤 ${item.bidder}` : 'No bids yet'}
                        </div>
                        <div style="text-align: center; color: #6b7280; font-size: 14px;">
                            ${item.bid_count || 0} bids placed
                        </div>
                    `;
                    container.appendChild(itemDiv);
                });
            }
            
            // Update statistics
            function updateStats(items) {
                let totalBids = 0;
                let highestBid = 0;
                let activeBidders = new Set();
                
                items.forEach(item => {
                    totalBids += item.bid_count || 0;
                    if (item.current_bid > highestBid) {
                        highestBid = item.current_bid;
                    }
                    if (item.bidder) {
                        activeBidders.add(item.bidder);
                    }
                });
                
                document.getElementById('totalBids').textContent = totalBids;
                document.getElementById('highestBid').textContent = `$${highestBid}`;
                document.getElementById('activeBidders').textContent = activeBidders.size;
                
                stats.totalBids = totalBids;
            }
            
            // Place manual bid
            function placeBid() {
                const itemId = document.getElementById('bidItemSelect').value;
                const bidder = document.getElementById('bidderName').value;
                const amount = parseInt(document.getElementById('bidAmount').value);
                
                if (!bidder || !amount) {
                    showMessage('Please enter your name and bid amount', 'error');
                    return;
                }
                
                fetch('/api/bid', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ item_id: itemId, bidder: bidder, amount: amount })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showMessage(`✅ Bid placed successfully!`, 'success');
                        logActivity(`✅ Your bid of $${amount} was accepted`);
                        document.getElementById('bidAmount').value = '';
                        loadAuctionItems();
                    } else {
                        showMessage(`❌ ${data.message || data.error}`, 'error');
                        logActivity(`❌ Bid rejected: ${data.error || data.message}`);
                    }
                })
                .catch(error => {
                    showMessage(`Error: ${error.message}`, 'error');
                });
            }
            
            // Start simulation
            function startSimulation() {
                fetch('/api/simulation/start', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('startBtn').disabled = true;
                            document.getElementById('stopBtn').disabled = false;
                            document.getElementById('simulationStatus').style.display = 'block';
                            document.getElementById('simBidders').textContent = data.bidders;
                            showMessage('🤖 Auto-bidding simulation started!', 'success');
                            logActivity('🚀 Started automated bidding simulation');
                        }
                    });
            }
            
            // Stop simulation
            function stopSimulation() {
                fetch('/api/simulation/stop', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('startBtn').disabled = false;
                            document.getElementById('stopBtn').disabled = true;
                            document.getElementById('simulationStatus').style.display = 'none';
                            showMessage('🛑 Simulation stopped', 'success');
                            logActivity('⏹️ Stopped automated bidding simulation');
                        }
                    });
            }
            
            // Log activity
            function logActivity(message) {
                const log = document.getElementById('activityLog');
                const entry = document.createElement('div');
                const timestamp = new Date().toLocaleTimeString();
                
                entry.className = 'activity-entry';
                entry.innerHTML = `<strong>${timestamp}</strong> ${message}`;
                
                if (log.children[0] && log.children[0].textContent.includes('will appear')) {
                    log.innerHTML = '';
                }
                
                log.insertBefore(entry, log.firstChild);
                
                // Keep only last 20 entries
                while (log.children.length > 20) {
                    log.removeChild(log.lastChild);
                }
            }
            
            // Socket event handlers
            socket.on('bid_update', function(data) {
                console.log('New bid:', data);
                logActivity(`💰 ${data.bidder} bid $${data.amount} on ${data.item_id}`);
                loadAuctionItems();
            });
            
            socket.on('connect', function() {
                console.log('✅ Connected to auction server');
                logActivity('🔗 Connected to live auction feed');
                loadAuctionItems();
            });
            
            socket.on('disconnect', function() {
                console.log('❌ Disconnected from auction server');
                logActivity('❌ Disconnected from auction server');
            });
            
            // Initialize on page load
            document.addEventListener('DOMContentLoaded', function() {
                console.log('✅ Page loaded, initializing auction demo');
                logActivity('🏆 Auction demo initialized');
                
                // Auto-refresh every 3 seconds
                setInterval(loadAuctionItems, 3000);
            });
        </script>
    </body>
    </html>
    '''

@app.route('/api/items')
def get_auction_items():
    """Get all auction items with current bids"""
    items = []
    
    for item in AUCTION_ITEMS:
        try:
            # Use first working node to avoid timeouts
            node = CLUSTER_NODES[0]
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
                    "status": "active"
                })
        except Exception as e:
            print(f"Error fetching {item['id']}: {e}")
            items.append({
                "item_id": item["id"],
                "name": item["name"],
                "current_bid": item["starting_bid"],
                "bidder": None,
                "bid_count": 0,
                "error": str(e)
            })
    
    return jsonify({"items": items})

@app.route('/api/bid', methods=['POST'])
def place_bid():
    """Place a bid on an item"""
    data = request.json
    item_id = data.get('item_id')
    bidder = data.get('bidder')
    bid_amount = data.get('amount')
    
    if not all([item_id, bidder, bid_amount]):
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    node = CLUSTER_NODES[0]
    
    try:
        # Read current item state
        response = requests.get(f"http://{node}/kv/{item_id}", timeout=3)
        
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
                "message": f"Your bid of ${bid_amount} is not higher than current bid of ${current_value['current_bid']}"
            }), 409
        
        # Update with new bid
        current_value["current_bid"] = bid_amount
        current_value["bidder"] = bidder
        current_value["bid_count"] += 1
        current_value["last_bid_time"] = time.time()
        
        # Write back
        write_response = requests.put(
            f"http://{node}/kv/{item_id}",
            json={"value": json.dumps(current_value)},
            timeout=3
        )
        
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
                "message": "Bid placed successfully!",
                "bid": {"amount": bid_amount, "bidder": bidder, "item_id": item_id}
            })
        else:
            return jsonify({"success": False, "error": "Failed to place bid"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Global variables for auto-bidding
AUTO_BIDDING = False
bidding_threads = []
BIDDER_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]

def auto_bidder(bidder_name, item_id, max_bid):
    """Simulate automatic bidding behavior"""
    global AUTO_BIDDING
    
    while AUTO_BIDDING:
        try:
            # Random delay between bids
            time.sleep(random.uniform(1, 4))
            
            # Get current bid
            node = CLUSTER_NODES[0]
            response = requests.get(f"http://{node}/kv/{item_id}", timeout=2)
            
            if response.status_code == 200:
                data = json.loads(response.json()["value"])
                current_bid = data["current_bid"]
                
                # Decide whether to bid (70% chance)
                if current_bid < max_bid and random.random() > 0.3:
                    bid_increment = random.choice([10, 20, 50, 100])
                    new_bid = current_bid + bid_increment
                    
                    if new_bid <= max_bid:
                        # Place bid directly to database
                        try:
                            # Read current item state
                            read_response = requests.get(f"http://{node}/kv/{item_id}", timeout=2)
                            if read_response.status_code == 200:
                                current_data = json.loads(read_response.json()["value"])
                                
                                # Check if bid is still valid
                                if new_bid > current_data["current_bid"]:
                                    # Update with new bid
                                    current_data["current_bid"] = new_bid
                                    current_data["bidder"] = bidder_name
                                    current_data["bid_count"] += 1
                                    current_data["last_bid_time"] = time.time()
                                    
                                    # Write back
                                    write_response = requests.put(
                                        f"http://{node}/kv/{item_id}",
                                        json={"value": json.dumps(current_data)},
                                        timeout=2
                                    )
                                    
                                    if write_response.status_code == 200:
                                        print(f"🎯 {bidder_name} bid ${new_bid} on {item_id}")
                                        # Emit socket update for real-time UI
                                        socketio.emit('bid_update', {
                                            'item_id': item_id,
                                            'bidder': bidder_name,
                                            'amount': new_bid,
                                            'bid_count': current_data["bid_count"],
                                            'timestamp': time.time()
                                        })
                                    else:
                                        print(f"❌ {bidder_name} bid failed: {write_response.status_code}")
                                        
                        except Exception as e:
                            print(f"Auto-bidder {bidder_name} database error: {e}")
                            continue
                        
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
        # 2-4 bidders per item
        num_bidders = random.randint(2, 4)
        selected_bidders = random.sample(BIDDER_NAMES, num_bidders)
        
        for bidder in selected_bidders:
            max_bid = item["starting_bid"] * random.uniform(3, 8)  # 3x to 8x starting bid
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
    
    return jsonify({"success": True, "message": "Auto-bidding simulation stopped"})

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to auction demo'})

if __name__ == '__main__':
    print("🏆 Starting Simple Auction Demo")
    print("📍 URL: http://localhost:8007")
    print("🎯 This is a simplified version to test UI functionality")
    print("=" * 50)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8007, allow_unsafe_werkzeug=True)