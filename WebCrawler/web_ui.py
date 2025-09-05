#!/usr/bin/env python3
"""
Microservices Web UI
A simple web interface to test and monitor the crawler microservices
"""
from flask import Flask, render_template_string, jsonify, request
import requests
import json
import time
from datetime import datetime

app = Flask(__name__)

# Service URLs
SERVICES = {
    'gateway': 'http://localhost:5010',
    'frontier': 'http://localhost:5011',
    'downloader': 'http://localhost:5002',
    'parser': 'http://localhost:5003',
    'deduplication': 'http://localhost:5004'
}

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microservices Crawler Demo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .services-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .service-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .service-status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-healthy { background: #d4edda; color: #155724; }
        .status-unhealthy { background: #f8d7da; color: #721c24; }
        .status-unknown { background: #fff3cd; color: #856404; }
        .test-section { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .input-group { margin: 10px 0; }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .input-group input, .input-group textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .result-box { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 10px; margin-top: 10px; font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
        .logs { background: #000; color: #00ff00; padding: 15px; border-radius: 5px; font-family: monospace; height: 200px; overflow-y: auto; margin-top: 10px; }
        .metric { display: inline-block; margin: 5px 10px; padding: 5px 10px; background: #e9ecef; border-radius: 4px; }
        .metric-value { font-weight: bold; color: #495057; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕷️ Web Crawler Microservices Demo</h1>
            <p>Monitor and test the distributed crawler architecture</p>
        </div>

        <!-- Service Health Status -->
        <div class="test-section">
            <h2>📊 Service Health Monitor</h2>
            <button class="btn btn-primary" onclick="refreshHealth()">🔄 Refresh Status</button>
            <div class="services-grid" id="servicesGrid">
                <!-- Services will be loaded here -->
            </div>
        </div>

        <!-- URL Processing Test -->
        <div class="test-section">
            <h2>🔍 Single URL Processing</h2>
            <div class="input-group">
                <label>URL to Process:</label>
                <input type="url" id="testUrl" value="https://httpbin.org/html" placeholder="Enter URL to test">
            </div>
            <button class="btn btn-success" onclick="processUrl()">🚀 Process URL</button>
            <div id="urlResult" class="result-box" style="display:none;"></div>
        </div>

        <!-- Batch Crawl Test -->
        <div class="test-section">
            <h2>🔄 Start Crawl Session</h2>
            <div class="input-group">
                <label>Seed URLs (one per line):</label>
                <textarea id="seedUrls" rows="3">https://httpbin.org/html
https://httpbin.org/links/3</textarea>
            </div>
            <button class="btn btn-success" onclick="startCrawl()">🚀 Start Crawl</button>
            <button class="btn btn-danger" onclick="stopCrawl()">⏹️ Stop Crawl</button>
            <div id="crawlResult" class="result-box" style="display:none;"></div>
            
            <h3>Crawl Status</h3>
            <div id="crawlStatus">
                <div class="metric">Status: <span class="metric-value" id="statusValue">Idle</span></div>
                <div class="metric">Processed: <span class="metric-value" id="processedValue">0</span></div>
                <div class="metric">Queued: <span class="metric-value" id="queuedValue">0</span></div>
                <div class="metric">Errors: <span class="metric-value" id="errorsValue">0</span></div>
            </div>
        </div>

        <!-- Individual Service Tests -->
        <div class="test-section">
            <h2>🧪 Individual Service Tests</h2>
            
            <h3>URL Frontier Service</h3>
            <button class="btn btn-primary" onclick="testFrontier()">Test Frontier</button>
            <div id="frontierResult" class="result-box" style="display:none;"></div>

            <h3>HTML Downloader Service</h3>
            <button class="btn btn-primary" onclick="testDownloader()">Test Downloader</button>
            <div id="downloaderResult" class="result-box" style="display:none;"></div>

            <h3>Content Parser Service</h3>
            <button class="btn btn-primary" onclick="testParser()">Test Parser</button>
            <div id="parserResult" class="result-box" style="display:none;"></div>

            <h3>Deduplication Service</h3>
            <button class="btn btn-primary" onclick="testDeduplication()">Test Deduplication</button>
            <div id="deduplicationResult" class="result-box" style="display:none;"></div>
        </div>

        <!-- Activity Logs -->
        <div class="test-section">
            <h2>📝 Activity Logs</h2>
            <div id="activityLogs" class="logs">Starting microservices monitor...\n</div>
        </div>
    </div>

    <script>
        // Auto-refresh health status every 10 seconds
        setInterval(refreshHealth, 10000);
        setInterval(updateCrawlStatus, 5000);
        
        // Initial load
        refreshHealth();
        
        function log(message) {
            const logs = document.getElementById('activityLogs');
            const timestamp = new Date().toLocaleTimeString();
            logs.textContent += `[${timestamp}] ${message}\n`;
            logs.scrollTop = logs.scrollHeight;
        }

        async function refreshHealth() {
            log('Refreshing service health status...');
            const grid = document.getElementById('servicesGrid');
            
            const services = ['gateway', 'frontier', 'downloader', 'parser', 'deduplication'];
            grid.innerHTML = '';

            for (const service of services) {
                const card = document.createElement('div');
                card.className = 'service-card';
                
                try {
                    const response = await fetch(`/api/health/${service}`);
                    const data = await response.json();
                    
                    const status = data.status === 'healthy' ? 'status-healthy' : 'status-unhealthy';
                    const port = {gateway: 5010, frontier: 5011, downloader: 5002, parser: 5003, deduplication: 5004}[service];
                    
                    card.innerHTML = `
                        <h3>${service.charAt(0).toUpperCase() + service.slice(1)}</h3>
                        <div class="service-status ${status}">${data.status || 'Unknown'}</div>
                        <p><strong>Port:</strong> ${port}</p>
                        <p><strong>Uptime:</strong> ${data.uptime ? Math.round(data.uptime) + 's' : 'N/A'}</p>
                        <p><strong>Version:</strong> ${data.version || 'N/A'}</p>
                        ${data.metrics ? '<p><strong>Metrics:</strong> ' + JSON.stringify(data.metrics) + '</p>' : ''}
                    `;
                } catch (error) {
                    card.innerHTML = `
                        <h3>${service.charAt(0).toUpperCase() + service.slice(1)}</h3>
                        <div class="service-status status-unhealthy">Unreachable</div>
                        <p>Error: ${error.message}</p>
                    `;
                }
                
                grid.appendChild(card);
            }
        }

        async function processUrl() {
            const url = document.getElementById('testUrl').value;
            if (!url) return alert('Please enter a URL');
            
            log(`Processing URL: ${url}`);
            const resultDiv = document.getElementById('urlResult');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Processing...';
            
            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                log(`URL processing ${data.success ? 'completed successfully' : 'failed'}`);
            } catch (error) {
                resultDiv.textContent = `Error: ${error.message}`;
                log(`URL processing failed: ${error.message}`);
            }
        }

        async function startCrawl() {
            const seedUrls = document.getElementById('seedUrls').value.split('\\n').filter(url => url.trim());
            if (seedUrls.length === 0) return alert('Please enter seed URLs');
            
            log(`Starting crawl with ${seedUrls.length} seed URLs`);
            const resultDiv = document.getElementById('crawlResult');
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Starting crawl...';
            
            try {
                const response = await fetch('/api/crawl/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({seed_urls: seedUrls})
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                log(`Crawl ${data.success ? 'started successfully' : 'failed to start'}`);
            } catch (error) {
                resultDiv.textContent = `Error: ${error.message}`;
                log(`Crawl start failed: ${error.message}`);
            }
        }

        async function stopCrawl() {
            log('Stopping crawl...');
            try {
                const response = await fetch('/api/crawl/stop', {method: 'POST'});
                const data = await response.json();
                log(`Crawl ${data.success ? 'stopped' : 'stop failed'}`);
            } catch (error) {
                log(`Crawl stop failed: ${error.message}`);
            }
        }

        async function updateCrawlStatus() {
            try {
                const response = await fetch('/api/crawl/status');
                const data = await response.json();
                
                document.getElementById('statusValue').textContent = data.status || 'Unknown';
                document.getElementById('processedValue').textContent = data.pages_processed || 0;
                document.getElementById('queuedValue').textContent = data.pages_queued || 0;
                document.getElementById('errorsValue').textContent = data.errors_count || 0;
            } catch (error) {
                // Silently fail for status updates
            }
        }

        async function testFrontier() {
            log('Testing Frontier service...');
            const resultDiv = document.getElementById('frontierResult');
            resultDiv.style.display = 'block';
            
            try {
                // Test enqueue
                const enqueueResponse = await fetch('/api/test/frontier', {method: 'POST'});
                const data = await enqueueResponse.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                log('Frontier test completed');
            } catch (error) {
                resultDiv.textContent = `Error: ${error.message}`;
                log(`Frontier test failed: ${error.message}`);
            }
        }

        async function testDownloader() {
            log('Testing Downloader service...');
            const resultDiv = document.getElementById('downloaderResult');
            resultDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/test/downloader', {method: 'POST'});
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                log('Downloader test completed');
            } catch (error) {
                resultDiv.textContent = `Error: ${error.message}`;
                log(`Downloader test failed: ${error.message}`);
            }
        }

        async function testParser() {
            log('Testing Parser service...');
            const resultDiv = document.getElementById('parserResult');
            resultDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/test/parser', {method: 'POST'});
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                log('Parser test completed');
            } catch (error) {
                resultDiv.textContent = `Error: ${error.message}`;
                log(`Parser test failed: ${error.message}`);
            }
        }

        async function testDeduplication() {
            log('Testing Deduplication service...');
            const resultDiv = document.getElementById('deduplicationResult');
            resultDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/test/deduplication', {method: 'POST'});
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                log('Deduplication test completed');
            } catch (error) {
                resultDiv.textContent = `Error: ${error.message}`;
                log(`Deduplication test failed: ${error.message}`);
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/health/<service>')
def check_service_health(service):
    """Check individual service health"""
    if service not in SERVICES:
        return jsonify({'error': 'Unknown service'}), 404
    
    try:
        response = requests.get(f'{SERVICES[service]}/health', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {'status': 'unhealthy', 'error': f'HTTP {response.status_code}'}
    except requests.exceptions.ConnectionError:
        return {'status': 'unreachable', 'error': 'Connection refused'}
    except requests.exceptions.Timeout:
        return {'status': 'timeout', 'error': 'Request timeout'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

@app.route('/api/process', methods=['POST'])
def process_url():
    """Process a single URL through the pipeline"""
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # Try gateway first
        try:
            response = requests.post(f'{SERVICES["gateway"]}/process', 
                                   json={'url': url}, timeout=30)
            return response.json()
        except:
            # Fallback: manually process through services
            result = {'url': url, 'steps': {}}
            
            # Step 1: Download
            download_resp = requests.post(f'{SERVICES["downloader"]}/download',
                                        json={'url': url}, timeout=15)
            result['steps']['download'] = download_resp.json()
            
            if download_resp.status_code == 200 and download_resp.json().get('success'):
                content = download_resp.json()['content']
                
                # Step 2: Parse
                parse_resp = requests.post(f'{SERVICES["parser"]}/parse',
                                         json={'url': url, 'content': content}, timeout=10)
                result['steps']['parse'] = parse_resp.json()
                
                # Step 3: Deduplication
                if parse_resp.status_code == 200 and parse_resp.json().get('success'):
                    text = parse_resp.json().get('text', '')
                    dedup_resp = requests.post(f'{SERVICES["deduplication"]}/check',
                                             json={'url': url, 'content': text}, timeout=10)
                    result['steps']['deduplication'] = dedup_resp.json()
            
            result['success'] = True
            return jsonify(result)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawl/start', methods=['POST'])
def start_crawl():
    """Start crawling process"""
    try:
        data = request.json
        response = requests.post(f'{SERVICES["gateway"]}/crawl/start', 
                               json=data, timeout=10)
        return response.json()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawl/stop', methods=['POST'])
def stop_crawl():
    """Stop crawling process"""
    try:
        response = requests.post(f'{SERVICES["gateway"]}/crawl/stop', timeout=10)
        return response.json()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawl/status')
def crawl_status():
    """Get crawl status"""
    try:
        response = requests.get(f'{SERVICES["gateway"]}/crawl/status', timeout=5)
        return response.json()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/frontier', methods=['POST'])
def test_frontier():
    """Test frontier service"""
    try:
        # Test enqueue
        test_url = f"https://httpbin.org/html?test={int(time.time())}"
        enqueue_resp = requests.post(f'{SERVICES["frontier"]}/enqueue',
                                   json={'url': test_url, 'priority': 5}, timeout=5)
        
        # Test dequeue
        dequeue_resp = requests.get(f'{SERVICES["frontier"]}/dequeue?count=1', timeout=5)
        
        return jsonify({
            'enqueue': enqueue_resp.json(),
            'dequeue': dequeue_resp.json()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/downloader', methods=['POST'])
def test_downloader():
    """Test downloader service"""
    try:
        response = requests.post(f'{SERVICES["downloader"]}/download',
                               json={'url': 'https://httpbin.org/html'}, timeout=15)
        data = response.json()
        # Truncate content for display
        if 'content' in data and len(data['content']) > 500:
            data['content'] = data['content'][:500] + '...[truncated]'
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/parser', methods=['POST'])
def test_parser():
    """Test parser service"""
    try:
        test_html = "<html><head><title>Test</title></head><body><h1>Hello</h1><p>Test content</p><a href='http://example.com'>Link</a></body></html>"
        response = requests.post(f'{SERVICES["parser"]}/parse',
                               json={'url': 'http://test.com', 'content': test_html}, timeout=10)
        return response.json()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/deduplication', methods=['POST'])
def test_deduplication():
    """Test deduplication service"""
    try:
        test_content = f"This is test content generated at {datetime.now()}"
        response = requests.post(f'{SERVICES["deduplication"]}/check',
                               json={'url': 'http://test.com', 'content': test_content}, timeout=10)
        return response.json()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌐 Starting Microservices Web UI...")
    print("📊 Dashboard available at: http://localhost:8080")
    print("🔧 Testing all microservices endpoints")
    app.run(host='0.0.0.0', port=8080, debug=False)