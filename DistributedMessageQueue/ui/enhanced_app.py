"""
Enhanced Distributed Message Queue Demo UI with Integrated Monitoring
Interactive web interface with comprehensive monitoring dashboard
"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import aiohttp
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uvicorn

app = FastAPI(title="Message Queue Demo UI with Monitoring")

# Service URLs from environment
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:19005")
MONITORING_URL = os.getenv("MONITORING_URL", "http://localhost:19006")
PRODUCER_URL = os.getenv("PRODUCER_URL", "http://localhost:19002")
CONSUMER_URL = os.getenv("CONSUMER_URL", "http://localhost:19003")
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:19004")

# Store for WebSocket connections
websocket_connections: List[WebSocket] = []

# Demo data
demo_topics = ["orders", "payments", "notifications", "analytics"]
demo_messages = {
    "orders": [
        {"orderId": "ORD-001", "userId": "USER-123", "amount": 99.99, "status": "pending"},
        {"orderId": "ORD-002", "userId": "USER-456", "amount": 149.99, "status": "confirmed"},
        {"orderId": "ORD-003", "userId": "USER-789", "amount": 299.99, "status": "shipped"}
    ],
    "payments": [
        {"paymentId": "PAY-001", "orderId": "ORD-001", "method": "credit_card", "status": "success"},
        {"paymentId": "PAY-002", "orderId": "ORD-002", "method": "paypal", "status": "pending"},
        {"paymentId": "PAY-003", "orderId": "ORD-003", "method": "stripe", "status": "success"}
    ],
    "notifications": [
        {"type": "email", "to": "user@example.com", "subject": "Order Confirmed", "priority": "high"},
        {"type": "sms", "to": "+1234567890", "message": "Your order has shipped", "priority": "medium"},
        {"type": "push", "userId": "USER-123", "title": "Payment Received", "priority": "low"}
    ],
    "analytics": [
        {"event": "page_view", "userId": "USER-123", "page": "/products", "timestamp": "2024-01-01T10:00:00"},
        {"event": "add_to_cart", "userId": "USER-456", "productId": "PROD-789", "timestamp": "2024-01-01T10:05:00"},
        {"event": "checkout", "userId": "USER-789", "amount": 299.99, "timestamp": "2024-01-01T10:10:00"}
    ]
}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the enhanced UI dashboard with monitoring"""
    return HTML_CONTENT

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates including monitoring data"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Send comprehensive monitoring data every 3 seconds
            monitoring_data = await get_comprehensive_monitoring_data()
            await websocket.send_json({"type": "monitoring_update", "data": monitoring_data})
            await asyncio.sleep(3)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

# Demo API endpoints (same as original)
@app.post("/api/demo/create-topics")
async def create_demo_topics():
    """Create demo topics"""
    results = []
    async with aiohttp.ClientSession() as session:
        for topic in demo_topics:
            try:
                async with session.post(
                    f"{GATEWAY_URL}/api/v1/topics",
                    json={"name": topic, "partitions": 3, "replication_factor": 3},
                    headers={"X-API-Key": "admin-key"}
                ) as resp:
                    result = await resp.json()
                    results.append({"topic": topic, "status": "created", "result": result})
            except Exception as e:
                results.append({"topic": topic, "status": "error", "error": str(e)})
    
    await broadcast_update({"type": "topics_created", "data": results})
    return results

@app.post("/api/demo/produce-messages")
async def produce_demo_messages(topic: str = "orders", count: int = 10):
    """Produce demo messages to a topic"""
    if topic not in demo_messages:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {topic}")
    
    messages_sent = []
    async with aiohttp.ClientSession() as session:
        for i in range(count):
            message = demo_messages[topic][i % len(demo_messages[topic])]
            message["timestamp"] = datetime.now().isoformat()
            message["sequence"] = i + 1
            
            try:
                async with session.post(
                    f"{GATEWAY_URL}/api/v1/produce",
                    json={
                        "topic": topic,
                        "key": f"{topic}-{i}",
                        "value": json.dumps(message)
                    },
                    headers={"X-API-Key": "admin-key"}
                ) as resp:
                    result = await resp.json()
                    messages_sent.append({
                        "sequence": i + 1,
                        "status": "sent",
                        "partition": result.get("partition"),
                        "offset": result.get("offset")
                    })
            except Exception as e:
                messages_sent.append({
                    "sequence": i + 1,
                    "status": "error",
                    "error": str(e)
                })
            
            await asyncio.sleep(0.1)
    
    await broadcast_update({"type": "messages_produced", "topic": topic, "data": messages_sent})
    return {"topic": topic, "count": len(messages_sent), "messages": messages_sent}

@app.post("/api/demo/consume-messages")
async def consume_demo_messages(topic: str = "orders", group: str = "demo-group", limit: int = 10):
    """Consume messages from a topic"""
    async with aiohttp.ClientSession() as session:
        try:
            # Subscribe to topic
            async with session.post(
                f"{GATEWAY_URL}/api/v1/subscribe",
                json={"topics": [topic], "group": group},
                headers={"X-API-Key": "admin-key"}
            ) as resp:
                subscription = await resp.json()
            
            # Consume messages
            async with session.get(
                f"{GATEWAY_URL}/api/v1/consume",
                params={"group": group, "timeout": 5, "limit": limit},
                headers={"X-API-Key": "admin-key"}
            ) as resp:
                messages = await resp.json()
                
                await broadcast_update({"type": "messages_consumed", "topic": topic, "data": messages})
                return messages
        except Exception as e:
            return {"error": str(e)}

# Enhanced monitoring API endpoints
@app.get("/api/monitoring/comprehensive")
async def get_comprehensive_monitoring_data():
    """Get comprehensive monitoring data from all sources"""
    async with aiohttp.ClientSession() as session:
        monitoring_data = {
            "timestamp": datetime.now().isoformat(),
            "system_health": {},
            "metrics": {},
            "alerts": {},
            "services": {},
            "prometheus_metrics": {}
        }
        
        try:
            # Get system health
            async with session.get(f"{MONITORING_URL}/health/system") as resp:
                if resp.status == 200:
                    monitoring_data["system_health"] = await resp.json()
        except:
            monitoring_data["system_health"] = {"status": "unknown", "error": "monitoring service unavailable"}
        
        try:
            # Get Prometheus metrics
            async with session.get(f"{MONITORING_URL}/metrics") as resp:
                if resp.status == 200:
                    metrics_text = await resp.text()
                    monitoring_data["prometheus_metrics"] = parse_prometheus_metrics(metrics_text)
        except:
            monitoring_data["prometheus_metrics"] = {"error": "metrics unavailable"}
        
        try:
            # Get alerts
            async with session.get(f"{MONITORING_URL}/alerts") as resp:
                if resp.status == 200:
                    monitoring_data["alerts"] = await resp.json()
        except:
            monitoring_data["alerts"] = {"active_alerts": {}, "alert_rules": {}}
        
        try:
            # Get individual service health
            services = {
                "producer": PRODUCER_URL,
                "consumer": CONSUMER_URL,
                "coordinator": COORDINATOR_URL,
                "gateway": GATEWAY_URL
            }
            
            for service_name, service_url in services.items():
                try:
                    async with session.get(f"{service_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        if resp.status == 200:
                            health_data = await resp.json()
                            monitoring_data["services"][service_name] = {
                                "status": "healthy",
                                "details": health_data,
                                "response_time": "< 2s"
                            }
                        else:
                            monitoring_data["services"][service_name] = {
                                "status": "unhealthy",
                                "details": f"HTTP {resp.status}"
                            }
                except:
                    monitoring_data["services"][service_name] = {
                        "status": "unreachable",
                        "details": "Connection failed"
                    }
        except:
            monitoring_data["services"] = {"error": "service health check failed"}
        
        return monitoring_data

@app.post("/api/monitoring/configure-alert")
async def configure_alert(alert_config: Dict[str, Any]):
    """Configure a new alert rule"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{MONITORING_URL}/alerts/configure",
                json=alert_config
            ) as resp:
                result = await resp.json()
                await broadcast_update({"type": "alert_configured", "data": result})
                return result
        except Exception as e:
            return {"error": str(e)}

def parse_prometheus_metrics(metrics_text: str) -> Dict[str, Any]:
    """Enhanced Prometheus metrics parser"""
    metrics = {
        "messages_produced_total": 0,
        "messages_consumed_total": 0,
        "topics_count": 0,
        "active_alerts": 0,
        "services": {}
    }
    
    for line in metrics_text.split('\n'):
        if line.startswith('msgqueue_messages_produced_total'):
            try:
                metrics["messages_produced_total"] = int(float(line.split()[-1]))
            except:
                pass
        elif line.startswith('msgqueue_messages_consumed_total'):
            try:
                metrics["messages_consumed_total"] = int(float(line.split()[-1]))
            except:
                pass
        elif line.startswith('msgqueue_topics_count'):
            try:
                metrics["topics_count"] = int(float(line.split()[-1]))
            except:
                pass
        elif line.startswith('msgqueue_active_alerts'):
            try:
                metrics["active_alerts"] = int(float(line.split()[-1]))
            except:
                pass
        elif line.startswith('msgqueue_service_up{service='):
            try:
                # Extract service name and status
                service = line.split('service="')[1].split('"')[0]
                status = int(float(line.split()[-1]))
                metrics["services"][service] = status
            except:
                pass
    
    return metrics

async def broadcast_update(data: Dict[str, Any]):
    """Broadcast updates to all WebSocket connections"""
    disconnected = []
    for ws in websocket_connections:
        try:
            await ws.send_json(data)
        except:
            disconnected.append(ws)
    
    # Remove disconnected websockets
    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)

# Enhanced HTML content with comprehensive monitoring dashboard
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Message Queue Demo - Enhanced Monitoring</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .tab-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
            margin-bottom: 20px;
        }
        
        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        
        .tab {
            flex: 1;
            padding: 15px 20px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }
        
        .tab.active {
            background: white;
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .tab:hover {
            background: #e9ecef;
        }
        
        .tab-content {
            display: none;
            padding: 30px;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        
        .card:hover {
            transform: translateY(-2px);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.2em;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-value {
            font-weight: bold;
            font-size: 1.2em;
        }
        
        .status-healthy { color: #28a745; }
        .status-unhealthy { color: #dc3545; }
        .status-unreachable { color: #6c757d; }
        .status-degraded { color: #ffc107; }
        
        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            margin: 5px;
        }
        
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .btn-small {
            padding: 5px 15px;
            font-size: 12px;
        }
        
        .control-group {
            margin-bottom: 25px;
        }
        
        .control-group h3 {
            color: #333;
            margin-bottom: 15px;
        }
        
        .btn-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 5px;
        }
        
        .input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 5px;
            width: 150px;
        }
        
        .log {
            background: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            margin-top: 15px;
        }
        
        .alert-item {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 10px;
            margin: 5px 0;
        }
        
        .alert-critical {
            background: #f8d7da;
            border-color: #f1aeb5;
        }
        
        .service-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .service-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            border-left: 4px solid;
        }
        
        .service-healthy {
            border-left-color: #28a745;
        }
        
        .service-unhealthy {
            border-left-color: #dc3545;
        }
        
        .service-unreachable {
            border-left-color: #6c757d;
        }
        
        .metric-large {
            text-align: center;
            padding: 20px;
        }
        
        .metric-large .value {
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }
        
        .metric-large .label {
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
        }
        
        @media (max-width: 768px) {
            .tabs {
                flex-direction: column;
            }
            
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Message Queue System - Enhanced Monitoring</h1>
        
        <div class="tab-container">
            <div class="tabs">
                <button class="tab active" onclick="showTab('overview')">📊 System Overview</button>
                <button class="tab" onclick="showTab('monitoring')">📈 Monitoring Dashboard</button>
                <button class="tab" onclick="showTab('demo')">🎮 Demo Controls</button>
                <button class="tab" onclick="showTab('alerts')">🚨 Alerts & Rules</button>
            </div>
            
            <!-- System Overview Tab -->
            <div id="overview" class="tab-content active">
                <div class="dashboard-grid">
                    <div class="card">
                        <h2>🌡️ System Health</h2>
                        <div class="metric-large">
                            <span id="system-health-status" class="value status-healthy">HEALTHY</span>
                            <div class="label">Overall Status</div>
                        </div>
                        <div class="metric">
                            <span>Health Percentage:</span>
                            <span id="health-percentage" class="metric-value status-healthy">100%</span>
                        </div>
                        <div class="metric">
                            <span>Services Online:</span>
                            <span id="services-online" class="metric-value">4/4</span>
                        </div>
                        <div class="metric">
                            <span>Active Alerts:</span>
                            <span id="active-alerts-count" class="metric-value">0</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>📊 Key Metrics</h2>
                        <div class="metric">
                            <span>Messages Produced:</span>
                            <span id="messages-produced" class="metric-value status-healthy">0</span>
                        </div>
                        <div class="metric">
                            <span>Messages Consumed:</span>
                            <span id="messages-consumed" class="metric-value status-healthy">0</span>
                        </div>
                        <div class="metric">
                            <span>Topics Count:</span>
                            <span id="topics-count" class="metric-value">0</span>
                        </div>
                        <div class="metric">
                            <span>Error Rate:</span>
                            <span id="error-rate" class="metric-value status-healthy">0%</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>⚡ Real-time Status</h2>
                        <div class="metric">
                            <span>Last Update:</span>
                            <span id="last-update" class="metric-value">Never</span>
                        </div>
                        <div class="metric">
                            <span>Connection:</span>
                            <span id="connection-status" class="metric-value status-unreachable">Connecting...</span>
                        </div>
                        <div class="metric">
                            <span>Data Points:</span>
                            <span id="data-points" class="metric-value">0</span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🖥️ Service Status</h2>
                    <div id="services-grid" class="service-grid">
                        <!-- Service cards will be populated by JavaScript -->
                    </div>
                </div>
            </div>
            
            <!-- Monitoring Dashboard Tab -->
            <div id="monitoring" class="tab-content">
                <div class="dashboard-grid">
                    <div class="card">
                        <h2>📈 Prometheus Metrics</h2>
                        <div id="prometheus-metrics">
                            <div class="metric">
                                <span>Messages Produced Total:</span>
                                <span id="prom-messages-produced" class="metric-value">0</span>
                            </div>
                            <div class="metric">
                                <span>Messages Consumed Total:</span>
                                <span id="prom-messages-consumed" class="metric-value">0</span>
                            </div>
                            <div class="metric">
                                <span>Active Services:</span>
                                <span id="prom-active-services" class="metric-value">0</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>📊 Historical Trends</h2>
                        <div class="metric">
                            <span>Message Rate Trend:</span>
                            <span id="message-trend" class="metric-value">📊 Stable</span>
                        </div>
                        <div class="metric">
                            <span>System Uptime:</span>
                            <span id="system-uptime" class="metric-value">N/A</span>
                        </div>
                        <div class="metric">
                            <span>Peak Messages/sec:</span>
                            <span id="peak-rate" class="metric-value">0</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Demo Controls Tab -->
            <div id="demo" class="tab-content">
                <div class="control-group">
                    <h3>🎯 Topic Management</h3>
                    <div class="btn-group">
                        <button class="btn" onclick="createTopics()">Create Demo Topics</button>
                    </div>
                </div>
                
                <div class="control-group">
                    <h3>📤 Message Production</h3>
                    <div class="btn-group">
                        <select id="produce-topic" class="select">
                            <option value="orders">Orders</option>
                            <option value="payments">Payments</option>
                            <option value="notifications">Notifications</option>
                            <option value="analytics">Analytics</option>
                        </select>
                        <input id="produce-count" class="input" type="number" value="10" min="1" max="100" placeholder="Count">
                        <button class="btn" onclick="produceMessages()">Produce Messages</button>
                    </div>
                </div>
                
                <div class="control-group">
                    <h3>📥 Message Consumption</h3>
                    <div class="btn-group">
                        <select id="consume-topic" class="select">
                            <option value="orders">Orders</option>
                            <option value="payments">Payments</option>
                            <option value="notifications">Notifications</option>
                            <option value="analytics">Analytics</option>
                        </select>
                        <input id="consume-group" class="input" type="text" value="demo-group" placeholder="Consumer Group">
                        <input id="consume-limit" class="input" type="number" value="10" min="1" max="50" placeholder="Limit">
                        <button class="btn" onclick="consumeMessages()">Consume Messages</button>
                    </div>
                </div>
                
                <div class="card">
                    <h2>📝 Activity Log</h2>
                    <div id="activity-log" class="log">
                        <div>System initialized. Ready for demo operations...</div>
                    </div>
                </div>
            </div>
            
            <!-- Alerts & Rules Tab -->
            <div id="alerts" class="tab-content">
                <div class="dashboard-grid">
                    <div class="card">
                        <h2>🚨 Active Alerts</h2>
                        <div id="active-alerts">
                            <p>No active alerts</p>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>📋 Alert Rules</h2>
                        <div id="alert-rules">
                            <p>Loading alert rules...</p>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>⚙️ Configure New Alert</h2>
                    <div class="control-group">
                        <input id="alert-name" class="input" type="text" placeholder="Alert Name">
                        <select id="alert-metric" class="select">
                            <option value="error_rate">Error Rate</option>
                            <option value="service_health">Service Health</option>
                            <option value="message_rate">Message Rate</option>
                        </select>
                        <select id="alert-condition" class="select">
                            <option value=">">Greater Than</option>
                            <option value="<">Less Than</option>
                            <option value=">=">Greater or Equal</option>
                            <option value="<=">Less or Equal</option>
                        </select>
                        <input id="alert-threshold" class="input" type="number" step="0.01" placeholder="Threshold">
                        <button class="btn" onclick="configureAlert()">Create Alert</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let socket;
        let dataPoints = 0;
        
        // Initialize WebSocket connection
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            socket.onopen = function() {
                updateConnectionStatus('Connected', 'healthy');
                logActivity('WebSocket connected - real-time updates enabled');
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'monitoring_update') {
                    updateMonitoringData(data.data);
                } else {
                    logActivity(`Update: ${data.type}`);
                }
            };
            
            socket.onclose = function() {
                updateConnectionStatus('Disconnected', 'unreachable');
                logActivity('WebSocket disconnected - attempting reconnection...');
                setTimeout(initWebSocket, 3000);
            };
            
            socket.onerror = function() {
                updateConnectionStatus('Error', 'unhealthy');
            };
        }
        
        function updateConnectionStatus(status, healthClass) {
            const element = document.getElementById('connection-status');
            element.textContent = status;
            element.className = `metric-value status-${healthClass}`;
        }
        
        function updateMonitoringData(data) {
            dataPoints++;
            document.getElementById('data-points').textContent = dataPoints;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            // Update system health
            if (data.system_health) {
                const health = data.system_health;
                document.getElementById('system-health-status').textContent = (health.status || 'UNKNOWN').toUpperCase();
                document.getElementById('system-health-status').className = `value status-${health.status || 'unreachable'}`;
                
                if (health.health_percentage !== undefined) {
                    const percentage = Math.round(health.health_percentage * 100);
                    document.getElementById('health-percentage').textContent = `${percentage}%`;
                    document.getElementById('health-percentage').className = `metric-value status-${health.status || 'unreachable'}`;
                }
                
                if (health.healthy_services !== undefined && health.total_services !== undefined) {
                    document.getElementById('services-online').textContent = `${health.healthy_services}/${health.total_services}`;
                }
                
                if (health.metrics && health.metrics.error_rate !== undefined) {
                    const errorRate = Math.round(health.metrics.error_rate * 100);
                    document.getElementById('error-rate').textContent = `${errorRate}%`;
                }
            }
            
            // Update Prometheus metrics
            if (data.prometheus_metrics) {
                const prom = data.prometheus_metrics;
                document.getElementById('messages-produced').textContent = prom.messages_produced_total || 0;
                document.getElementById('messages-consumed').textContent = prom.messages_consumed_total || 0;
                document.getElementById('topics-count').textContent = prom.topics_count || 0;
                
                // Update Prometheus tab
                document.getElementById('prom-messages-produced').textContent = prom.messages_produced_total || 0;
                document.getElementById('prom-messages-consumed').textContent = prom.messages_consumed_total || 0;
                
                if (prom.services) {
                    const activeServices = Object.values(prom.services).filter(s => s === 1).length;
                    document.getElementById('prom-active-services').textContent = activeServices;
                }
            }
            
            // Update alerts
            if (data.alerts) {
                const alertCount = data.alerts.total_active || Object.keys(data.alerts.active_alerts || {}).length;
                document.getElementById('active-alerts-count').textContent = alertCount;
                
                updateAlertsDisplay(data.alerts);
            }
            
            // Update individual services
            if (data.services) {
                updateServicesGrid(data.services);
            }
        }
        
        function updateServicesGrid(services) {
            const grid = document.getElementById('services-grid');
            grid.innerHTML = '';
            
            for (const [serviceName, serviceData] of Object.entries(services)) {
                const card = document.createElement('div');
                card.className = `service-card service-${serviceData.status}`;
                card.innerHTML = `
                    <h4>${serviceName.charAt(0).toUpperCase() + serviceName.slice(1)}</h4>
                    <div class="metric">
                        <span>Status:</span>
                        <span class="status-${serviceData.status}">${serviceData.status}</span>
                    </div>
                    <div class="metric">
                        <span>Details:</span>
                        <span>${typeof serviceData.details === 'object' ? JSON.stringify(serviceData.details).substring(0,30) + '...' : serviceData.details}</span>
                    </div>
                `;
                grid.appendChild(card);
            }
        }
        
        function updateAlertsDisplay(alertsData) {
            const activeAlertsDiv = document.getElementById('active-alerts');
            const alertRulesDiv = document.getElementById('alert-rules');
            
            // Update active alerts
            const activeAlerts = alertsData.active_alerts || {};
            if (Object.keys(activeAlerts).length === 0) {
                activeAlertsDiv.innerHTML = '<p>No active alerts</p>';
            } else {
                activeAlertsDiv.innerHTML = '';
                for (const [alertName, alertInfo] of Object.entries(activeAlerts)) {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert-item alert-critical';
                    alertDiv.innerHTML = `
                        <strong>${alertName.replace('_', ' ').toUpperCase()}</strong><br>
                        Metric: ${alertInfo.metric} ${alertInfo.condition} ${alertInfo.threshold}<br>
                        Value: ${alertInfo.value}<br>
                        Duration: ${alertInfo.duration_seconds}s
                    `;
                    activeAlertsDiv.appendChild(alertDiv);
                }
            }
            
            // Update alert rules
            const alertRules = alertsData.alert_rules || {};
            if (Object.keys(alertRules).length === 0) {
                alertRulesDiv.innerHTML = '<p>No alert rules configured</p>';
            } else {
                alertRulesDiv.innerHTML = '';
                for (const [ruleName, ruleInfo] of Object.entries(alertRules)) {
                    const ruleDiv = document.createElement('div');
                    ruleDiv.className = 'alert-item';
                    ruleDiv.innerHTML = `
                        <strong>${ruleName.replace('_', ' ').toUpperCase()}</strong><br>
                        Condition: ${ruleInfo.metric} ${ruleInfo.condition} ${ruleInfo.threshold}
                    `;
                    alertRulesDiv.appendChild(ruleDiv);
                }
            }
        }
        
        // Tab switching
        function showTab(tabId) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }
        
        // Demo functions
        function createTopics() {
            logActivity('Creating demo topics...');
            fetch('/api/demo/create-topics', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    logActivity(`Created ${data.length} topics: ${data.map(t => t.topic).join(', ')}`);
                })
                .catch(error => logActivity(`Error creating topics: ${error}`));
        }
        
        function produceMessages() {
            const topic = document.getElementById('produce-topic').value;
            const count = document.getElementById('produce-count').value;
            
            logActivity(`Producing ${count} messages to topic: ${topic}`);
            fetch(`/api/demo/produce-messages?topic=${topic}&count=${count}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    logActivity(`Produced ${data.count} messages to ${data.topic}`);
                })
                .catch(error => logActivity(`Error producing messages: ${error}`));
        }
        
        function consumeMessages() {
            const topic = document.getElementById('consume-topic').value;
            const group = document.getElementById('consume-group').value;
            const limit = document.getElementById('consume-limit').value;
            
            logActivity(`Consuming messages from topic: ${topic}, group: ${group}`);
            fetch(`/api/demo/consume-messages?topic=${topic}&group=${group}&limit=${limit}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        logActivity(`Error consuming: ${data.error}`);
                    } else {
                        logActivity(`Consumed ${data.message_count || 0} messages from ${topic}`);
                    }
                })
                .catch(error => logActivity(`Error consuming messages: ${error}`));
        }
        
        function configureAlert() {
            const alertConfig = {
                name: document.getElementById('alert-name').value,
                metric: document.getElementById('alert-metric').value,
                condition: document.getElementById('alert-condition').value,
                threshold: parseFloat(document.getElementById('alert-threshold').value)
            };
            
            if (!alertConfig.name || !alertConfig.threshold) {
                logActivity('Error: Alert name and threshold are required');
                return;
            }
            
            logActivity(`Configuring alert: ${alertConfig.name}`);
            fetch('/api/monitoring/configure-alert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(alertConfig)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        logActivity(`Error configuring alert: ${data.error}`);
                    } else {
                        logActivity(`Alert configured: ${alertConfig.name}`);
                        // Clear form
                        document.getElementById('alert-name').value = '';
                        document.getElementById('alert-threshold').value = '';
                    }
                })
                .catch(error => logActivity(`Error configuring alert: ${error}`));
        }
        
        function logActivity(message) {
            const log = document.getElementById('activity-log');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.innerHTML = `[${timestamp}] ${message}`;
            log.appendChild(logEntry);
            log.scrollTop = log.scrollHeight;
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            initWebSocket();
            logActivity('UI initialized - connecting to monitoring services...');
        });
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)