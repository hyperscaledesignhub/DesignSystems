"""
Content Parser Microservice
Parses HTML content and extracts text, metadata, and links
"""
import os
import sys
import time
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

# Add shared models to path
sys.path.append('/app/shared')
from models import ParseRequest, ParseResponse, ServiceHealth, ServiceStatus

app = Flask(__name__)
CORS(app)

# Service configuration
SERVICE_NAME = "content-parser"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()


class ContentParserService:
    def __init__(self):
        self.stats = {
            'total_parsed': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'total_links_extracted': 0,
            'average_parse_time': 0
        }
        self._parse_times = []
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters
        text = re.sub(r'[\r\n\t]', ' ', text)
        # Strip leading/trailing whitespace
        return text.strip()
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """Extract metadata from HTML"""
        metadata = {}
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            if meta.get('name'):
                metadata[meta['name']] = meta.get('content', '')
            elif meta.get('property'):
                metadata[meta['property']] = meta.get('content', '')
        
        # Extract other common metadata
        if soup.find('html'):
            metadata['lang'] = soup.find('html').get('lang', '')
        
        # Extract canonical URL
        canonical = soup.find('link', {'rel': 'canonical'})
        if canonical:
            metadata['canonical'] = canonical.get('href', '')
        
        return metadata
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and normalize all links from HTML"""
        links = []
        
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if href:
                # Skip empty or javascript links
                if href.startswith('#') or href.startswith('javascript:'):
                    continue
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Validate URL
                try:
                    parsed = urlparse(absolute_url)
                    if parsed.scheme in ['http', 'https']:
                        links.append(absolute_url)
                except:
                    continue
        
        return list(set(links))  # Remove duplicates
    
    def parse(self, parse_request: ParseRequest) -> ParseResponse:
        """Parse HTML content"""
        start_time = time.time()
        self.stats['total_parsed'] += 1
        
        try:
            # Parse HTML
            soup = BeautifulSoup(parse_request.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Extract title
            title = None
            if soup.title:
                title = self._clean_text(soup.title.string or '')
            
            # Extract text
            text = self._clean_text(soup.get_text())
            
            # Extract links
            links = self._extract_links(soup, parse_request.url)
            
            # Extract metadata if requested
            metadata = {}
            if parse_request.extract_metadata:
                metadata = self._extract_metadata(soup)
            
            # Update parse time
            parse_time = time.time() - start_time
            self._parse_times.append(parse_time)
            
            # Update stats
            self.stats['successful_parses'] += 1
            self.stats['total_links_extracted'] += len(links)
            self.stats['average_parse_time'] = sum(self._parse_times) / len(self._parse_times)
            
            return ParseResponse(
                url=parse_request.url,
                title=title,
                text=text,
                links=links,
                metadata=metadata,
                success=True
            )
            
        except Exception as e:
            self.stats['failed_parses'] += 1
            return ParseResponse(
                url=parse_request.url,
                title=None,
                text="",
                links=[],
                metadata={},
                success=False,
                error=str(e)
            )
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return self.stats.copy()


# Initialize service
parser_service = ContentParserService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health = ServiceHealth(
        service_name=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        uptime=time.time() - START_TIME,
        version=SERVICE_VERSION,
        metrics=parser_service.get_stats()
    )
    return jsonify(health.dict())


@app.route('/parse', methods=['POST'])
def parse_content():
    """Parse HTML content"""
    try:
        data = request.json
        parse_request = ParseRequest(**data)
        response = parser_service.parse(parse_request)
        
        return jsonify(response.dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/parse_batch', methods=['POST'])
def parse_batch():
    """Parse multiple HTML documents"""
    try:
        data = request.json
        documents = data.get('documents', [])
        
        results = []
        for doc in documents:
            parse_request = ParseRequest(**doc)
            response = parser_service.parse(parse_request)
            results.append(response.dict())
        
        successful = sum(1 for r in results if r['success'])
        return jsonify({
            'total': len(documents),
            'successful': successful,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get parser statistics"""
    return jsonify(parser_service.get_stats())


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=False)