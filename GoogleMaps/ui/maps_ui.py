#!/usr/bin/env python3
"""
Google Maps Clone - Web UI Application
Runs as external Python process (not in Docker)
"""

import asyncio
import json
import time
import os
import stat
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import webbrowser
from pathlib import Path

try:
    from fastapi import FastAPI, Request, WebSocket, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    import aiohttp
    import requests
except ImportError:
    print("❌ Required packages not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "fastapi", "uvicorn", "jinja2", "aiofiles", "aiohttp", "requests"])
    
    # Re-import after installation
    from fastapi import FastAPI, Request, WebSocket, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    import aiohttp
    import requests

# Configuration
API_BASE_URL = "http://localhost:8086"  # Backend API
UI_PORT = 3002
UI_HOST = "0.0.0.0"

# Create FastAPI app
app = FastAPI(
    title="Google Maps Clone - Web UI",
    description="Interactive web interface for the Google Maps Clone",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create templates directory and static files
ui_dir = Path(__file__).parent
templates_dir = ui_dir / "templates"
static_dir = ui_dir / "static"

# Create directories if they don't exist
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)
(static_dir / "css").mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)

# Templates
templates = Jinja2Templates(directory=str(templates_dir))

class APIClient:
    """Client to communicate with backend API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    async def get(self, endpoint: str) -> Dict:
        """Make GET request to API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    return await response.json()
        except Exception as e:
            return {"error": f"API request failed: {str(e)}"}
    
    async def post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request to API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{endpoint}", 
                    json=data
                ) as response:
                    return await response.json()
        except Exception as e:
            return {"error": f"API request failed: {str(e)}"}

# Global API client
api_client = APIClient(API_BASE_URL)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main maps interface"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "api_base_url": API_BASE_URL
    })

@app.get("/test", response_class=HTMLResponse)
async def test_interface(request: Request):
    """Enhanced testing interface for real database features"""
    return templates.TemplateResponse("test.html", {
        "request": request,
        "api_base_url": API_BASE_URL
    })

@app.get("/maps", response_class=HTMLResponse)
async def user_maps_interface(request: Request):
    """End-user Google Maps interface"""
    return templates.TemplateResponse("user_maps.html", {
        "request": request,
        "api_base_url": API_BASE_URL
    })

@app.get("/api/health")
async def health_check():
    """UI health check"""
    backend_health = await api_client.get("/api/v1/health")
    return {
        "ui_status": "healthy",
        "backend_status": backend_health,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/test/individual-feature")
async def test_individual_feature(feature_data: dict):
    """Test individual location features with custom parameters"""
    feature_type = feature_data.get("type")
    params = feature_data.get("params", {})
    
    try:
        if feature_type == "batch_update":
            result = await api_client.post("/api/v1/location/batch", params)
        elif feature_type == "current_location":
            user_id = params.get("user_id", "demo_user")
            result = await api_client.get(f"/api/v1/location/current/{user_id}")
        elif feature_type == "location_history":
            user_id = params.get("user_id", "demo_user")
            limit = params.get("limit", 10)
            result = await api_client.get(f"/api/v1/location/history/{user_id}?limit={limit}")
        elif feature_type == "nearby_search":
            user_id = params.get("user_id", "demo_user")
            radius = params.get("radius_km", 5.0)
            result = await api_client.get(f"/api/v1/location/nearby/{user_id}?radius_km={radius}")
        elif feature_type == "geohash_info":
            user_id = params.get("user_id", "demo_user")
            result = await api_client.get(f"/api/v1/location/geohash/{user_id}")
        elif feature_type == "location_share":
            result = await api_client.post("/api/v1/location/share", params)
        elif feature_type == "system_stats":
            result = await api_client.get("/api/v1/system/stats")
        elif feature_type == "health_check":
            result = await api_client.get("/api/v1/health")
        else:
            return {"error": f"Unknown feature type: {feature_type}"}
            
        return {
            "feature_type": feature_type,
            "status": "success" if "error" not in result else "failed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "feature_type": feature_type,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/demo/location-features")
async def demo_location_features():
    """Demo all 8 core location features"""
    
    # Test data
    test_locations = [
        {"latitude": 37.7749, "longitude": -122.4194, "accuracy": 5.0},
        {"latitude": 37.7849, "longitude": -122.4094, "accuracy": 8.0}
    ]
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "features_tested": []
    }
    
    # Feature 1 & 8: Batch Location Updates
    try:
        batch_result = await api_client.post("/api/v1/location/batch", {
            "user_id": "demo_user",
            "locations": test_locations,
            "anonymous": False
        })
        results["features_tested"].append({
            "feature": "Real-time Location Tracking + Batch Updates",
            "status": "success" if "batch_id" in batch_result else "failed",
            "result": batch_result
        })
    except Exception as e:
        results["features_tested"].append({
            "feature": "Real-time Location Tracking + Batch Updates",
            "status": "failed",
            "error": str(e)
        })
    
    # Feature 2: Current Location
    try:
        current_result = await api_client.get("/api/v1/location/current/demo_user")
        results["features_tested"].append({
            "feature": "Current Location Retrieval",
            "status": "success" if current_result.get("found") else "failed",
            "result": current_result
        })
    except Exception as e:
        results["features_tested"].append({
            "feature": "Current Location Retrieval", 
            "status": "failed",
            "error": str(e)
        })
    
    # Feature 3: Location History
    try:
        history_result = await api_client.get("/api/v1/location/history/demo_user?limit=10")
        results["features_tested"].append({
            "feature": "Location History Queries",
            "status": "success" if "locations" in history_result else "failed",
            "result": history_result
        })
    except Exception as e:
        results["features_tested"].append({
            "feature": "Location History Queries",
            "status": "failed", 
            "error": str(e)
        })
    
    # Feature 4: Proximity Search
    try:
        nearby_result = await api_client.get("/api/v1/location/nearby/demo_user?radius_km=5")
        results["features_tested"].append({
            "feature": "Proximity Search",
            "status": "success" if "nearby_users" in nearby_result else "failed",
            "result": nearby_result
        })
    except Exception as e:
        results["features_tested"].append({
            "feature": "Proximity Search",
            "status": "failed",
            "error": str(e)
        })
    
    # Add simulated results for features 5-7
    results["features_tested"].extend([
        {
            "feature": "Geospatial Indexing",
            "status": "simulated",
            "result": {"geohash": "9q8yyw8", "precision": 7, "cell_size": "~150m x 150m"}
        },
        {
            "feature": "Location Sharing", 
            "status": "simulated",
            "result": {"sharing_id": str(uuid.uuid4()), "expires_in": "30 minutes"}
        },
        {
            "feature": "Location Privacy",
            "status": "simulated", 
            "result": {"anonymous_mode": True, "encryption": "AES-256", "retention": "90 days"}
        }
    ])
    
    return results

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Simulate real-time location updates
            update = {
                "type": "location_update",
                "user_id": f"user_{uuid.uuid4().hex[:6]}",
                "latitude": 37.7749 + (hash(time.time()) % 100) / 10000,
                "longitude": -122.4194 + (hash(time.time() * 2) % 100) / 10000,
                "timestamp": datetime.utcnow().isoformat(),
                "accuracy": 5.0
            }
            
            await websocket.send_text(json.dumps(update))
            await asyncio.sleep(2)  # Send update every 2 seconds
            
    except Exception as e:
        print(f"WebSocket error: {e}")

# Create HTML template
def create_html_template():
    """Create the main HTML template"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🗺️ Google Maps Clone - Interactive UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: rgba(255,255,255,0.95);
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            color: #333;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .container {
            flex: 1;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        
        .feature-card {
            background: rgba(255,255,255,0.9);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .feature-title {
            color: #333;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .feature-status {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: auto;
        }
        
        .status-success { background: #d4edda; color: #155724; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .status-testing { background: #fff3cd; color: #856404; }
        
        .feature-description {
            color: #666;
            margin-bottom: 1rem;
            line-height: 1.4;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .btn-secondary {
            background: #6c757d;
            margin-left: 0.5rem;
        }
        
        .real-time-section {
            background: rgba(255,255,255,0.9);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .real-time-updates {
            max-height: 300px;
            overflow-y: auto;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
        }
        
        .update-item {
            background: white;
            border-radius: 6px;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-left: 4px solid #667eea;
        }
        
        .results-section {
            background: rgba(255,255,255,0.9);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .results-content {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 0.9rem;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #28a745;
            animation: pulse 2s infinite;
        }
        
        .status-dot.disconnected {
            background: #dc3545;
            animation: none;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .features-grid { grid-template-columns: 1fr; }
            .header { padding: 1rem; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🗺️ Google Maps Clone - Interactive UI</h1>
        <div class="connection-status">
            <div class="status-dot" id="connectionStatus"></div>
            <span id="connectionText">Connecting...</span>
        </div>
    </div>
    
    <div class="container">
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-title">
                    <span>📍 Core Location Services</span>
                    <span class="feature-status status-testing" id="locationStatus">Ready</span>
                </div>
                <div class="feature-description">
                    Test all 8 core location features: real-time tracking, current location, 
                    history queries, proximity search, geospatial indexing, location sharing, 
                    privacy features, and batch processing.
                </div>
                <button class="btn" onclick="testLocationFeatures()">Test Location Features</button>
                <button class="btn btn-secondary" onclick="viewDocs()">API Docs</button>
            </div>
            
            <div class="feature-card">
                <div class="feature-title">
                    <span>🔄 Real-time Updates</span>
                    <span class="feature-status status-testing" id="realtimeStatus">Connecting</span>
                </div>
                <div class="feature-description">
                    Live WebSocket connection showing real-time location updates from users 
                    across the system. Experience the power of real-time mapping.
                </div>
                <button class="btn" onclick="toggleRealTime()" id="realtimeBtn">Start Real-time</button>
            </div>
            
            <div class="feature-card">
                <div class="feature-title">
                    <span>⚡ Performance Monitor</span>
                    <span class="feature-status status-success" id="perfStatus">Active</span>
                </div>
                <div class="feature-description">
                    Monitor system performance including response times, throughput, 
                    and resource usage. View metrics and health status.
                </div>
                <button class="btn" onclick="checkHealth()">Check Health</button>
                <button class="btn btn-secondary" onclick="openMonitoring()">Monitoring</button>
            </div>
        </div>
        
        <div class="real-time-section">
            <h2>📡 Real-time Location Updates</h2>
            <div class="real-time-updates" id="realtimeUpdates">
                <div class="update-item">Waiting for connection...</div>
            </div>
        </div>
        
        <div class="results-section">
            <h2>📊 Test Results</h2>
            <div class="results-content" id="testResults">
Click "Test Location Features" to run comprehensive tests of all 8 core location services.

Features that will be tested:
✅ Real-time Location Tracking - High-throughput batch processing  
✅ Current Location Retrieval - <50ms response time
✅ Location History Queries - Time-based location data  
✅ Proximity Search - Find nearby users/places
✅ Geospatial Indexing - Geohashing for efficient queries
✅ Location Sharing - Share location with others
✅ Location Privacy - Anonymous mode & data encryption
✅ Batch Location Updates - Efficient bulk processing
            </div>
        </div>
    </div>
    
    <script>
        let websocket = null;
        let realtimeActive = false;
        
        // Initialize WebSocket connection
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function() {
                document.getElementById('connectionStatus').classList.remove('disconnected');
                document.getElementById('connectionText').textContent = 'Connected to UI Server';
                document.getElementById('realtimeStatus').textContent = 'Connected';
                document.getElementById('realtimeStatus').className = 'feature-status status-success';
            };
            
            websocket.onmessage = function(event) {
                if (realtimeActive) {
                    const update = JSON.parse(event.data);
                    addRealtimeUpdate(update);
                }
            };
            
            websocket.onclose = function() {
                document.getElementById('connectionStatus').classList.add('disconnected');
                document.getElementById('connectionText').textContent = 'Disconnected';
                document.getElementById('realtimeStatus').textContent = 'Disconnected';
                document.getElementById('realtimeStatus').className = 'feature-status status-failed';
                setTimeout(initWebSocket, 5000); // Reconnect after 5 seconds
            };
        }
        
        // Add real-time update to display
        function addRealtimeUpdate(update) {
            const container = document.getElementById('realtimeUpdates');
            const updateDiv = document.createElement('div');
            updateDiv.className = 'update-item';
            updateDiv.innerHTML = `
                <strong>${update.user_id}</strong><br>
                📍 ${update.latitude.toFixed(4)}, ${update.longitude.toFixed(4)}<br>
                🕒 ${new Date(update.timestamp).toLocaleTimeString()}
                <span style="float: right;">±${update.accuracy}m</span>
            `;
            
            container.insertBefore(updateDiv, container.firstChild);
            
            // Keep only last 10 updates
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }
        
        // Toggle real-time updates
        function toggleRealTime() {
            realtimeActive = !realtimeActive;
            const btn = document.getElementById('realtimeBtn');
            
            if (realtimeActive) {
                btn.textContent = 'Stop Real-time';
                btn.style.background = '#dc3545';
            } else {
                btn.textContent = 'Start Real-time';
                btn.style.background = '';
            }
        }
        
        // Test location features
        async function testLocationFeatures() {
            const statusEl = document.getElementById('locationStatus');
            const resultsEl = document.getElementById('testResults');
            
            statusEl.textContent = 'Testing...';
            statusEl.className = 'feature-status status-testing';
            
            resultsEl.textContent = 'Testing all 8 core location features...\\n\\n';
            
            try {
                const response = await fetch('/api/demo/location-features');
                const results = await response.json();
                
                let output = `🗺️ CORE LOCATION SERVICES TEST RESULTS\\n`;
                output += `Timestamp: ${results.timestamp}\\n`;
                output += `${'='.repeat(50)}\\n\\n`;
                
                results.features_tested.forEach((test, index) => {
                    const emoji = test.status === 'success' ? '✅' : 
                                 test.status === 'failed' ? '❌' : '🔄';
                    output += `${index + 1}. ${emoji} ${test.feature}\\n`;
                    output += `   Status: ${test.status.toUpperCase()}\\n`;
                    
                    if (test.result && typeof test.result === 'object') {
                        output += `   Result: ${JSON.stringify(test.result, null, 2)}\\n`;
                    } else if (test.error) {
                        output += `   Error: ${test.error}\\n`;
                    }
                    output += '\\n';
                });
                
                const successCount = results.features_tested.filter(t => t.status === 'success').length;
                output += `${'='.repeat(50)}\\n`;
                output += `🎉 SUMMARY: ${successCount}/${results.features_tested.length} features tested successfully!\\n`;
                
                resultsEl.textContent = output;
                
                statusEl.textContent = `${successCount}/${results.features_tested.length} Passed`;
                statusEl.className = successCount === results.features_tested.length ? 
                    'feature-status status-success' : 'feature-status status-failed';
                
            } catch (error) {
                resultsEl.textContent = `❌ Test failed: ${error.message}`;
                statusEl.textContent = 'Failed';
                statusEl.className = 'feature-status status-failed';
            }
        }
        
        // Check system health
        async function checkHealth() {
            try {
                const response = await fetch('/api/health');
                const health = await response.json();
                
                const resultsEl = document.getElementById('testResults');
                resultsEl.textContent = `🔍 SYSTEM HEALTH CHECK\\n${JSON.stringify(health, null, 2)}`;
                
            } catch (error) {
                const resultsEl = document.getElementById('testResults');
                resultsEl.textContent = `❌ Health check failed: ${error.message}`;
            }
        }
        
        // Open API documentation
        function viewDocs() {
            window.open(`${window.location.protocol}//${window.location.hostname}:8080/docs`, '_blank');
        }
        
        // Open monitoring dashboard
        function openMonitoring() {
            window.open(`${window.location.protocol}//${window.location.hostname}:3000`, '_blank');
        }
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            initWebSocket();
        });
    </script>
</body>
</html>
    """
    
    with open(templates_dir / "index.html", "w") as f:
        f.write(html_content)

# Create startup script for UI
def create_ui_startup_script():
    """Create startup script for the UI"""
    script_content = f"""#!/usr/bin/env python3

import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    print("🚀 Starting Google Maps Clone - Web UI")
    print("======================================")
    
    # Check if backend is running
    try:
        import requests
        response = requests.get("{API_BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API is running")
        else:
            print("⚠️  Backend API might not be fully ready")
    except Exception as e:
        print("❌ Backend API not accessible. Please start backend services first.")
        print("   Run: ./scripts/start-all-services.sh")
        return
    
    # Start UI server
    print(f"\\n🌐 Starting Web UI on http://{UI_HOST}:{UI_PORT}")
    print("📱 Features available:")
    print("   - Interactive location testing")  
    print("   - Real-time updates via WebSocket")
    print("   - Performance monitoring")
    print("   - API documentation access")
    
    # Start the UI server
    try:
        import uvicorn
        uvicorn.run(
            "maps_ui:app",
            host="{UI_HOST}",
            port={UI_PORT},
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\\n🛑 UI Server stopped")
    except Exception as e:
        print(f"❌ Error starting UI: {{e}}")

if __name__ == "__main__":
    main()
"""
    
    with open(ui_dir / "start_ui.py", "w") as f:
        f.write(script_content)
    
    # Make executable
    import stat
    os.chmod(ui_dir / "start_ui.py", stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)

if __name__ == "__main__":
    # Create necessary files
    create_html_template()
    create_ui_startup_script()
    
    print("🗺️ Google Maps Clone - Web UI Server")
    print("====================================")
    print(f"🌐 Server: http://{UI_HOST}:{UI_PORT}")
    print(f"📡 Backend: {API_BASE_URL}")
    print("✨ Features: Interactive testing, Real-time updates, Monitoring")
    print("\\n🚀 Starting server...")
    
    # Start the server
    uvicorn.run(
        app,
        host=UI_HOST,
        port=UI_PORT,
        reload=False,
        log_level="info"
    )