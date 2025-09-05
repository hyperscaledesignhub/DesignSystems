"""
API Gateway Service - Fixed Version
Orchestrates communication between all microservices with proper state management
"""
import os
import sys
import time
import requests
import json
import redis
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

# Add shared models to path
sys.path.append('/app/shared')
from models import (
    URLRequest, DownloadRequest, ParseRequest,
    DeduplicationRequest, ServiceHealth, ServiceStatus,
    CrawlStatus
)

app = Flask(__name__)
CORS(app)

# Service configuration
SERVICE_NAME = "api-gateway"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()

# Microservice URLs
SERVICES = {
    'frontier': os.getenv('FRONTIER_URL', 'http://frontier:5000'),
    'downloader': os.getenv('DOWNLOADER_URL', 'http://downloader:5000'),
    'parser': os.getenv('PARSER_URL', 'http://parser:5000'),
    'deduplication': os.getenv('DEDUP_URL', 'http://deduplication:5000'),
    'extractor': os.getenv('EXTRACTOR_URL', 'http://crawler-extractor:5000'),
    'storage': os.getenv('STORAGE_URL', 'http://crawler-storage:5000')
}


class APIGateway:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.is_crawling = False
        self.crawl_thread = None
        self.stop_requested = False
        
        # Redis connection for persistent stats
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            decode_responses=True
        )
        
        # Initialize persistent cumulative stats in Redis if not exists
        self._init_persistent_stats()
        
        # Current crawl stats (in-memory, resets per crawl)
        self.crawl_stats = {
            'crawl_id': None,
            'status': 'idle',
            'pages_processed': 0,
            'pages_queued': 0,
            'duplicates_found': 0,
            'errors_count': 0,
            'start_time': None,
            'elapsed_time': 0
        }
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
    def _init_persistent_stats(self):
        """Initialize persistent statistics in Redis"""
        stats_keys = [
            'crawler:total_pages_processed',
            'crawler:total_duplicates_found', 
            'crawler:total_errors',
            'crawler:total_urls_extracted',
            'crawler:total_crawls_started',
            'crawler:total_crawls_completed'
        ]
        
        for key in stats_keys:
            if not self.redis_client.exists(key):
                self.redis_client.set(key, 0)
    
    def _increment_persistent_stat(self, stat_name: str, amount: int = 1):
        """Thread-safe increment of persistent statistics"""
        try:
            key = f"crawler:{stat_name}"
            self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"Error updating persistent stat {stat_name}: {e}")
    
    def _get_persistent_stats(self) -> Dict:
        """Get all persistent statistics from Redis"""
        try:
            return {
                'total_pages_processed': int(self.redis_client.get('crawler:total_pages_processed') or 0),
                'total_duplicates_found': int(self.redis_client.get('crawler:total_duplicates_found') or 0),
                'total_errors': int(self.redis_client.get('crawler:total_errors') or 0),
                'total_urls_extracted': int(self.redis_client.get('crawler:total_urls_extracted') or 0),
                'total_crawls_started': int(self.redis_client.get('crawler:total_crawls_started') or 0),
                'total_crawls_completed': int(self.redis_client.get('crawler:total_crawls_completed') or 0)
            }
        except Exception as e:
            print(f"Error reading persistent stats: {e}")
            return {
                'total_pages_processed': 0,
                'total_duplicates_found': 0,
                'total_errors': 0,
                'total_urls_extracted': 0,
                'total_crawls_started': 0,
                'total_crawls_completed': 0
            }
    
    def _make_request(self, service: str, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """Make request to a microservice"""
        try:
            url = f"{SERVICES[service]}{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f"Service returned {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            return {'error': f"Could not connect to {service} service"}
        except requests.exceptions.Timeout:
            return {'error': f"Timeout connecting to {service} service"}
        except Exception as e:
            return {'error': str(e)}
    
    def process_url(self, url: str) -> Dict:
        """Process a single URL through the entire pipeline"""
        result = {'url': url, 'success': False, 'steps': {}}
        
        try:
            # Step 1: Download content
            download_resp = self._make_request(
                'downloader', '/download', 'POST',
                {'url': url}
            )
            result['steps']['download'] = download_resp
            
            if not download_resp.get('success'):
                result['error'] = 'Download failed'
                return result
            
            # Step 2: Parse content
            parse_resp = self._make_request(
                'parser', '/parse', 'POST',
                {
                    'url': url,
                    'content': download_resp['content'],
                    'extract_metadata': True
                }
            )
            result['steps']['parse'] = parse_resp
            
            if not parse_resp.get('success'):
                result['error'] = 'Parse failed'
                return result
            
            # Step 3: Check for duplicates
            dedup_resp = self._make_request(
                'deduplication', '/check', 'POST',
                {
                    'url': url,
                    'content': parse_resp['text']
                }
            )
            result['steps']['deduplication'] = dedup_resp
            
            if dedup_resp.get('is_duplicate'):
                result['is_duplicate'] = True
                with self.lock:
                    self.crawl_stats['duplicates_found'] += 1
                # Update persistent stats
                self._increment_persistent_stat('total_duplicates_found', 1)
            
            # Step 4: Extract URLs (if extractor service exists)
            if 'extractor' in SERVICES:
                extract_resp = self._make_request(
                    'extractor', '/extract', 'POST',
                    {
                        'url': url,
                        'html_content': download_resp['content']
                    }
                )
                result['steps']['extraction'] = extract_resp
                
                # Add extracted URLs to frontier
                if extract_resp.get('extracted_urls'):
                    urls_added = 0
                    for extracted_url in extract_resp['extracted_urls'][:10]:  # Limit for demo
                        resp = self._make_request(
                            'frontier', '/enqueue', 'POST',
                            {'url': extracted_url, 'priority': 5, 'depth': 1}
                        )
                        if resp and not resp.get('error'):
                            urls_added += 1
                    
                    # Update persistent stats
                    self._increment_persistent_stat('total_urls_extracted', urls_added)
            
            # Step 5: Store content (if storage service exists)
            if 'storage' in SERVICES:
                storage_resp = self._make_request(
                    'storage', '/store', 'POST',
                    {
                        'url': url,
                        'content': download_resp['content'],
                        'metadata': {
                            'title': parse_resp.get('title'),
                            'text_length': len(parse_resp.get('text', '')),
                            'links_count': len(parse_resp.get('links', []))
                        }
                    }
                )
                result['steps']['storage'] = storage_resp
            
            result['success'] = True
            
            # Update stats
            with self.lock:
                self.crawl_stats['pages_processed'] += 1
            
            # Update persistent stats
            self._increment_persistent_stat('total_pages_processed', 1)
            
        except Exception as e:
            result['error'] = str(e)
            with self.lock:
                self.crawl_stats['errors_count'] += 1
            
            # Update persistent stats
            self._increment_persistent_stat('total_errors', 1)
        
        return result
    
    def start_crawl(self, seed_urls: List[str]) -> str:
        """Start crawling process"""
        with self.lock:
            if self.is_crawling:
                return None
            
            self.is_crawling = True
            self.stop_requested = False
            
            # Reset only current crawl stats, not total stats
            self.crawl_stats = {
                'crawl_id': f"crawl_{int(time.time())}",
                'status': 'running',
                'pages_processed': 0,
                'pages_queued': len(seed_urls),
                'duplicates_found': 0,
                'errors_count': 0,
                'start_time': datetime.now(),
                'elapsed_time': 0
            }
        
        # Increment total crawls started
        self._increment_persistent_stat('total_crawls_started', 1)
        
        # Add seed URLs to frontier
        for url in seed_urls:
            self._make_request(
                'frontier', '/enqueue', 'POST',
                {'url': url, 'priority': 10}
            )
        
        # Start crawl worker in background
        self.crawl_thread = threading.Thread(target=self._crawl_worker)
        self.crawl_thread.daemon = True
        self.crawl_thread.start()
        
        return self.crawl_stats['crawl_id']
    
    def _crawl_worker(self):
        """Background worker for crawling"""
        max_pages = 20  # Reduced limit for demo to prevent infinite crawling
        no_url_count = 0
        max_no_url_attempts = 5  # Reduced attempts to stop sooner
        consecutive_duplicates = 0
        max_consecutive_duplicates = 10  # Stop if too many consecutive duplicates
        
        while not self.stop_requested:
            with self.lock:
                if self.crawl_stats['pages_processed'] >= max_pages:
                    break
            
            # Get URLs from frontier
            frontier_resp = self._make_request('frontier', '/dequeue?count=1', 'GET')
            
            if not frontier_resp.get('urls') or len(frontier_resp['urls']) == 0:
                # No URLs available
                no_url_count += 1
                if no_url_count >= max_no_url_attempts:
                    # No more URLs to process
                    break
                time.sleep(1)
                continue
            
            no_url_count = 0  # Reset counter
            
            # Process each URL
            for url_data in frontier_resp['urls']:
                if self.stop_requested:
                    break
                
                url = url_data['url']
                result = self.process_url(url)
                
                # Track consecutive duplicates to prevent infinite loops
                if result.get('is_duplicate'):
                    consecutive_duplicates += 1
                    if consecutive_duplicates >= max_consecutive_duplicates:
                        print(f"Stopping crawl: {consecutive_duplicates} consecutive duplicates found")
                        self.stop_requested = True
                        break
                else:
                    consecutive_duplicates = 0  # Reset counter on non-duplicate
                
                # Respect crawl delay
                time.sleep(url_data.get('crawl_delay', 1))
        
        # Update status
        with self.lock:
            self.crawl_stats['status'] = 'stopped' if self.stop_requested else 'completed'
            self.is_crawling = False
        
        # Increment completed crawls if not stopped manually
        if not self.stop_requested:
            self._increment_persistent_stat('total_crawls_completed', 1)
    
    def stop_crawl(self):
        """Stop crawling process"""
        with self.lock:
            if not self.is_crawling:
                return False
            
            self.stop_requested = True
            self.crawl_stats['status'] = 'stopping'
        
        # Wait for thread to finish (with timeout)
        if self.crawl_thread:
            self.crawl_thread.join(timeout=5)
        
        with self.lock:
            self.is_crawling = False
            self.crawl_stats['status'] = 'stopped'
        
        return True
    
    def get_service_health(self) -> Dict:
        """Check health of all services"""
        health_status = {}
        
        for service, url in SERVICES.items():
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    health_status[service] = response.json()
                else:
                    health_status[service] = {'status': 'unhealthy', 'error': f"HTTP {response.status_code}"}
            except Exception as e:
                health_status[service] = {'status': 'unhealthy', 'error': str(e)}
        
        return health_status
    
    def get_crawl_stats(self) -> Dict:
        """Get current crawl statistics with persistent total stats"""
        with self.lock:
            # Update queue size from frontier
            frontier_stats = self._make_request('frontier', '/stats', 'GET')
            self.crawl_stats['pages_queued'] = frontier_stats.get('total_in_queue', 0)
            
            # Calculate elapsed time
            if self.crawl_stats['start_time']:
                elapsed = datetime.now() - self.crawl_stats['start_time']
                self.crawl_stats['elapsed_time'] = elapsed.total_seconds()
            
            # Get persistent stats from Redis
            persistent_stats = self._get_persistent_stats()
            
            # Combine current and persistent total stats
            combined_stats = self.crawl_stats.copy()
            combined_stats.update(persistent_stats)
            
            return combined_stats


# Initialize gateway
gateway = APIGateway()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health = ServiceHealth(
        service_name=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        uptime=time.time() - START_TIME,
        version=SERVICE_VERSION,
        metrics={'services': len(SERVICES)}
    )
    return jsonify(health.dict())


@app.route('/services/health', methods=['GET'])
def services_health():
    """Check health of all microservices"""
    return jsonify(gateway.get_service_health())


@app.route('/crawl/start', methods=['POST'])
def start_crawl():
    """Start crawling with seed URLs"""
    try:
        data = request.json
        seed_urls = data.get('seed_urls', [])
        
        if not seed_urls:
            return jsonify({'error': 'No seed URLs provided'}), 400
        
        crawl_id = gateway.start_crawl(seed_urls)
        
        if crawl_id:
            return jsonify({
                'success': True,
                'crawl_id': crawl_id,
                'message': f'Started crawling with {len(seed_urls)} seed URLs'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Crawl already in progress'
            }), 409
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/crawl/stop', methods=['POST'])
def stop_crawl():
    """Stop current crawl"""
    success = gateway.stop_crawl()
    
    if success:
        return jsonify({'success': True, 'message': 'Crawl stopped'})
    else:
        return jsonify({'success': False, 'message': 'No crawl in progress'})


@app.route('/crawl/status', methods=['GET'])
def crawl_status():
    """Get current crawl status with total stats"""
    return jsonify(gateway.get_crawl_stats())


@app.route('/process', methods=['POST'])
def process_single_url():
    """Process a single URL through the pipeline"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        result = gateway.process_url(url)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_all_stats():
    """Get statistics from all services including persistent totals"""
    stats = {}
    
    for service in SERVICES:
        service_stats = gateway._make_request(service, '/stats', 'GET')
        stats[service] = service_stats
    
    # Add gateway persistent total stats
    stats['gateway'] = gateway._get_persistent_stats()
    
    return jsonify(stats)


@app.route('/stats/reset', methods=['POST'])
def reset_stats():
    """Reset persistent total statistics (for testing)"""
    try:
        # Reset persistent stats in Redis
        stats_keys = [
            'crawler:total_pages_processed',
            'crawler:total_duplicates_found', 
            'crawler:total_errors',
            'crawler:total_urls_extracted',
            'crawler:total_crawls_started',
            'crawler:total_crawls_completed'
        ]
        
        for key in stats_keys:
            gateway.redis_client.set(key, 0)
        
        return jsonify({'success': True, 'message': 'Persistent stats reset'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)