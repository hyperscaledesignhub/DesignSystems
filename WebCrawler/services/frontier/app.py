"""
URL Frontier Microservice
Manages URL queue with politeness constraints and prioritization
"""
import os
import sys
import time
import redis
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import heapq
import hashlib

# Add shared models to path
sys.path.append('/app/shared')
from models import URLRequest, URLBatch, ServiceHealth, ServiceStatus

app = Flask(__name__)
CORS(app)

# Redis connection
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Service configuration
SERVICE_NAME = "url-frontier"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()

# Frontier configuration
MAX_URLS_PER_HOST = 100
DEFAULT_CRAWL_DELAY = 1.0
BATCH_SIZE = 10


class URLFrontierService:
    def __init__(self):
        self.stats = {
            'urls_enqueued': 0,
            'urls_dequeued': 0,
            'unique_hosts': 0,
            'total_in_queue': 0
        }
    
    def _get_host(self, url: str) -> str:
        """Extract host from URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    def _get_url_hash(self, url: str) -> str:
        """Generate hash for URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def enqueue_url(self, url_request: URLRequest) -> bool:
        """Add URL to frontier queue"""
        try:
            url = url_request.url
            url_hash = self._get_url_hash(url)
            host = self._get_host(url)
            
            # Check if URL already exists
            if redis_client.sismember('frontier:seen_urls', url_hash):
                return False
            
            # Add to seen URLs
            redis_client.sadd('frontier:seen_urls', url_hash)
            
            # Store URL data
            url_data = {
                'url': url,
                'priority': url_request.priority,
                'crawl_delay': url_request.crawl_delay,
                'depth': url_request.depth,
                'metadata': url_request.metadata,
                'enqueued_at': datetime.now().isoformat()
            }
            
            # Add to priority queue (using Redis sorted set)
            score = -url_request.priority  # Negative for max-heap behavior
            redis_client.zadd(f'frontier:queue:{host}', {json.dumps(url_data): score})
            
            # Track host
            redis_client.sadd('frontier:hosts', host)
            
            # Update last access time for host
            redis_client.hset('frontier:host_access', host, time.time())
            
            # Update stats
            self.stats['urls_enqueued'] += 1
            self.stats['unique_hosts'] = redis_client.scard('frontier:hosts')
            
            return True
            
        except Exception as e:
            app.logger.error(f"Error enqueuing URL: {e}")
            return False
    
    def dequeue_urls(self, count: int = 1) -> List[Dict]:
        """Get URLs from queue respecting politeness"""
        urls = []
        current_time = time.time()
        
        try:
            # Get all hosts
            hosts = redis_client.smembers('frontier:hosts')
            
            for host in hosts:
                if len(urls) >= count:
                    break
                
                # Check politeness constraint
                last_access = redis_client.hget('frontier:host_access', host)
                if last_access:
                    last_access_time = float(last_access)
                    if current_time - last_access_time < DEFAULT_CRAWL_DELAY:
                        continue
                
                # Get URL from this host's queue
                queue_key = f'frontier:queue:{host}'
                url_data = redis_client.zrange(queue_key, 0, 0)
                
                if url_data:
                    # Remove from queue
                    redis_client.zrem(queue_key, url_data[0])
                    
                    # Update last access time
                    redis_client.hset('frontier:host_access', host, current_time)
                    
                    # Parse and add to results
                    url_info = json.loads(url_data[0])
                    urls.append(url_info)
                    
                    # Update stats
                    self.stats['urls_dequeued'] += 1
                    
                    # Remove host if queue is empty
                    if redis_client.zcard(queue_key) == 0:
                        redis_client.srem('frontier:hosts', host)
            
            self.stats['unique_hosts'] = redis_client.scard('frontier:hosts')
            return urls
            
        except Exception as e:
            app.logger.error(f"Error dequeuing URLs: {e}")
            return []
    
    def get_queue_size(self) -> int:
        """Get total queue size"""
        total = 0
        hosts = redis_client.smembers('frontier:hosts')
        for host in hosts:
            total += redis_client.zcard(f'frontier:queue:{host}')
        return total
    
    def get_stats(self) -> Dict:
        """Get frontier statistics"""
        self.stats['total_in_queue'] = self.get_queue_size()
        return self.stats.copy()


# Initialize service
frontier_service = URLFrontierService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health = ServiceHealth(
        service_name=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        uptime=time.time() - START_TIME,
        version=SERVICE_VERSION,
        metrics=frontier_service.get_stats()
    )
    return jsonify(health.dict())


@app.route('/enqueue', methods=['POST'])
def enqueue_url():
    """Add URL to frontier queue"""
    try:
        data = request.json
        url_request = URLRequest(**data)
        success = frontier_service.enqueue_url(url_request)
        
        return jsonify({
            'success': success,
            'url': url_request.url,
            'message': 'URL enqueued' if success else 'URL already seen'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/enqueue_batch', methods=['POST'])
def enqueue_batch():
    """Add multiple URLs to frontier"""
    try:
        data = request.json
        urls = data.get('urls', [])
        
        results = []
        for url_data in urls:
            url_request = URLRequest(**url_data)
            success = frontier_service.enqueue_url(url_request)
            results.append({
                'url': url_request.url,
                'success': success
            })
        
        successful = sum(1 for r in results if r['success'])
        return jsonify({
            'total': len(urls),
            'successful': successful,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/dequeue', methods=['GET'])
def dequeue_urls():
    """Get URLs from queue"""
    try:
        count = request.args.get('count', 1, type=int)
        count = min(count, BATCH_SIZE)  # Limit batch size
        
        urls = frontier_service.dequeue_urls(count)
        
        return jsonify({
            'urls': urls,
            'count': len(urls)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get frontier statistics"""
    return jsonify(frontier_service.get_stats())


@app.route('/clear', methods=['POST'])
def clear_queue():
    """Clear all queues (for testing)"""
    try:
        # Clear all frontier keys
        for key in redis_client.scan_iter('frontier:*'):
            redis_client.delete(key)
        
        # Reset stats
        frontier_service.stats = {
            'urls_enqueued': 0,
            'urls_dequeued': 0,
            'unique_hosts': 0,
            'total_in_queue': 0
        }
        
        return jsonify({'success': True, 'message': 'Queue cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)