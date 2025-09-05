"""
URL Extractor Service
Extracts and filters URLs from HTML content for continued crawling
"""
import os
import sys
import time
import re
from urllib.parse import urljoin, urlparse, urlunparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Set

# Add shared models to path
sys.path.append('/app/shared')
from models import ServiceHealth, ServiceStatus

app = Flask(__name__)
CORS(app)

# Service configuration
SERVICE_NAME = "url-extractor"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()

class URLExtractor:
    def __init__(self):
        self.stats = {
            'urls_extracted': 0,
            'pages_processed': 0,
            'invalid_urls_filtered': 0,
            'duplicate_urls_filtered': 0
        }
        
        # URL filtering patterns
        self.exclude_extensions = {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.jpg', '.jpeg', '.png', 
            '.gif', '.bmp', '.svg', '.ico', '.css', '.js', '.xml',
            '.json', '.rss', '.atom'
        }
        
        # Common URL patterns to exclude
        self.exclude_patterns = [
            r'mailto:',
            r'javascript:',
            r'tel:',
            r'ftp:',
            r'#',
            r'\?.*print.*',  # Print versions
            r'.*\.(pdf|doc|zip|jpg|png|gif|css|js)$',  # File extensions
        ]
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and should be crawled"""
        try:
            # Basic URL validation
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Only HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check file extensions
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in self.exclude_extensions):
                return False
            
            # Check exclude patterns
            for pattern in self.exclude_patterns:
                if re.search(pattern, url.lower()):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and unnecessary parameters"""
        try:
            parsed = urlparse(url)
            # Remove fragment (everything after #)
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                None  # Remove fragment
            ))
            
            # Remove trailing slash for consistency (except for root)
            if normalized.endswith('/') and len(parsed.path) > 1:
                normalized = normalized[:-1]
                
            return normalized
        except Exception:
            return url
    
    def extract_urls_from_html(self, html_content: str, base_url: str) -> List[str]:
        """Extract URLs from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            urls = set()
            
            # Extract from different HTML elements
            for element in soup.find_all(['a', 'link']):
                href = element.get('href')
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, href)
                    
                    # Validate and normalize
                    if self.is_valid_url(absolute_url):
                        normalized = self.normalize_url(absolute_url)
                        urls.add(normalized)
            
            # Filter to same domain only (for focused crawling)
            base_domain = urlparse(base_url).netloc
            filtered_urls = []
            
            for url in urls:
                url_domain = urlparse(url).netloc
                if url_domain == base_domain:
                    filtered_urls.append(url)
            
            return filtered_urls
            
        except Exception as e:
            print(f"Error extracting URLs: {e}")
            return []
    
    def extract_urls(self, url: str, html_content: str, max_urls: int = 50) -> Dict:
        """Main URL extraction logic"""
        try:
            self.stats['pages_processed'] += 1
            
            # Extract URLs
            extracted_urls = self.extract_urls_from_html(html_content, url)
            
            # Limit number of URLs to prevent overwhelming
            if len(extracted_urls) > max_urls:
                extracted_urls = extracted_urls[:max_urls]
            
            self.stats['urls_extracted'] += len(extracted_urls)
            
            return {
                'success': True,
                'url': url,
                'extracted_urls': extracted_urls,
                'count': len(extracted_urls),
                'base_domain': urlparse(url).netloc,
                'processing_time': time.time()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'extracted_urls': [],
                'count': 0
            }

# Initialize extractor
extractor = URLExtractor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health = ServiceHealth(
        service_name=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        uptime=time.time() - START_TIME,
        version=SERVICE_VERSION,
        metrics=extractor.stats
    )
    return jsonify(health.dict())

@app.route('/extract', methods=['POST'])
def extract_urls():
    """Extract URLs from HTML content"""
    try:
        data = request.json
        url = data.get('url')
        html_content = data.get('html_content')
        max_urls = data.get('max_urls', 50)
        
        if not url or not html_content:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: url and html_content'
            }), 400
        
        result = extractor.extract_urls(url, html_content, max_urls)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics"""
    return jsonify({
        'service': SERVICE_NAME,
        'stats': extractor.stats,
        'uptime': time.time() - START_TIME
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5005))
    print(f"🔗 Starting URL Extractor Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)