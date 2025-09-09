"""Monitoring service implementation."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Response
from contextlib import asynccontextmanager
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from ..shared.models import MetricPoint, SystemMetrics, HealthStatus, ServiceStatus
from ..shared.config import Config
from ..shared.utils import make_http_request

logger = structlog.get_logger()


# Prometheus metrics
request_count = Counter('msgqueue_requests_total', 'Total requests', ['service', 'endpoint'])
request_duration = Histogram('msgqueue_request_duration_seconds', 'Request duration', ['service'])
message_count = Counter('msgqueue_messages_total', 'Total messages', ['topic', 'type'])
consumer_lag = Gauge('msgqueue_consumer_lag', 'Consumer lag', ['group', 'topic', 'partition'])
service_health = Gauge('msgqueue_service_health', 'Service health', ['service'])
broker_partitions = Gauge('msgqueue_broker_partitions', 'Broker partitions', ['broker', 'topic'])


class MetricsCollector:
    """Collects and stores metrics from all services."""
    
    def __init__(self):
        self.metrics_store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.service_endpoints = {
            "producer": f"http://localhost:{Config.PRODUCER_PORT}",
            "consumer": f"http://localhost:{Config.CONSUMER_PORT}",
            "broker": f"http://localhost:{Config.BROKER_PORT}",
            "coordinator": f"http://localhost:{Config.COORDINATOR_PORT}",
            "gateway": f"http://localhost:{Config.GATEWAY_PORT}"
        }
        self.last_collection_time = datetime.utcnow()
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start metrics collection."""
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collector started")
    
    async def stop(self):
        """Stop metrics collection."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
        logger.info("Metrics collector stopped")
    
    async def _collection_loop(self):
        """Periodic metrics collection loop."""
        while self._running:
            try:
                await self._collect_all_metrics()
                await asyncio.sleep(Config.SCRAPE_INTERVAL_MS / 1000)
            except Exception as e:
                logger.error("Error in metrics collection", error=str(e))
                await asyncio.sleep(5)
    
    async def _collect_all_metrics(self):
        """Collect metrics from all services."""
        timestamp = datetime.utcnow()
        
        # Collect from each service
        for service_name, endpoint in self.service_endpoints.items():
            await self._collect_service_metrics(service_name, endpoint, timestamp)
        
        # Collect system metrics
        await self._collect_system_metrics(timestamp)
        
        self.last_collection_time = timestamp
    
    async def _collect_service_metrics(self, service_name: str, endpoint: str, timestamp: datetime):
        """Collect metrics from a specific service."""
        try:
            # Health check
            health_response = await make_http_request("GET", f"{endpoint}/health", timeout=5)
            health_value = 1 if health_response and health_response.get("status") == "healthy" else 0
            service_health.labels(service=service_name).set(health_value)
            
            # Service-specific metrics
            if service_name == "producer":
                await self._collect_producer_metrics(endpoint, timestamp)
            elif service_name == "consumer":
                await self._collect_consumer_metrics(endpoint, timestamp)
            elif service_name == "broker":
                await self._collect_broker_metrics(endpoint, timestamp)
            elif service_name == "coordinator":
                await self._collect_coordinator_metrics(endpoint, timestamp)
            elif service_name == "gateway":
                await self._collect_gateway_metrics(endpoint, timestamp)
                
        except Exception as e:
            logger.warning("Failed to collect metrics from service", service=service_name, error=str(e))
            service_health.labels(service=service_name).set(0)
    
    async def _collect_producer_metrics(self, endpoint: str, timestamp: datetime):
        """Collect producer-specific metrics."""
        try:
            response = await make_http_request("GET", f"{endpoint}/status")
            if response:
                metrics = response.get("metrics", {})
                
                # Store metrics
                self._store_metric("producer_messages_total", metrics.get("total_messages", 0), timestamp)
                self._store_metric("producer_errors_total", metrics.get("total_errors", 0), timestamp)
                self._store_metric("producer_error_rate", metrics.get("error_rate", 0), timestamp)
                
                # Batch metrics
                batch_stats = metrics.get("batch_stats", {})
                self._store_metric("producer_active_batches", batch_stats.get("active_batches", 0), timestamp)
                
        except Exception as e:
            logger.warning("Failed to collect producer metrics", error=str(e))
    
    async def _collect_consumer_metrics(self, endpoint: str, timestamp: datetime):
        """Collect consumer-specific metrics."""
        try:
            response = await make_http_request("GET", f"{endpoint}/status")
            if response:
                metrics = response.get("metrics", {})
                
                # Store metrics
                self._store_metric("consumer_messages_consumed", metrics.get("consumed_messages", 0), timestamp)
                
                processing_stats = metrics.get("processing_stats", {})
                self._store_metric("consumer_processed_count", processing_stats.get("processed_count", 0), timestamp)
                self._store_metric("consumer_error_count", processing_stats.get("error_count", 0), timestamp)
                
        except Exception as e:
            logger.warning("Failed to collect consumer metrics", error=str(e))
    
    async def _collect_broker_metrics(self, endpoint: str, timestamp: datetime):
        """Collect broker-specific metrics."""
        try:
            # Get topics
            topics_response = await make_http_request("GET", f"{endpoint}/topics")
            if topics_response:
                topics = topics_response.get("topics", [])
                self._store_metric("broker_topics_count", len(topics), timestamp)
                
                # Count partitions
                total_partitions = sum(topic.get("partitions", 0) for topic in topics)
                self._store_metric("broker_partitions_total", total_partitions, timestamp)
                
        except Exception as e:
            logger.warning("Failed to collect broker metrics", error=str(e))
    
    async def _collect_coordinator_metrics(self, endpoint: str, timestamp: datetime):
        """Collect coordinator-specific metrics."""
        try:
            # Get brokers
            brokers_response = await make_http_request("GET", f"{endpoint}/brokers")
            if brokers_response:
                brokers = brokers_response.get("brokers", [])
                healthy_brokers = [b for b in brokers if b.get("status") == "healthy"]
                
                self._store_metric("coordinator_brokers_total", len(brokers), timestamp)
                self._store_metric("coordinator_brokers_healthy", len(healthy_brokers), timestamp)
            
            # Get consumer groups
            groups_response = await make_http_request("GET", f"{endpoint}/consumer-groups")
            if groups_response:
                groups = groups_response.get("groups", [])
                self._store_metric("coordinator_consumer_groups", len(groups), timestamp)
                
        except Exception as e:
            logger.warning("Failed to collect coordinator metrics", error=str(e))
    
    async def _collect_gateway_metrics(self, endpoint: str, timestamp: datetime):
        """Collect gateway-specific metrics."""
        try:
            # Gateway status includes request counts
            response = await make_http_request("GET", f"{endpoint}/api/v1/status")
            if response:
                gateway_stats = response.get("services", {}).get("gateway", {})
                
                self._store_metric("gateway_requests_total", gateway_stats.get("request_count", 0), timestamp)
                self._store_metric("gateway_errors_total", gateway_stats.get("error_count", 0), timestamp)
                self._store_metric("gateway_error_rate", gateway_stats.get("error_rate", 0), timestamp)
                
        except Exception as e:
            logger.warning("Failed to collect gateway metrics", error=str(e))
    
    async def _collect_system_metrics(self, timestamp: datetime):
        """Collect system-level metrics."""
        try:
            # System uptime and basic metrics
            import psutil
            
            # CPU and memory
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            self._store_metric("system_cpu_percent", cpu_percent, timestamp)
            self._store_metric("system_memory_percent", memory.percent, timestamp)
            self._store_metric("system_disk_percent", disk.percent, timestamp)
            
        except Exception as e:
            logger.warning("Failed to collect system metrics", error=str(e))
    
    def _store_metric(self, name: str, value: float, timestamp: datetime):
        """Store a metric point."""
        metric_point = MetricPoint(
            name=name,
            value=value,
            timestamp=timestamp
        )
        self.metrics_store[name].append(metric_point)
    
    def get_metrics(self, name: str = None, since: datetime = None) -> List[MetricPoint]:
        """Get stored metrics."""
        if name:
            metrics = list(self.metrics_store.get(name, []))
        else:
            metrics = []
            for metric_name, metric_points in self.metrics_store.items():
                metrics.extend(metric_points)
        
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        
        return sorted(metrics, key=lambda x: x.timestamp)
    
    def get_metric_names(self) -> List[str]:
        """Get all available metric names."""
        return list(self.metrics_store.keys())


class AlertManager:
    """Simple alerting based on thresholds."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules = {
            "high_error_rate": {"metric": "producer_error_rate", "threshold": 0.1, "condition": ">"},
            "high_cpu": {"metric": "system_cpu_percent", "threshold": 80, "condition": ">"},
            "high_memory": {"metric": "system_memory_percent", "threshold": 85, "condition": ">"},
            "unhealthy_brokers": {"metric": "coordinator_brokers_healthy", "threshold": 1, "condition": "<"}
        }
        self.active_alerts: Dict[str, datetime] = {}
        self._check_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start alert checking."""
        self._running = True
        self._check_task = asyncio.create_task(self._check_alerts_loop())
        logger.info("Alert manager started")
    
    async def stop(self):
        """Stop alert checking."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
        logger.info("Alert manager stopped")
    
    async def _check_alerts_loop(self):
        """Periodic alert checking."""
        while self._running:
            try:
                await self._check_all_alerts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error("Error in alert checking", error=str(e))
                await asyncio.sleep(10)
    
    async def _check_all_alerts(self):
        """Check all alert rules."""
        for alert_name, rule in self.alert_rules.items():
            await self._check_alert(alert_name, rule)
    
    async def _check_alert(self, alert_name: str, rule: dict):
        """Check a specific alert rule."""
        try:
            metric_name = rule["metric"]
            threshold = rule["threshold"]
            condition = rule["condition"]
            
            # Get recent metrics
            since = datetime.utcnow() - timedelta(minutes=5)
            metrics = self.metrics_collector.get_metrics(metric_name, since)
            
            if not metrics:
                return
            
            # Get latest value
            latest_metric = metrics[-1]
            value = latest_metric.value
            
            # Check condition
            alert_triggered = False
            if condition == ">":
                alert_triggered = value > threshold
            elif condition == "<":
                alert_triggered = value < threshold
            elif condition == ">=":
                alert_triggered = value >= threshold
            elif condition == "<=":
                alert_triggered = value <= threshold
            
            # Handle alert
            if alert_triggered:
                if alert_name not in self.active_alerts:
                    self.active_alerts[alert_name] = datetime.utcnow()
                    logger.warning(
                        "ALERT TRIGGERED",
                        alert=alert_name,
                        metric=metric_name,
                        value=value,
                        threshold=threshold,
                        condition=condition
                    )
            else:
                if alert_name in self.active_alerts:
                    duration = datetime.utcnow() - self.active_alerts[alert_name]
                    del self.active_alerts[alert_name]
                    logger.info(
                        "ALERT RESOLVED",
                        alert=alert_name,
                        duration_seconds=duration.total_seconds()
                    )
                    
        except Exception as e:
            logger.error("Error checking alert", alert=alert_name, error=str(e))
    
    def get_active_alerts(self) -> Dict[str, dict]:
        """Get currently active alerts."""
        return {
            name: {
                "triggered_at": timestamp.isoformat(),
                "duration_seconds": (datetime.utcnow() - timestamp).total_seconds()
            }
            for name, timestamp in self.active_alerts.items()
        }
    
    def configure_alert(self, name: str, metric: str, threshold: float, condition: str):
        """Configure a new alert rule."""
        self.alert_rules[name] = {
            "metric": metric,
            "threshold": threshold,
            "condition": condition
        }
        logger.info("Alert configured", name=name, metric=metric, threshold=threshold)


class MonitoringService:
    """Main monitoring service."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager(self.metrics_collector)
        self.startup_time = datetime.utcnow()
    
    async def startup(self):
        """Service startup."""
        logger.info("Starting monitoring service")
        await self.metrics_collector.start()
        await self.alert_manager.start()
    
    async def shutdown(self):
        """Service shutdown."""
        logger.info("Shutting down monitoring service")
        await self.alert_manager.stop()
        await self.metrics_collector.stop()


# Global service instance
monitoring_service = MonitoringService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await monitoring_service.startup()
    yield
    await monitoring_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Message Queue Monitoring Service",
    description="Metrics collection and alerting service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/metrics/json", response_model=dict)
async def get_metrics_json(metric: str = None, since_minutes: int = 60):
    """Get metrics in JSON format."""
    try:
        since = datetime.utcnow() - timedelta(minutes=since_minutes)
        metrics = monitoring_service.metrics_collector.get_metrics(metric, since)
        
        return {
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat(),
                    "labels": m.labels
                }
                for m in metrics
            ],
            "count": len(metrics),
            "since": since.isoformat()
        }
    
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/names", response_model=dict)
async def get_metric_names():
    """Get available metric names."""
    try:
        names = monitoring_service.metrics_collector.get_metric_names()
        return {"metric_names": names, "count": len(names)}
    
    except Exception as e:
        logger.error("Failed to get metric names", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/system", response_model=dict)
async def get_system_health():
    """Get aggregated system health."""
    try:
        # Get latest health metrics for all services
        services = ["producer", "consumer", "broker", "coordinator", "gateway"]
        service_health_status = {}
        
        for service in services:
            metrics = monitoring_service.metrics_collector.get_metrics(f"{service}_health")
            if metrics:
                latest = metrics[-1]
                service_health_status[service] = "healthy" if latest.value > 0 else "unhealthy"
            else:
                service_health_status[service] = "unknown"
        
        # Overall system health
        healthy_count = sum(1 for status in service_health_status.values() if status == "healthy")
        total_services = len(services)
        
        if healthy_count == total_services:
            overall_status = "healthy"
        elif healthy_count > total_services / 2:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        # Get active alerts
        active_alerts = monitoring_service.alert_manager.get_active_alerts()
        
        return {
            "overall_status": overall_status,
            "healthy_services": healthy_count,
            "total_services": total_services,
            "service_health": service_health_status,
            "active_alerts": active_alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Failed to get system health", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts", response_model=dict)
async def get_alerts():
    """Get active alerts."""
    try:
        active_alerts = monitoring_service.alert_manager.get_active_alerts()
        alert_rules = monitoring_service.alert_manager.alert_rules
        
        return {
            "active_alerts": active_alerts,
            "alert_rules": alert_rules,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Failed to get alerts", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/configure", response_model=dict)
async def configure_alert(alert_config: dict):
    """Configure a new alert rule."""
    try:
        name = alert_config["name"]
        metric = alert_config["metric"]
        threshold = alert_config["threshold"]
        condition = alert_config.get("condition", ">")
        
        monitoring_service.alert_manager.configure_alert(name, metric, threshold, condition)
        
        return {
            "status": "configured",
            "alert": {
                "name": name,
                "metric": metric,
                "threshold": threshold,
                "condition": condition
            }
        }
    
    except Exception as e:
        logger.error("Failed to configure alert", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard", response_model=dict)
async def get_dashboard_data():
    """Get dashboard data."""
    try:
        # Get recent metrics for dashboard
        since = datetime.utcnow() - timedelta(hours=1)
        
        dashboard_data = {
            "system_overview": {
                "uptime_seconds": (datetime.utcnow() - monitoring_service.startup_time).total_seconds(),
                "collection_interval_ms": Config.SCRAPE_INTERVAL_MS,
                "last_collection": monitoring_service.metrics_collector.last_collection_time.isoformat()
            },
            "key_metrics": {},
            "service_status": {},
            "active_alerts": monitoring_service.alert_manager.get_active_alerts()
        }
        
        # Get key metrics
        key_metric_names = [
            "producer_messages_total",
            "consumer_messages_consumed", 
            "coordinator_brokers_healthy",
            "system_cpu_percent",
            "system_memory_percent"
        ]
        
        for metric_name in key_metric_names:
            metrics = monitoring_service.metrics_collector.get_metrics(metric_name, since)
            if metrics:
                latest = metrics[-1]
                dashboard_data["key_metrics"][metric_name] = {
                    "current_value": latest.value,
                    "timestamp": latest.timestamp.isoformat()
                }
        
        return dashboard_data
    
    except Exception as e:
        logger.error("Failed to get dashboard data", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    try:
        details = {
            "uptime_seconds": (datetime.utcnow() - monitoring_service.startup_time).total_seconds(),
            "metrics_collected": len(monitoring_service.metrics_collector.metrics_store),
            "active_alerts": len(monitoring_service.alert_manager.active_alerts),
            "last_collection": monitoring_service.metrics_collector.last_collection_time.isoformat()
        }
        
        return HealthStatus(
            service="monitoring",
            status=ServiceStatus.HEALTHY,
            details=details
        )
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthStatus(
            service="monitoring",
            status=ServiceStatus.UNHEALTHY,
            details={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.monitoring.server:app",
        host="0.0.0.0",
        port=Config.MONITORING_PORT,
        log_level=Config.LOG_LEVEL.lower()
    )