"""
Content Deduplication Microservice
Detects and manages duplicate content using hashing and similarity algorithms
"""
import os
import sys
import time
import hashlib
import redis
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, List

# Add shared models to path
sys.path.append('/app/shared')
from models import DeduplicationRequest, DeduplicationResponse, ServiceHealth, ServiceStatus

app = Flask(__name__)
CORS(app)

# Redis connection
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Service configuration
SERVICE_NAME = "content-deduplication"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()


class DeduplicationService:
    def __init__(self):
        self.stats = {
            'total_checks': 0,
            'duplicates_found': 0,
            'unique_content': 0,
            'total_hashes': 0
        }
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _calculate_simhash(self, content: str) -> str:
        """Simple simhash implementation for similarity detection"""
        # Simplified version - in production use proper simhash library
        words = content.lower().split()
        hash_bits = [0] * 64
        
        for word in words:
            word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(64):
                if word_hash & (1 << i):
                    hash_bits[i] += 1
                else:
                    hash_bits[i] -= 1
        
        simhash = 0
        for i in range(64):
            if hash_bits[i] > 0:
                simhash |= (1 << i)
        
        return hex(simhash)
    
    def check_duplicate(self, dedup_request: DeduplicationRequest) -> DeduplicationResponse:
        """Check if content is duplicate"""
        self.stats['total_checks'] += 1
        
        # Calculate content hash
        content_hash = dedup_request.content_hash or self._calculate_hash(dedup_request.content)
        
        # Check if exact duplicate exists
        hash_key = f"dedup:hash:{content_hash}"
        existing_urls = redis_client.smembers(hash_key)
        
        is_duplicate = len(existing_urls) > 0
        
        if is_duplicate:
            self.stats['duplicates_found'] += 1
            similar_urls = list(existing_urls)[:10]  # Return max 10 similar URLs
        else:
            self.stats['unique_content'] += 1
            similar_urls = []
            # Add this URL to the hash set
            redis_client.sadd(hash_key, dedup_request.url)
        
        # Calculate similarity hash for near-duplicate detection
        simhash = self._calculate_simhash(dedup_request.content)
        simhash_key = f"dedup:simhash:{simhash[:16]}"  # Use prefix for bucketing
        
        # Store simhash mapping
        redis_client.hset(f"dedup:url_simhash", dedup_request.url, simhash)
        redis_client.sadd(simhash_key, dedup_request.url)
        
        self.stats['total_hashes'] = redis_client.dbsize()
        
        return DeduplicationResponse(
            is_duplicate=is_duplicate,
            content_hash=content_hash,
            similarity_score=1.0 if is_duplicate else 0.0,
            similar_urls=similar_urls
        )
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return self.stats.copy()


# Initialize service
dedup_service = DeduplicationService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health = ServiceHealth(
        service_name=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        uptime=time.time() - START_TIME,
        version=SERVICE_VERSION,
        metrics=dedup_service.get_stats()
    )
    return jsonify(health.dict())


@app.route('/check', methods=['POST'])
def check_duplicate():
    """Check if content is duplicate"""
    try:
        data = request.json
        dedup_request = DeduplicationRequest(**data)
        response = dedup_service.check_duplicate(dedup_request)
        
        return jsonify(response.dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/check_batch', methods=['POST'])
def check_batch():
    """Check multiple contents for duplicates"""
    try:
        data = request.json
        contents = data.get('contents', [])
        
        results = []
        for content_data in contents:
            dedup_request = DeduplicationRequest(**content_data)
            response = dedup_service.check_duplicate(dedup_request)
            results.append(response.dict())
        
        duplicates = sum(1 for r in results if r['is_duplicate'])
        return jsonify({
            'total': len(contents),
            'duplicates': duplicates,
            'unique': len(contents) - duplicates,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get deduplication statistics"""
    return jsonify(dedup_service.get_stats())


@app.route('/clear', methods=['POST'])
def clear_dedup_data():
    """Clear deduplication data (for testing)"""
    try:
        # Clear all dedup keys
        for key in redis_client.scan_iter('dedup:*'):
            redis_client.delete(key)
        
        # Reset stats
        dedup_service.stats = {
            'total_checks': 0,
            'duplicates_found': 0,
            'unique_content': 0,
            'total_hashes': 0
        }
        
        return jsonify({'success': True, 'message': 'Deduplication data cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=False)