"""
HTML Downloader Microservice
Handles HTTP requests with retries, rate limiting, and caching
"""
import os
import sys
import time
import requests
import redis
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from typing import Dict, Optional
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Add shared models to path
sys.path.append('/app/shared')
from models import DownloadRequest, DownloadResponse, ServiceHealth, ServiceStatus

app = Flask(__name__)
CORS(app)

# Redis connection for caching
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Service configuration
SERVICE_NAME = "html-downloader"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()

# Downloader configuration
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
CACHE_TTL = 3600  # 1 hour
USER_AGENT = "Mozilla/5.0 (compatible; WebCrawler/1.0)"


class HTMLDownloaderService:
    def __init__(self):
        self.session = self._create_session()
        self.stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'cache_hits': 0,
            'total_bytes': 0,
            'average_download_time': 0
        }
        self._download_times = []
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=DEFAULT_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return session
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return f"cache:html:{hashlib.md5(url.encode()).hexdigest()}"
    
    def _get_from_cache(self, url: str) -> Optional[Dict]:
        """Get cached content if available"""
        try:
            cache_key = self._get_cache_key(url)
            cached_data = redis_client.get(cache_key)
            if cached_data:
                import json
                self.stats['cache_hits'] += 1
                return json.loads(cached_data)
        except Exception as e:
            app.logger.error(f"Cache retrieval error: {e}")
        return None
    
    def _save_to_cache(self, url: str, response_data: Dict):
        """Save content to cache"""
        try:
            cache_key = self._get_cache_key(url)
            import json
            redis_client.setex(
                cache_key,
                CACHE_TTL,
                json.dumps(response_data)
            )
        except Exception as e:
            app.logger.error(f"Cache save error: {e}")
    
    def download(self, download_request: DownloadRequest) -> DownloadResponse:
        """Download content from URL"""
        url = download_request.url
        
        # Check cache first
        cached = self._get_from_cache(url)
        if cached:
            return DownloadResponse(**cached)
        
        start_time = time.time()
        self.stats['total_downloads'] += 1
        
        try:
            # Prepare headers
            headers = self.session.headers.copy()
            if download_request.headers:
                headers.update(download_request.headers)
            
            # Make request
            response = self.session.get(
                url,
                headers=headers,
                timeout=download_request.timeout,
                allow_redirects=True
            )
            
            download_time = time.time() - start_time
            self._download_times.append(download_time)
            
            # Update stats
            self.stats['successful_downloads'] += 1
            self.stats['total_bytes'] += len(response.content)
            self.stats['average_download_time'] = sum(self._download_times) / len(self._download_times)
            
            # Create response
            download_response = DownloadResponse(
                url=url,
                content=response.text,
                status_code=response.status_code,
                headers=dict(response.headers),
                download_time=download_time,
                success=True
            )
            
            # Cache successful downloads
            if response.status_code == 200:
                self._save_to_cache(url, download_response.dict())
            
            return download_response
            
        except requests.exceptions.Timeout:
            self.stats['failed_downloads'] += 1
            return DownloadResponse(
                url=url,
                content="",
                status_code=0,
                headers={},
                download_time=time.time() - start_time,
                success=False,
                error="Request timeout"
            )
        except requests.exceptions.RequestException as e:
            self.stats['failed_downloads'] += 1
            return DownloadResponse(
                url=url,
                content="",
                status_code=0,
                headers={},
                download_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
        except Exception as e:
            self.stats['failed_downloads'] += 1
            return DownloadResponse(
                url=url,
                content="",
                status_code=0,
                headers={},
                download_time=time.time() - start_time,
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return self.stats.copy()


# Initialize service
downloader_service = HTMLDownloaderService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health = ServiceHealth(
        service_name=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        uptime=time.time() - START_TIME,
        version=SERVICE_VERSION,
        metrics=downloader_service.get_stats()
    )
    return jsonify(health.dict())


@app.route('/download', methods=['POST'])
def download_page():
    """Download content from URL"""
    try:
        data = request.json
        download_request = DownloadRequest(**data)
        response = downloader_service.download(download_request)
        
        return jsonify(response.dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/download_batch', methods=['POST'])
def download_batch():
    """Download multiple URLs"""
    try:
        data = request.json
        urls = data.get('urls', [])
        
        results = []
        for url_data in urls:
            if isinstance(url_data, str):
                download_request = DownloadRequest(url=url_data)
            else:
                download_request = DownloadRequest(**url_data)
            
            response = downloader_service.download(download_request)
            results.append(response.dict())
        
        successful = sum(1 for r in results if r['success'])
        return jsonify({
            'total': len(urls),
            'successful': successful,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get downloader statistics"""
    return jsonify(downloader_service.get_stats())


@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    """Clear download cache"""
    try:
        # Clear all cache keys
        for key in redis_client.scan_iter('cache:html:*'):
            redis_client.delete(key)
        
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)