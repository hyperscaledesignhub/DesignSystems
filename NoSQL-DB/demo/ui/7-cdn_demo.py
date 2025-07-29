#!/usr/bin/env python3
"""
CDN Distribution Demo for Distributed Database
Content distribution and caching simulation
"""
import os
import sys
import json
import time
import threading
import requests
import random
import hashlib
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from demo.demo_utils import DemoLogger, check_cluster_status

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cdn-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
CDN_REGIONS = ["us-east", "us-west", "eu-west", "asia-pacific"]
CONTENT_TYPES = ["image", "video", "document", "webpage", "api_response"]

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

def get_region_for_node(node):
    """Map cluster nodes to CDN regions"""
    node_region_map = {
        "localhost:9999": "us-east",
        "localhost:10000": "us-west", 
        "localhost:10001": "eu-west"
    }
    return node_region_map.get(node, "asia-pacific")

@app.route('/')
def cdn_demo():
    """CDN distribution demo UI"""
    return render_template('cdn_demo.html')

@app.route('/api/content')
def list_cached_content():
    """List all cached content across CDN regions"""
    nodes = get_cluster_nodes()
    content_data = {}
    
    for node in nodes:
        region = get_region_for_node(node)
        content_data[region] = {"node": node, "cached_items": [], "cache_hits": 0, "cache_misses": 0}
        
        try:
            # Get cache statistics for this region
            stats_response = requests.get(f"http://{node}/kv/cdn_stats_{region}", timeout=3)
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                if "value" in stats_data and "error" not in stats_data:
                    stats = json.loads(stats_data["value"])
                    content_data[region]["cache_hits"] = stats.get("cache_hits", 0)
                    content_data[region]["cache_misses"] = stats.get("cache_misses", 0)
            
            # Search for cached content items (this is a simplified approach)
            # In a real CDN, we'd have a content registry
            for content_type in CONTENT_TYPES:
                for i in range(1, 6):  # Check for content_1 through content_5
                    content_id = f"{content_type}_{i}"
                    cache_key = f"cdn_cache_{region}_{content_id}"
                    
                    try:
                        response = requests.get(f"http://{node}/kv/{cache_key}", timeout=1)
                        if response.status_code == 200:
                            data = response.json()
                            if "value" in data and "error" not in data:
                                cached_item = json.loads(data["value"])
                                content_data[region]["cached_items"].append({
                                    "content_id": content_id,
                                    "content_type": cached_item.get("content_type", content_type),
                                    "size_kb": cached_item.get("size_kb", 0),
                                    "cached_at": cached_item.get("cached_at", time.time()),
                                    "hit_count": cached_item.get("hit_count", 0),
                                    "last_accessed": cached_item.get("last_accessed", time.time())
                                })
                    except:
                        continue  # Content not cached in this region
                        
        except Exception as e:
            content_data[region]["error"] = str(e)
    
    return jsonify({"success": True, "regions": content_data})

@app.route('/api/content/<content_id>/request', methods=['POST'])
def request_content():
    """Simulate content request through CDN"""
    data = request.json
    content_id = data.get("content_id")
    user_region = data.get("region", random.choice(CDN_REGIONS))
    content_type = data.get("content_type", random.choice(CONTENT_TYPES))
    
    nodes = get_cluster_nodes()
    
    # Find the node serving this region
    region_node = None
    for node in nodes:
        if get_region_for_node(node) == user_region:
            region_node = node
            break
    
    if not region_node:
        region_node = random.choice(nodes)  # Fallback
        user_region = get_region_for_node(region_node)
    
    cache_key = f"cdn_cache_{user_region}_{content_id}"
    cache_hit = False
    response_time = 0
    
    try:
        start_time = time.time()
        
        # Check if content is cached in user's region
        response = requests.get(f"http://{region_node}/kv/{cache_key}", timeout=3)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if "value" in response_data and "error" not in response_data:
                # Cache hit!
                cache_hit = True
                cached_content = json.loads(response_data["value"])
                
                # Update hit count and last accessed
                cached_content["hit_count"] = cached_content.get("hit_count", 0) + 1
                cached_content["last_accessed"] = time.time()
                
                # Write back updated cache entry
                requests.put(f"http://{region_node}/kv/{cache_key}",
                           json={"value": json.dumps(cached_content)}, timeout=3)
                
                response_time = (time.time() - start_time) * 1000  # ms
                
            else:
                # Cache miss - simulate fetching from origin
                cache_hit = False
                response_time = random.uniform(200, 800)  # Slower origin fetch
                
                # Create and cache the content
                content_data = {
                    "content_id": content_id,
                    "content_type": content_type,
                    "size_kb": random.randint(50, 5000),
                    "cached_at": time.time(),
                    "hit_count": 1,
                    "last_accessed": time.time(),
                    "origin_server": "origin.example.com",
                    "region": user_region
                }
                
                requests.put(f"http://{region_node}/kv/{cache_key}",
                           json={"value": json.dumps(content_data)}, timeout=3)
        else:
            # Cache miss - content not found
            cache_hit = False
            response_time = random.uniform(200, 800)
            
            # Create and cache the content
            content_data = {
                "content_id": content_id,
                "content_type": content_type,
                "size_kb": random.randint(50, 5000),
                "cached_at": time.time(),
                "hit_count": 1,
                "last_accessed": time.time(),
                "origin_server": "origin.example.com",
                "region": user_region
            }
            
            requests.put(f"http://{region_node}/kv/{cache_key}",
                       json={"value": json.dumps(content_data)}, timeout=3)
        
        # Update region cache statistics
        stats_key = f"cdn_stats_{user_region}"
        try:
            stats_response = requests.get(f"http://{region_node}/kv/{stats_key}", timeout=3)
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                if "value" in stats_data and "error" not in stats_data:
                    stats = json.loads(stats_data["value"])
                else:
                    stats = {"cache_hits": 0, "cache_misses": 0, "total_requests": 0}
            else:
                stats = {"cache_hits": 0, "cache_misses": 0, "total_requests": 0}
            
            if cache_hit:
                stats["cache_hits"] += 1
            else:
                stats["cache_misses"] += 1
            stats["total_requests"] += 1
            stats["last_updated"] = time.time()
            
            requests.put(f"http://{region_node}/kv/{stats_key}",
                       json={"value": json.dumps(stats)}, timeout=3)
        except:
            pass  # Stats update failed, but request succeeded
        
        # Emit real-time update
        socketio.emit('content_requested', {
            'content_id': content_id,
            'content_type': content_type,
            'region': user_region,
            'cache_hit': cache_hit,
            'response_time': response_time,
            'node': region_node,
            'timestamp': time.time()
        })
        
        return jsonify({
            "success": True,
            "content_id": content_id,
            "region": user_region,
            "cache_hit": cache_hit,
            "response_time_ms": round(response_time, 2),
            "node_used": region_node,
            "message": "Cache hit - content served from edge" if cache_hit else "Cache miss - content fetched from origin"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/content/<content_id>/invalidate', methods=['POST'])
def invalidate_content():
    """Invalidate cached content across all CDN regions"""
    data = request.json
    content_id = data.get("content_id")
    nodes = get_cluster_nodes()
    
    invalidated_regions = []
    
    for node in nodes:
        region = get_region_for_node(node)
        cache_key = f"cdn_cache_{region}_{content_id}"
        
        try:
            # Check if content exists in this region
            response = requests.get(f"http://{node}/kv/{cache_key}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                if "value" in data and "error" not in data:
                    # Content exists, invalidate it by deleting
                    # Note: In this demo, we'll just mark it as invalidated
                    cached_content = json.loads(data["value"])
                    cached_content["invalidated"] = True
                    cached_content["invalidated_at"] = time.time()
                    
                    requests.put(f"http://{node}/kv/{cache_key}",
                               json={"value": json.dumps(cached_content)}, timeout=3)
                    
                    invalidated_regions.append(region)
        except:
            continue
    
    # Emit real-time update
    socketio.emit('content_invalidated', {
        'content_id': content_id,
        'regions': invalidated_regions,
        'timestamp': time.time()
    })
    
    return jsonify({
        "success": True,
        "content_id": content_id,
        "invalidated_regions": invalidated_regions,
        "message": f"Content invalidated in {len(invalidated_regions)} regions"
    })

@app.route('/api/cluster/status')
def cluster_status():
    """Get cluster health status"""
    nodes = get_cluster_nodes()
    status = {}
    
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/health", timeout=2)
            if response.status_code == 200:
                region = get_region_for_node(node)
                status[f"node-{i+1}"] = {
                    "address": node,
                    "region": region,
                    "status": "healthy",
                    "data": response.json()
                }
            else:
                status[f"node-{i+1}"] = {
                    "address": node,
                    "region": get_region_for_node(node),
                    "status": "error",
                    "message": f"HTTP {response.status_code}"
                }
        except Exception as e:
            status[f"node-{i+1}"] = {
                "address": node,
                "region": get_region_for_node(node),
                "status": "offline",
                "message": str(e)
            }
    
    return jsonify(status)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to CDN Distribution demo'})

# Background task for generating CDN traffic
def generate_cdn_traffic():
    """Generate realistic CDN request traffic"""
    
    content_items = [
        {"id": "homepage_css", "type": "document"},
        {"id": "product_image_1", "type": "image"},
        {"id": "promo_video", "type": "video"},
        {"id": "api_products", "type": "api_response"},
        {"id": "user_avatar_123", "type": "image"},
        {"id": "landing_page", "type": "webpage"}
    ]
    
    while True:
        try:
            # Generate content requests
            for _ in range(random.randint(1, 3)):
                content = random.choice(content_items)
                region = random.choice(CDN_REGIONS)
                
                requests.post('http://localhost:8004/api/content/{}/request'.format(content["id"]),
                            json={
                                "content_id": content["id"],
                                "region": region,
                                "content_type": content["type"]
                            }, timeout=3)
                
                print(f"🌐 CDN Request: {content['id']} from {region}")
                
                time.sleep(random.uniform(0.5, 2.0))
            
            # Occasionally invalidate content
            if random.random() < 0.1:  # 10% chance
                content = random.choice(content_items)
                requests.post(f'http://localhost:8004/api/content/{content["id"]}/invalidate',
                            json={"content_id": content["id"]}, timeout=3)
                print(f"🗑️ Invalidated: {content['id']}")
            
        except Exception as e:
            print(f"CDN traffic generation error: {e}")
        
        time.sleep(random.uniform(3, 8))  # Request cycle every 3-8 seconds

def init_cdn_regions():
    """Initialize CDN region statistics"""
    nodes = get_cluster_nodes()
    
    for node in nodes:
        region = get_region_for_node(node)
        stats_data = {
            "region": region,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_requests": 0,
            "initialized_at": time.time(),
            "last_updated": time.time()
        }
        
        stats_key = f"cdn_stats_{region}"
        
        try:
            # Check if stats already exist
            response = requests.get(f"http://{node}/kv/{stats_key}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                if "value" in data and "error" not in data:
                    print(f"✅ CDN stats for {region} already exist")
                    continue
        except:
            pass
        
        # Initialize stats
        try:
            response = requests.put(f"http://{node}/kv/{stats_key}",
                                  json={"value": json.dumps(stats_data)}, timeout=5)
            if response.status_code == 200:
                print(f"✅ Initialized CDN region: {region} on {node}")
        except Exception as e:
            print(f"Error initializing CDN region {region}: {e}")

if __name__ == '__main__':
    # Initialize CDN regions
    init_cdn_regions()
    
    # Start background traffic generation
    traffic_thread = threading.Thread(target=generate_cdn_traffic, daemon=True)
    traffic_thread.start()
    
    print("🌐 Starting CDN Distribution Demo...")
    print("📍 URL: http://localhost:8004")
    print("🎯 Features: Content distribution and caching simulation")
    print("🔄 Endpoints: Regular /kv/ (optimized for cache operations)")
    print("🌍 Regions: US-East, US-West, EU-West, Asia-Pacific")
    print("📦 Content Types: Images, Videos, Documents, Webpages, API Responses")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8004, allow_unsafe_werkzeug=True)