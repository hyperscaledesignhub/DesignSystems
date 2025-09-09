"""
Simple Monitoring Service for Demo
"""

from fastapi import FastAPI
import aiohttp
import time
from typing import Dict, Any

app = FastAPI(title="Message Queue Monitoring")

# Service URLs
SERVICES = {
    "broker-1": "http://msgqueue-broker-1:19001",
    "broker-2": "http://msgqueue-broker-2:19001", 
    "broker-3": "http://msgqueue-broker-3:19001",
    "producer": "http://msgqueue-producer:19002",
    "consumer-1": "http://msgqueue-consumer-1:19003",
    "consumer-2": "http://msgqueue-consumer-2:19003",
    "coordinator": "http://msgqueue-coordinator:19004",
    "gateway": "http://msgqueue-gateway:19005"
}

@app.on_event("startup")
async def startup():
    print("Monitoring service started on port 19006")

@app.get("/metrics")
async def get_metrics():
    """Get Prometheus-style metrics."""
    metrics_data = await collect_metrics()
    
    # Convert to Prometheus format
    prometheus_metrics = []
    prometheus_metrics.append(f"messages_produced_total {metrics_data.get('total_messages', 0)}")
    prometheus_metrics.append(f"messages_consumed_total {metrics_data.get('consumed_messages', 0)}")
    prometheus_metrics.append(f"topics_count {metrics_data.get('topics_count', 0)}")
    
    for service, health in metrics_data.get('service_health', {}).items():
        status = 1 if health['status'] == 'healthy' else 0
        prometheus_metrics.append(f'{service.replace("-", "_")}_up {status}')
    
    return "\n".join(prometheus_metrics) + "\n"

@app.get("/health/system")
async def get_system_health():
    """Get overall system health."""
    metrics = await collect_metrics()
    
    healthy_services = len([
        s for s in metrics.get('service_health', {}).values() 
        if s['status'] == 'healthy'
    ])
    total_services = len(SERVICES)
    
    overall_status = "healthy" if healthy_services >= total_services * 0.7 else "unhealthy"
    
    return {
        "status": overall_status,
        "healthy_services": healthy_services,
        "total_services": total_services,
        "services": metrics.get('service_health', {}),
        "metrics": {
            "topics_count": metrics.get('topics_count', 0),
            "total_messages": metrics.get('total_messages', 0),
            "uptime": time.time()
        }
    }

async def collect_metrics() -> Dict[str, Any]:
    """Collect metrics from all services."""
    service_health = {}
    total_messages = 0
    topics_count = 0
    
    async with aiohttp.ClientSession() as session:
        # Check service health
        for service, url in SERVICES.items():
            try:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        health = await response.json()
                        service_health[service] = {"status": "healthy", "details": health}
                        
                        # Extract metrics if available
                        if "total_messages" in health:
                            total_messages += health["total_messages"]
                        if "topics_count" in health:
                            topics_count = max(topics_count, health["topics_count"])
                    else:
                        service_health[service] = {"status": "unhealthy", "details": f"HTTP {response.status}"}
            except:
                service_health[service] = {"status": "unreachable", "details": "Connection failed"}
        
        # Try to get broker-specific metrics
        try:
            async with session.get(f"{SERVICES['broker-1']}/topics") as response:
                if response.status == 200:
                    topics = await response.json()
                    topics_count = len(topics)
        except:
            pass
    
    return {
        "service_health": service_health,
        "total_messages": total_messages,
        "consumed_messages": int(total_messages * 0.8),  # Simulate consumption
        "topics_count": topics_count,
        "timestamp": time.time()
    }

@app.get("/dashboard")
async def get_dashboard():
    """Simple HTML dashboard."""
    metrics = await collect_metrics()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Message Queue Dashboard</title></head>
    <body>
    <h1>Message Queue System Dashboard</h1>
    <h2>Services Status</h2>
    <ul>
    """
    
    for service, health in metrics.get('service_health', {}).items():
        status_icon = "✅" if health['status'] == 'healthy' else "❌"
        html += f"<li>{status_icon} {service}: {health['status']}</li>"
    
    html += f"""
    </ul>
    <h2>Metrics</h2>
    <ul>
        <li>Topics: {metrics.get('topics_count', 0)}</li>
        <li>Messages Produced: {metrics.get('total_messages', 0)}</li>
        <li>Messages Consumed: {metrics.get('consumed_messages', 0)}</li>
    </ul>
    <script>setTimeout(() => location.reload(), 5000);</script>
    </body>
    </html>
    """
    
    return html

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "monitoring"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19006)