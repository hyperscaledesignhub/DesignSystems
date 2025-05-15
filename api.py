from flask import Flask, request, jsonify
from flask_cors import CORS
from app import RateLimiterFactory, load_config
import os
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load configuration
config = load_config()
rate_limiter_config = config['rate_limiter']

# Create Redis client
redis_client = RateLimiterFactory.create_redis_client()

# Create rate limiter with proper parameters
rate_limiter = RateLimiterFactory.create_rate_limiter(
    algorithm=rate_limiter_config['algorithm'],
    redis_client=redis_client,
    max_requests=rate_limiter_config['max_requests'],
    algorithm_config=rate_limiter_config['algorithms'][rate_limiter_config['algorithm']]
)

print(f"Using {rate_limiter_config['algorithm'].replace('_', ' ').title()} Rate Limiter")

@app.route('/api/limited')
def limited_endpoint():
    """Rate limited API endpoint."""
    # Get client identifier from custom header or fallback to IP
    client_id = request.headers.get('X-Client-ID')
    if client_id:
        # If X-Client-ID is present, use it directly
        logger.info(f"Using X-Client-ID header: {client_id}")
    else:
        # Fallback to IP address
        client_id = request.remote_addr
        if 'X-Forwarded-For' in request.headers:
            client_id = request.headers['X-Forwarded-For'].split(',')[0].strip()
        logger.info(f"Using IP address as client_id: {client_id}")
    
    logger.info(f"Headers: {dict(request.headers)}")
    
    rate_limit_method = RateLimiterFactory.get_rate_limit_method(rate_limiter)
    allowed, remaining, reset_time = rate_limit_method(client_id)
    
    logger.info(f"Rate limit decision for {client_id}: allowed={allowed}, remaining={remaining}")
    
    if not allowed:
        return jsonify({
            'error': 'Rate limit exceeded',
            'remaining': remaining,
            'reset_time': reset_time
        }), 429
    
    return jsonify({
        'message': 'Request processed successfully',
        'remaining': remaining,
        'reset_time': reset_time
    })

@app.route('/api/unlimited', methods=['GET'])
def unlimited_endpoint():
    """Unlimited API endpoint for comparison."""
    return jsonify({'message': 'Unlimited request processed'}), 200

if __name__ == '__main__':
    # Force port 5001 and disable reloader
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False) 