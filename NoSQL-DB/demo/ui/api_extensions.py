#!/usr/bin/env python3
"""
API Extensions for REAL database operations
These endpoints perform ACTUAL operations against your distributed database cluster
"""

from flask import Blueprint, jsonify, request
import requests
import json
import time
import random
from real_traffic_generator import get_real_traffic_generator

api_bp = Blueprint('api_extensions', __name__, url_prefix='/api')

def get_cluster_nodes():
    """Get cluster nodes from environment"""
    import os
    cluster_env = os.environ.get('CLUSTER_NODES')
    if cluster_env:
        return [node.strip() for node in cluster_env.split(',')]
    return ["localhost:9999", "localhost:10000", "localhost:10001"]

@api_bp.route('/real/twitter/active_tweets')
def get_active_tweets():
    """Get REAL active tweets from traffic generator"""
    traffic_gen = get_real_traffic_generator()
    if traffic_gen:
        active_tweets = traffic_gen.get_active_tweets()
        
        # Get REAL data from database for each tweet
        tweets_data = []
        nodes = get_cluster_nodes()
        
        for tweet_id in active_tweets[-10:]:  # Last 10 tweets
            try:
                node = random.choice(nodes)
                response = requests.get(f"http://{node}/kv/{tweet_id}", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    tweet_data = json.loads(data.get("value", "{}"))
                    tweets_data.append({
                        'tweet_id': tweet_id,
                        'data': tweet_data,
                        'node': node
                    })
            except Exception as e:
                print(f"Error fetching tweet {tweet_id}: {e}")
        
        return jsonify({
            'success': True,
            'tweets': tweets_data,
            'total_active': len(active_tweets)
        })
    
    return jsonify({'success': False, 'error': 'No traffic generator running'})

@api_bp.route('/real/collab/active_documents')
def get_active_documents():
    """Get REAL active documents from traffic generator"""
    traffic_gen = get_real_traffic_generator()
    if traffic_gen:
        active_docs = traffic_gen.get_active_documents()
        
        # Get REAL data from database for each document
        docs_data = []
        nodes = get_cluster_nodes()
        
        for doc_id in active_docs[-5:]:  # Last 5 documents
            try:
                node = random.choice(nodes)
                response = requests.get(f"http://{node}/kv/{doc_id}", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    doc_data = json.loads(data.get("value", "{}"))
                    docs_data.append({
                        'doc_id': doc_id,
                        'data': doc_data,
                        'node': node
                    })
            except Exception as e:
                print(f"Error fetching document {doc_id}: {e}")
        
        return jsonify({
            'success': True,
            'documents': docs_data,
            'total_active': len(active_docs)
        })
    
    return jsonify({'success': False, 'error': 'No traffic generator running'})

@api_bp.route('/real/inventory/active_products')
def get_active_inventory():
    """Get REAL inventory data from database"""
    nodes = get_cluster_nodes()
    products = ["iphone-14-pro", "macbook-pro", "airpods-pro", "ipad-air", "apple-watch"]
    
    inventory_data = []
    
    for product in products:
        try:
            node = random.choice(nodes)
            response = requests.get(f"http://{node}/kv/inventory_{product}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                product_data = json.loads(data.get("value", "{}"))
                inventory_data.append({
                    'product_id': product,
                    'data': product_data,
                    'node': node
                })
        except Exception as e:
            print(f"Error fetching inventory {product}: {e}")
    
    return jsonify({
        'success': True,
        'inventory': inventory_data
    })

@api_bp.route('/real/cluster/write_test', methods=['POST'])
def cluster_write_test():
    """Perform REAL write test across all nodes"""
    nodes = get_cluster_nodes()
    test_key = f"test_write_{int(time.time() * 1000)}"
    test_data = {
        'message': 'REAL cluster write test',
        'timestamp': time.time(),
        'test_id': test_key
    }
    
    results = []
    
    for i, node in enumerate(nodes):
        try:
            start_time = time.time()
            response = requests.put(
                f"http://{node}/kv/{test_key}",
                json={"value": json.dumps(test_data)},
                timeout=5
            )
            end_time = time.time()
            
            if response.status_code == 200:
                results.append({
                    'node': node,
                    'status': 'success',
                    'latency_ms': round((end_time - start_time) * 1000, 2),
                    'response': response.json()
                })
            else:
                results.append({
                    'node': node,
                    'status': 'error',
                    'error': response.text
                })
                
        except Exception as e:
            results.append({
                'node': node,
                'status': 'error',
                'error': str(e)
            })
    
    return jsonify({
        'success': True,
        'test_key': test_key,
        'results': results,
        'total_nodes': len(nodes)
    })

@api_bp.route('/real/cluster/read_test/<test_key>')
def cluster_read_test(test_key):
    """Perform REAL read test across all nodes"""
    nodes = get_cluster_nodes()
    results = []
    
    for node in nodes:
        try:
            start_time = time.time()
            response = requests.get(f"http://{node}/kv/{test_key}", timeout=3)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                results.append({
                    'node': node,
                    'status': 'success',
                    'latency_ms': round((end_time - start_time) * 1000, 2),
                    'data': json.loads(data.get("value", "{}")),
                    'vector_clock': data.get("vector_clock", {})
                })
            else:
                results.append({
                    'node': node,
                    'status': 'error',
                    'error': response.text
                })
                
        except Exception as e:
            results.append({
                'node': node,
                'status': 'error',
                'error': str(e)
            })
    
    # Check consistency
    successful_reads = [r for r in results if r['status'] == 'success']
    consistent = True
    if len(successful_reads) > 1:
        first_data = successful_reads[0]['data']
        consistent = all(r['data'] == first_data for r in successful_reads)
    
    return jsonify({
        'success': True,
        'test_key': test_key,
        'results': results,
        'consistency_check': {
            'consistent': consistent,
            'successful_reads': len(successful_reads),
            'total_nodes': len(nodes)
        }
    })

@api_bp.route('/real/traffic/stats')
def get_traffic_stats():
    """Get REAL traffic generation statistics"""
    traffic_gen = get_real_traffic_generator()
    if traffic_gen:
        return jsonify({
            'success': True,
            'active_tweets': len(traffic_gen.get_active_tweets()),
            'active_documents': len(traffic_gen.get_active_documents()),
            'running': traffic_gen.running,
            'timestamp': time.time()
        })
    
    return jsonify({
        'success': False,
        'error': 'No traffic generator running',
        'active_tweets': 0,
        'active_documents': 0,
        'running': False
    })