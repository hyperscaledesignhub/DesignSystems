#!/usr/bin/env python3
"""
Inventory Management Demo for Distributed Database
Multi-warehouse inventory tracking with real-time updates
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

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from demo.demo_utils import DemoLogger, check_cluster_status

app = Flask(__name__)
app.config['SECRET_KEY'] = 'inventory-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
PRODUCTS = ["iphone-14-pro", "macbook-pro", "airpods-pro", "ipad-air", "apple-watch"]
WAREHOUSES = ["ny", "la", "chicago"]

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
def inventory_demo():
    """Inventory management demo UI"""
    return render_template('inventory_demo.html')

@app.route('/api/inventory')
def get_all_inventory():
    """Get inventory levels for all products across all warehouses"""
    nodes = get_cluster_nodes()
    inventory_data = {}
    
    for product in PRODUCTS:
        try:
            # Use random node for load balancing
            node = random.choice(nodes)
            response = requests.get(f"http://{node}/kv/inventory_{product}", timeout=3)
            
            if response.status_code == 200:
                response_data = response.json()
                
                if "error" in response_data:
                    inventory_data[product] = {"error": response_data["error"]}
                else:
                    value_str = response_data.get("value", "{}")
                    product_data = json.loads(value_str)
                    inventory_data[product] = {
                        "warehouses": product_data.get("warehouses", {}),
                        "last_updated": product_data.get("last_updated", time.time()),
                        "total_stock": sum(product_data.get("warehouses", {}).values()),
                        "node_used": node
                    }
            else:
                inventory_data[product] = {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            inventory_data[product] = {"error": str(e)}
    
    return jsonify({"success": True, "inventory": inventory_data})

@app.route('/api/inventory/<product>')
def get_product_inventory(product):
    """Get inventory for a specific product from all nodes"""
    nodes = get_cluster_nodes()
    product_data = {}
    
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/kv/inventory_{product}", timeout=3)
            if response.status_code == 200:
                response_data = response.json()
                
                if "error" in response_data:
                    product_data[f"node-{i+1}"] = {
                        "address": node,
                        "status": "error", 
                        "error": response_data["error"]
                    }
                else:
                    value_str = response_data.get("value", "{}")
                    inventory = json.loads(value_str)
                    product_data[f"node-{i+1}"] = {
                        "address": node,
                        "status": "healthy",
                        "inventory": inventory,
                        "total_stock": sum(inventory.get("warehouses", {}).values())
                    }
            else:
                product_data[f"node-{i+1}"] = {
                    "address": node,
                    "status": "no_data"
                }
        except Exception as e:
            product_data[f"node-{i+1}"] = {
                "address": node,
                "status": "error",
                "error": str(e)
            }
    
    return jsonify(product_data)

@app.route('/api/inventory/<product>/update', methods=['POST'])
def update_inventory():
    """Update inventory for a product in a specific warehouse"""
    data = request.json
    product = data.get("product")
    warehouse = data.get("warehouse")
    change = data.get("change", 0)  # Positive for shipments, negative for orders
    operation_type = "shipment" if change > 0 else "order"
    nodes = get_cluster_nodes()
    
    try:
        # Use random node for geographic distribution
        node = random.choice(nodes)
        
        # Get current inventory
        response = requests.get(f"http://{node}/kv/inventory_{product}", timeout=3)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if "error" in response_data:
                return jsonify({"success": False, "error": response_data["error"]}), 500
            
            value_str = response_data.get("value", "{}")
            inventory_data = json.loads(value_str)
        else:
            # Initialize if not exists
            inventory_data = {
                "product_id": product,
                "warehouses": {wh: random.randint(100, 500) for wh in WAREHOUSES},
                "last_updated": time.time()
            }
        
        # Update warehouse stock
        if "warehouses" not in inventory_data:
            inventory_data["warehouses"] = {}
        if warehouse not in inventory_data["warehouses"]:
            inventory_data["warehouses"][warehouse] = random.randint(100, 500)
        
        # Apply change and ensure stock doesn't go negative
        old_stock = inventory_data["warehouses"][warehouse]
        new_stock = max(0, old_stock + change)
        inventory_data["warehouses"][warehouse] = new_stock
        inventory_data["last_updated"] = time.time()
        
        # Write back to database
        write_response = requests.put(
            f"http://{node}/kv/inventory_{product}",
            json={"value": json.dumps(inventory_data)},
            timeout=3
        )
        
        if write_response.status_code == 200:
            write_data = write_response.json()
            
            if "error" in write_data:
                return jsonify({"success": False, "error": write_data["error"]}), 500
            
            # Emit real-time update
            socketio.emit('inventory_updated', {
                'product': product,
                'warehouse': warehouse,
                'operation': operation_type,
                'change': change,
                'old_stock': old_stock,
                'new_stock': new_stock,
                'total_stock': sum(inventory_data["warehouses"].values()),
                'node': node,
                'timestamp': time.time()
            })
            
            return jsonify({
                "success": True,
                "product": product,
                "warehouse": warehouse,
                "operation": operation_type,
                "change": change,
                "old_stock": old_stock,
                "new_stock": new_stock,
                "inventory": inventory_data,
                "node_used": node
            })
        else:
            return jsonify({"success": False, "error": f"Write failed: {write_response.text}"}), 500
            
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
    emit('connected', {'data': 'Connected to Inventory Management demo'})

# Background task for generating inventory traffic
def generate_inventory_traffic():
    """Generate realistic inventory management traffic"""
    
    while True:
        try:
            for product in PRODUCTS:
                if random.random() < 0.4:  # 40% chance per product
                    warehouse = random.choice(WAREHOUSES)
                    change = random.randint(-10, 20)  # Orders reduce, shipments increase
                    operation = "shipment" if change > 0 else "order"
                    
                    requests.post('http://localhost:8003/api/inventory/{}/update'.format(product),
                                json={
                                    "product": product,
                                    "warehouse": warehouse, 
                                    "change": change
                                }, timeout=3)
                    
                    print(f"📦 {operation.capitalize()}: {product} {warehouse} {change:+d}")
                    
                    time.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            print(f"Inventory traffic generation error: {e}")
        
        time.sleep(random.uniform(8, 20))  # Update cycle every 8-20 seconds

def init_inventory_data():
    """Initialize inventory data for all products"""
    nodes = get_cluster_nodes()
    
    for product in PRODUCTS:
        inventory_data = {
            "product_id": product,
            "warehouses": {
                warehouse: random.randint(100, 500) 
                for warehouse in WAREHOUSES
            },
            "last_updated": time.time(),
            "created_at": time.time()
        }
        
        try:
            response = requests.get(f"http://{nodes[0]}/kv/inventory_{product}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                if "value" in data and "error" not in data:
                    print(f"✅ Inventory for {product} already exists")
                    continue
        except:
            pass
        
        # Create initial inventory
        try:
            response = requests.put(
                f"http://{nodes[0]}/kv/inventory_{product}",
                json={"value": json.dumps(inventory_data)},
                timeout=5
            )
            if response.status_code == 200:
                total_stock = sum(inventory_data["warehouses"].values())
                print(f"✅ Initialized inventory for {product}: {total_stock} units across warehouses")
        except Exception as e:
            print(f"Error initializing inventory for {product}: {e}")

if __name__ == '__main__':
    # Initialize inventory data
    init_inventory_data()
    
    # Start background traffic generation
    traffic_thread = threading.Thread(target=generate_inventory_traffic, daemon=True)
    traffic_thread.start()
    
    print("📦 Starting Inventory Management Demo...")
    print("📍 URL: http://localhost:8003")
    print("🎯 Features: Multi-warehouse inventory tracking with real-time updates")
    print("🔄 Endpoints: Regular /kv/ (optimized for high-volume operations)")
    print("🏪 Warehouses: NY, LA, Chicago")
    print("📱 Products: iPhone, MacBook, AirPods, iPad, Apple Watch")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8003, allow_unsafe_werkzeug=True)