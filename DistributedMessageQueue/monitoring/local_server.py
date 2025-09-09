"""
Enhanced Monitoring Service for Demo with Local Service URLs
"""

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
import aiohttp
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict, deque

app = FastAPI(title="Message Queue Monitoring")

# Service URLs for local testing
SERVICES = {
    "producer": "http://localhost:19002",
    "consumer": "http://localhost:19003", 
    "coordinator": "http://localhost:19004",
    "gateway": "http://localhost:19005"
}

# Metrics storage
metrics_history = defaultdict(lambda: deque(maxlen=100))
alert_rules = {
    "high_error_rate": {"metric": "error_rate", "threshold": 0.1, "condition": ">"},
    "service_down": {"metric": "service_health", "threshold": 0.7, "condition": "<"},
    "low_messages": {"metric": "message_rate", "threshold": 1.0, "condition": "<"}
}
active_alerts = {}

# Background task for metrics collection
background_tasks = set()

@app.on_event("startup")
async def startup():
    print("Monitoring service started on port 19006")
    # Start background metrics collection
    task = asyncio.create_task(metrics_collection_loop())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

@app.on_event("shutdown")
async def shutdown():
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)

async def metrics_collection_loop():
    """Background task to collect metrics periodically."""
    while True:
        try:
            await collect_and_store_metrics()
            await check_alerts()
            await asyncio.sleep(10)  # Collect every 10 seconds
        except Exception as e:
            print(f"Error in metrics collection: {e}")
            await asyncio.sleep(5)

async def collect_and_store_metrics():
    """Collect metrics and store in history."""
    current_time = time.time()
    metrics = await collect_metrics()
    
    # Store key metrics with timestamps
    metrics_history["timestamp"].append(current_time)
    metrics_history["healthy_services"].append(len([
        s for s in metrics.get('service_health', {}).values() 
        if s['status'] == 'healthy'
    ]))
    metrics_history["total_services"].append(len(SERVICES))
    metrics_history["message_rate"].append(metrics.get('total_messages', 0))
    metrics_history["error_rate"].append(calculate_error_rate(metrics))

async def calculate_error_rate(metrics: Dict) -> float:
    """Calculate system error rate."""
    unhealthy_services = len([
        s for s in metrics.get('service_health', {}).values() 
        if s['status'] != 'healthy'
    ])
    total_services = len(SERVICES)
    return unhealthy_services / max(total_services, 1) if total_services > 0 else 0.0

async def check_alerts():
    """Check alert conditions and trigger/resolve alerts."""
    global active_alerts
    
    if not metrics_history["timestamp"]:
        return
        
    # Get latest metrics
    latest_metrics = {
        "service_health": len(metrics_history["healthy_services"]) / max(len(SERVICES), 1) if metrics_history["healthy_services"] else 0,
        "error_rate": metrics_history["error_rate"][-1] if metrics_history["error_rate"] else 0,
        "message_rate": metrics_history["message_rate"][-1] if metrics_history["message_rate"] else 0
    }
    
    for alert_name, rule in alert_rules.items():
        metric_value = latest_metrics.get(rule["metric"], 0)
        threshold = rule["threshold"]
        condition = rule["condition"]
        
        # Check condition
        alert_triggered = False
        if condition == ">":
            alert_triggered = metric_value > threshold
        elif condition == "<":
            alert_triggered = metric_value < threshold
        elif condition == ">=":
            alert_triggered = metric_value >= threshold
        elif condition == "<=":
            alert_triggered = metric_value <= threshold
        
        # Handle alert state
        if alert_triggered and alert_name not in active_alerts:
            active_alerts[alert_name] = {
                "triggered_at": datetime.utcnow(),
                "metric": rule["metric"],
                "value": metric_value,
                "threshold": threshold,
                "condition": condition
            }
            print(f"ALERT TRIGGERED: {alert_name} - {rule['metric']} {condition} {threshold} (current: {metric_value})")
        elif not alert_triggered and alert_name in active_alerts:
            duration = datetime.utcnow() - active_alerts[alert_name]["triggered_at"]
            print(f"ALERT RESOLVED: {alert_name} after {duration}")
            del active_alerts[alert_name]

@app.get("/metrics")
async def get_prometheus_metrics():
    """Get Prometheus-compatible metrics."""
    metrics_data = await collect_metrics()
    
    # Generate Prometheus format
    prometheus_lines = []
    
    # Help and type declarations
    prometheus_lines.extend([
        "# HELP msgqueue_messages_produced_total Total messages produced",
        "# TYPE msgqueue_messages_produced_total counter",
        f"msgqueue_messages_produced_total {metrics_data.get('total_messages', 0)}",
        "",
        "# HELP msgqueue_messages_consumed_total Total messages consumed", 
        "# TYPE msgqueue_messages_consumed_total counter",
        f"msgqueue_messages_consumed_total {metrics_data.get('consumed_messages', 0)}",
        "",
        "# HELP msgqueue_topics_count Number of topics",
        "# TYPE msgqueue_topics_count gauge",
        f"msgqueue_topics_count {metrics_data.get('topics_count', 0)}",
        "",
        "# HELP msgqueue_service_up Service availability (1=up, 0=down)",
        "# TYPE msgqueue_service_up gauge"
    ])
    
    # Service health metrics
    for service, health in metrics_data.get('service_health', {}).items():
        status_value = 1 if health['status'] == 'healthy' else 0
        service_name = service.replace("-", "_")
        prometheus_lines.append(f'msgqueue_service_up{{service="{service_name}"}} {status_value}')
    
    prometheus_lines.extend([
        "",
        "# HELP msgqueue_active_alerts Number of active alerts",
        "# TYPE msgqueue_active_alerts gauge",
        f"msgqueue_active_alerts {len(active_alerts)}",
        ""
    ])
    
    return Response(content="\n".join(prometheus_lines), media_type="text/plain")

@app.get("/health/system")
async def get_system_health():
    """Comprehensive system health aggregation."""
    metrics = await collect_metrics()
    
    healthy_services = len([
        s for s in metrics.get('service_health', {}).values() 
        if s['status'] == 'healthy'
    ])
    total_services = len(SERVICES)
    
    # Health calculation based on percentage of healthy services
    health_percentage = healthy_services / max(total_services, 1)
    overall_status = "healthy" if health_percentage >= 0.7 else "degraded" if health_percentage >= 0.5 else "unhealthy"
    
    return {
        "status": overall_status,
        "health_percentage": health_percentage,
        "healthy_services": healthy_services,
        "total_services": total_services,
        "services": metrics.get('service_health', {}),
        "metrics": {
            "topics_count": metrics.get('topics_count', 0),
            "total_messages": metrics.get('total_messages', 0),
            "consumed_messages": metrics.get('consumed_messages', 0),
            "uptime": time.time(),
            "error_rate": await calculate_error_rate(metrics)
        },
        "alerts": {
            "active_count": len(active_alerts),
            "active_alerts": list(active_alerts.keys())
        }
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Enhanced HTML dashboard with real-time metrics."""
    metrics = await collect_metrics()
    system_health = await get_system_health()
    
    # Calculate trends
    message_trend = "📈" if len(metrics_history["message_rate"]) >= 2 and metrics_history["message_rate"][-1] > metrics_history["message_rate"][-2] else "📊"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Message Queue Dashboard</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .card {{ background: white; border-radius: 8px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .status-healthy {{ color: #28a745; }}
            .status-unhealthy {{ color: #dc3545; }}
            .status-unreachable {{ color: #6c757d; }}
            .metric {{ display: inline-block; margin: 10px 20px; }}
            .alert {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 5px 0; border-radius: 4px; }}
            .alert-critical {{ background: #f8d7da; border-color: #f1aeb5; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖥️ Message Queue System Dashboard</h1>
            
            <div class="card">
                <h2>System Health: <span class="status-{system_health['status']}">{system_health['status'].upper()} ({system_health['health_percentage']:.1%})</span></h2>
                <div class="metric">Healthy Services: {system_health['healthy_services']}/{system_health['total_services']}</div>
                <div class="metric">Error Rate: {system_health['metrics']['error_rate']:.1%}</div>
                <div class="metric">Active Alerts: {len(active_alerts)}</div>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h2>Services Status</h2>
    """
    
    for service, health in metrics.get('service_health', {}).items():
        status_class = f"status-{health['status'].replace(' ', '-')}"
        icon = "✅" if health['status'] == 'healthy' else "❌" if health['status'] == 'unhealthy' else "⚠️"
        html += f"                    <div class='{status_class}'>{icon} <strong>{service}</strong>: {health['status']}</div>\n"
    
    html += f"""
                </div>
                
                <div class="card">
                    <h2>Key Metrics {message_trend}</h2>
                    <div class="metric">📊 Topics: {metrics.get('topics_count', 0)}</div>
                    <div class="metric">📤 Messages Produced: {metrics.get('total_messages', 0)}</div>
                    <div class="metric">📥 Messages Consumed: {metrics.get('consumed_messages', 0)}</div>
                    <div class="metric">⏱️ Collection Time: {datetime.now().strftime('%H:%M:%S')}</div>
                </div>
            </div>
    """
    
    if active_alerts:
        html += """
            <div class="card">
                <h2>🚨 Active Alerts</h2>
        """
        for alert_name, alert_info in active_alerts.items():
            duration = datetime.utcnow() - alert_info["triggered_at"]
            alert_class = "alert-critical" if "down" in alert_name or "high" in alert_name else "alert"
            html += f"""
                <div class="{alert_class}">
                    <strong>{alert_name.replace('_', ' ').title()}</strong><br>
                    Metric: {alert_info['metric']} = {alert_info['value']:.3f} {alert_info['condition']} {alert_info['threshold']}<br>
                    Duration: {str(duration).split('.')[0]}
                </div>
            """
        html += "</div>"
    
    html += """
            <div class="card">
                <h2>Alert Rules</h2>
    """
    for rule_name, rule in alert_rules.items():
        html += f"                <div>📋 {rule_name.replace('_', ' ').title()}: {rule['metric']} {rule['condition']} {rule['threshold']}</div>\n"
    
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.get("/alerts")
async def get_alerts():
    """Get current alerts and alert rules."""
    return {
        "active_alerts": {
            name: {
                "triggered_at": info["triggered_at"].isoformat(),
                "metric": info["metric"],
                "value": info["value"],
                "threshold": info["threshold"],
                "condition": info["condition"],
                "duration_seconds": (datetime.utcnow() - info["triggered_at"]).total_seconds()
            }
            for name, info in active_alerts.items()
        },
        "alert_rules": alert_rules,
        "total_active": len(active_alerts)
    }

@app.post("/alerts/configure")
async def configure_alert(alert_config: Dict[str, Any]):
    """Configure a new alert rule."""
    name = alert_config["name"]
    metric = alert_config["metric"] 
    threshold = alert_config["threshold"]
    condition = alert_config.get("condition", ">")
    
    alert_rules[name] = {
        "metric": metric,
        "threshold": threshold,
        "condition": condition
    }
    
    return {
        "status": "configured",
        "alert": {
            "name": name,
            "metric": metric,
            "threshold": threshold,
            "condition": condition
        }
    }

async def collect_metrics() -> Dict[str, Any]:
    """Enhanced metrics collection from all services."""
    service_health = {}
    total_messages = 0
    topics_count = 0
    
    async with aiohttp.ClientSession() as session:
        # Check service health
        for service, url in SERVICES.items():
            try:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        health = await response.json()
                        service_health[service] = {"status": "healthy", "details": health}
                        
                        # Extract service-specific metrics
                        if service == "coordinator" and "brokers_count" in health:
                            topics_count = health.get("consumer_groups_count", 0)
                        elif service == "producer":
                            # Simulate message count tracking
                            total_messages += 100  # Demo data
                    else:
                        service_health[service] = {"status": "unhealthy", "details": f"HTTP {response.status}"}
            except asyncio.TimeoutError:
                service_health[service] = {"status": "unreachable", "details": "Timeout"}
            except Exception as e:
                service_health[service] = {"status": "unreachable", "details": f"Error: {str(e)}"}
    
    return {
        "service_health": service_health,
        "total_messages": total_messages + int(time.time() % 1000),  # Simulate growing count
        "consumed_messages": int(total_messages * 0.85),  # Simulate 85% consumption rate
        "topics_count": max(topics_count, 3),  # At least 3 topics for demo
        "timestamp": time.time()
    }

@app.get("/metrics/history")
async def get_metrics_history():
    """Get historical metrics for trend analysis."""
    return {
        "timestamps": list(metrics_history["timestamp"])[-20:],  # Last 20 data points
        "healthy_services": list(metrics_history["healthy_services"])[-20:],
        "message_rate": list(metrics_history["message_rate"])[-20:],
        "error_rate": list(metrics_history["error_rate"])[-20:],
        "data_points": len(metrics_history["timestamp"])
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "monitoring",
        "uptime": time.time(),
        "active_alerts": len(active_alerts),
        "services_monitored": len(SERVICES)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19006)