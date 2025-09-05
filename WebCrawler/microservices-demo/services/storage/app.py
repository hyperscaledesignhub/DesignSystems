"""
Content Storage Service
Stores crawled content with metadata for retrieval and analysis
"""
import os
import sys
import time
import json
import hashlib
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, List, Optional

# Add shared models to path
sys.path.append('/app/shared')
from models import ServiceHealth, ServiceStatus

app = Flask(__name__)
CORS(app)

# Service configuration
SERVICE_NAME = "content-storage"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()

class ContentStorage:
    def __init__(self):
        # Storage configuration
        self.storage_path = Path(os.getenv('STORAGE_PATH', '/app/data'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage directories
        (self.storage_path / 'content').mkdir(exist_ok=True)
        (self.storage_path / 'metadata').mkdir(exist_ok=True)
        (self.storage_path / 'index').mkdir(exist_ok=True)
        
        self.stats = {
            'documents_stored': 0,
            'total_bytes_stored': 0,
            'storage_errors': 0,
            'duplicate_documents': 0,
            'last_stored': None
        }
        
        # Load existing index
        self.index_file = self.storage_path / 'index' / 'content_index.json'
        self.content_index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load existing content index"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading index: {e}")
        return {}
    
    def _save_index(self):
        """Save content index"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.content_index, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _generate_file_path(self, url: str, content_hash: str) -> Path:
        """Generate file path for storing content"""
        # Use hash prefix for directory structure (better distribution)
        dir_name = content_hash[:2]
        content_dir = self.storage_path / 'content' / dir_name
        content_dir.mkdir(exist_ok=True)
        
        # Use hash as filename to avoid filesystem issues with URLs
        return content_dir / f"{content_hash}.json"
    
    def store_content(self, url: str, content: str, metadata: Dict = None) -> Dict:
        """Store crawled content with metadata"""
        try:
            timestamp = datetime.utcnow()
            content_hash = self._generate_content_hash(content)
            
            # Check for duplicates
            if content_hash in self.content_index:
                self.stats['duplicate_documents'] += 1
                return {
                    'success': True,
                    'stored': False,
                    'reason': 'duplicate_content',
                    'content_hash': content_hash,
                    'original_url': self.content_index[content_hash]['url'],
                    'timestamp': timestamp
                }
            
            # Prepare document
            document = {
                'url': url,
                'content': content,
                'content_hash': content_hash,
                'metadata': metadata or {},
                'stored_at': timestamp,
                'content_length': len(content),
                'service_version': SERVICE_VERSION
            }
            
            # Generate file path
            file_path = self._generate_file_path(url, content_hash)
            
            # Store content
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, indent=2, default=str, ensure_ascii=False)
            
            # Update index
            self.content_index[content_hash] = {
                'url': url,
                'file_path': str(file_path),
                'stored_at': timestamp,
                'content_length': len(content),
                'metadata': metadata or {}
            }
            
            # Update stats
            self.stats['documents_stored'] += 1
            self.stats['total_bytes_stored'] += len(content)
            self.stats['last_stored'] = timestamp
            
            # Save index periodically (every 10 documents or on demand)
            if self.stats['documents_stored'] % 10 == 0:
                self._save_index()
            
            return {
                'success': True,
                'stored': True,
                'content_hash': content_hash,
                'file_path': str(file_path),
                'document_id': content_hash,
                'timestamp': timestamp,
                'content_length': len(content)
            }
            
        except Exception as e:
            self.stats['storage_errors'] += 1
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'timestamp': datetime.utcnow()
            }
    
    def retrieve_content(self, content_hash: str) -> Optional[Dict]:
        """Retrieve stored content by hash"""
        try:
            if content_hash not in self.content_index:
                return None
            
            file_path = Path(self.content_index[content_hash]['file_path'])
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"Error retrieving content: {e}")
            return None
    
    def search_by_url(self, url: str) -> Optional[Dict]:
        """Search for content by URL"""
        for content_hash, info in self.content_index.items():
            if info['url'] == url:
                return self.retrieve_content(content_hash)
        return None
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        return {
            **self.stats,
            'total_documents': len(self.content_index),
            'storage_path': str(self.storage_path),
            'index_size': len(self.content_index)
        }

# Initialize storage
storage = ContentStorage()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health = ServiceHealth(
        service_name=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        uptime=time.time() - START_TIME,
        version=SERVICE_VERSION,
        metrics=storage.get_storage_stats()
    )
    return jsonify(health.dict())

@app.route('/store', methods=['POST'])
def store_content():
    """Store crawled content"""
    try:
        data = request.json
        url = data.get('url')
        content = data.get('content')
        metadata = data.get('metadata', {})
        
        if not url or not content:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: url and content'
            }), 400
        
        result = storage.store_content(url, content, metadata)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/retrieve/<content_hash>', methods=['GET'])
def retrieve_content(content_hash):
    """Retrieve content by hash"""
    try:
        content = storage.retrieve_content(content_hash)
        if content:
            return jsonify({
                'success': True,
                'content': content
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Content not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/search', methods=['POST'])
def search_content():
    """Search for content by URL"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'Missing required field: url'
            }), 400
        
        content = storage.search_by_url(url)
        if content:
            return jsonify({
                'success': True,
                'content': content
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Content not found for URL'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get storage service statistics"""
    return jsonify({
        'service': SERVICE_NAME,
        'stats': storage.get_storage_stats(),
        'uptime': time.time() - START_TIME
    })

@app.route('/index', methods=['GET'])
def get_index():
    """Get content index (for debugging/admin)"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        # Return limited index for performance
        limited_index = dict(list(storage.content_index.items())[:limit])
        
        return jsonify({
            'success': True,
            'index': limited_index,
            'total_entries': len(storage.content_index),
            'showing': len(limited_index)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5006))
    print(f"💾 Starting Content Storage Service on port {port}")
    print(f"📁 Storage path: {storage.storage_path}")
    app.run(host='0.0.0.0', port=port, debug=False)