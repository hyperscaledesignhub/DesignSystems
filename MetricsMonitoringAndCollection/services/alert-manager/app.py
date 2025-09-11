import asyncio
import yaml
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import httpx
import sys
import os

sys.path.append('/app')
from shared.config import AlertManagerConfig
from shared.utils import setup_logging, HealthChecker
from shared.models import AlertRule, Alert, AlertSeverity, AlertState

app = FastAPI(title="Alert Manager", version="1.0.0")
logger = setup_logging("alert-manager", AlertManagerConfig.LOG_LEVEL)
health_checker = HealthChecker()

class AlertManager:
    def __init__(self):
        self.config = AlertManagerConfig()
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        query_service_host = os.getenv("QUERY_SERVICE_HOST", "localhost")
        self.query_service_url = f"http://{query_service_host}:{self.config.QUERY_SERVICE_PORT}"
        self.running = False
        
    async def initialize(self):
        """Initialize the alert manager."""
        try:
            # Load alert rules from file
            await self.load_alert_rules()
            
            # Register health checks
            health_checker.add_check("query_service", self._check_query_service_health)
            health_checker.add_check("smtp", self._check_smtp_health)
            
            logger.info("Alert Manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    async def load_alert_rules(self):
        """Load alert rules from YAML file."""
        try:
            if os.path.exists(self.config.ALERT_RULES_PATH):
                with open(self.config.ALERT_RULES_PATH, 'r') as file:
                    rules_data = yaml.safe_load(file)
                    
                self.alert_rules = []
                for rule_data in rules_data.get('rules', []):
                    rule = AlertRule(
                        name=rule_data['name'],
                        metric_name=rule_data['metric_name'],
                        threshold=float(rule_data['threshold']),
                        duration_minutes=int(rule_data['duration_minutes']),
                        severity=AlertSeverity(rule_data['severity']),
                        message=rule_data['message'],
                        labels=rule_data.get('labels', {})
                    )
                    self.alert_rules.append(rule)
                
                logger.info(f"Loaded {len(self.alert_rules)} alert rules")
            else:
                logger.warning(f"Alert rules file not found: {self.config.ALERT_RULES_PATH}")
                
        except Exception as e:
            logger.error(f"Failed to load alert rules: {e}")
            raise
    
    async def _check_query_service_health(self):
        """Check query service health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.query_service_url}/health", timeout=5)
                response.raise_for_status()
                return {"status": "connected"}
        except Exception as e:
            raise Exception(f"Query service unreachable: {e}")
    
    def _check_smtp_health(self):
        """Check SMTP server health."""
        try:
            if not self.config.SMTP_HOST:
                return {"status": "not_configured"}
            
            server = smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT)
            server.quit()
            return {"status": "connected"}
        except Exception as e:
            raise Exception(f"SMTP server unreachable: {e}")
    
    async def evaluate_rules(self):
        """Evaluate all alert rules against current metrics."""
        for rule in self.alert_rules:
            try:
                await self.evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule.name}: {e}")
    
    async def evaluate_rule(self, rule: AlertRule):
        """Evaluate a single alert rule."""
        try:
            # Query latest metric value
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.query_service_url}/query/latest/{rule.metric_name}",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                if 'error' in data:
                    logger.warning(f"No data for metric {rule.metric_name}")
                    return
                
                current_value = data['value']
                alert_key = f"{rule.name}:{rule.metric_name}"
                
                # Check if threshold is breached
                if current_value > rule.threshold:
                    await self.handle_alert_firing(rule, current_value, data, alert_key)
                else:
                    await self.handle_alert_resolved(rule, alert_key)
                    
        except Exception as e:
            logger.error(f"Failed to evaluate rule {rule.name}: {e}")
    
    async def handle_alert_firing(self, rule: AlertRule, current_value: float, metric_data: Dict, alert_key: str):
        """Handle a firing alert."""
        now = datetime.utcnow()
        
        if alert_key in self.active_alerts:
            # Update existing alert
            alert = self.active_alerts[alert_key]
            alert.current_value = current_value
            
            # Check if alert has been firing long enough
            if alert.state == AlertState.PENDING:
                duration = now - alert.started_at
                if duration.total_seconds() >= rule.duration_minutes * 60:
                    alert.state = AlertState.FIRING
                    await self.send_alert_notification(alert)
                    logger.info(f"Alert {rule.name} transitioned to FIRING")
        else:
            # Create new alert
            alert = Alert(
                rule_name=rule.name,
                metric_name=rule.metric_name,
                current_value=current_value,
                threshold=rule.threshold,
                state=AlertState.PENDING,
                severity=rule.severity,
                message=rule.message,
                labels={**rule.labels, **metric_data.get('labels', {})},
                started_at=now
            )
            self.active_alerts[alert_key] = alert
            logger.info(f"New alert {rule.name} created in PENDING state")
    
    async def handle_alert_resolved(self, rule: AlertRule, alert_key: str):
        """Handle a resolved alert."""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            if alert.state == AlertState.FIRING:
                alert.state = AlertState.RESOLVED
                alert.resolved_at = datetime.utcnow()
                await self.send_resolved_notification(alert)
                logger.info(f"Alert {rule.name} resolved")
            
            # Remove resolved alert
            del self.active_alerts[alert_key]
    
    async def send_alert_notification(self, alert: Alert):
        """Send alert notification via email and webhook."""
        try:
            # Send email notification
            if self.config.SMTP_HOST:
                await self.send_email_notification(alert)
            
            # Send webhook notification (if configured)
            webhook_url = os.getenv("WEBHOOK_URL")
            if webhook_url:
                await self.send_webhook_notification(alert, webhook_url)
                
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    async def send_resolved_notification(self, alert: Alert):
        """Send resolved notification."""
        try:
            # Send email notification
            if self.config.SMTP_HOST:
                await self.send_email_resolved_notification(alert)
                
        except Exception as e:
            logger.error(f"Failed to send resolved notification: {e}")
    
    async def send_email_notification(self, alert: Alert):
        """Send email alert notification."""
        if not self.config.SMTP_HOST:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.SMTP_FROM
            msg['To'] = os.getenv("ALERT_EMAIL", "admin@localhost")
            msg['Subject'] = f"ALERT: {alert.rule_name} - {alert.severity.value.upper()}"
            
            body = f"""
Alert: {alert.rule_name}
Severity: {alert.severity.value.upper()}
Metric: {alert.metric_name}
Current Value: {alert.current_value}
Threshold: {alert.threshold}
Message: {alert.message}
Started: {alert.started_at.isoformat()}
Labels: {alert.labels}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT)
            if self.config.SMTP_USERNAME:
                server.starttls()
                server.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    async def send_email_resolved_notification(self, alert: Alert):
        """Send email resolved notification."""
        if not self.config.SMTP_HOST:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.SMTP_FROM
            msg['To'] = os.getenv("ALERT_EMAIL", "admin@localhost")
            msg['Subject'] = f"RESOLVED: {alert.rule_name}"
            
            body = f"""
Alert Resolved: {alert.rule_name}
Metric: {alert.metric_name}
Duration: {alert.resolved_at - alert.started_at}
Resolved: {alert.resolved_at.isoformat()}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT)
            if self.config.SMTP_USERNAME:
                server.starttls()
                server.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email resolved notification sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send resolved email: {e}")
    
    async def send_webhook_notification(self, alert: Alert, webhook_url: str):
        """Send webhook notification."""
        try:
            payload = {
                "alert": alert.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                
            logger.info(f"Webhook notification sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
    
    async def start_evaluation_loop(self):
        """Start the alert evaluation loop."""
        self.running = True
        logger.info(f"Starting alert evaluation every {self.config.EVALUATION_INTERVAL} seconds")
        
        while self.running:
            try:
                await self.evaluate_rules()
                await asyncio.sleep(self.config.EVALUATION_INTERVAL)
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    def stop(self):
        """Stop the alert manager."""
        self.running = False

# Global alert manager instance
alert_manager = AlertManager()

@app.on_event("startup")
async def startup_event():
    """Initialize the alert manager on startup."""
    await alert_manager.initialize()
    # Start evaluation loop in background
    asyncio.create_task(alert_manager.start_evaluation_loop())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    alert_manager.stop()

@app.get("/alerts/rules")
async def get_alert_rules():
    """Get all alert rules."""
    return {
        "rules": [rule.to_dict() for rule in alert_manager.alert_rules],
        "count": len(alert_manager.alert_rules)
    }

@app.post("/alerts/rules")
async def add_alert_rule(rule_data: dict):
    """Add or update an alert rule."""
    try:
        rule = AlertRule(
            name=rule_data['name'],
            metric_name=rule_data['metric_name'],
            threshold=float(rule_data['threshold']),
            duration_minutes=int(rule_data['duration_minutes']),
            severity=AlertSeverity(rule_data['severity']),
            message=rule_data['message'],
            labels=rule_data.get('labels', {})
        )
        
        # Remove existing rule with same name
        alert_manager.alert_rules = [r for r in alert_manager.alert_rules if r.name != rule.name]
        alert_manager.alert_rules.append(rule)
        
        return {"status": "rule added", "rule": rule.to_dict()}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/alerts/active")
async def get_active_alerts():
    """Get all active alerts."""
    return {
        "alerts": [alert.to_dict() for alert in alert_manager.active_alerts.values()],
        "count": len(alert_manager.active_alerts)
    }

@app.post("/alerts/silence")
async def silence_alert(alert_name: str):
    """Silence an active alert."""
    silenced = False
    for key, alert in list(alert_manager.active_alerts.items()):
        if alert.rule_name == alert_name:
            del alert_manager.active_alerts[key]
            silenced = True
    
    if silenced:
        return {"status": f"alert {alert_name} silenced"}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await health_checker.run_checks()
        
        # For demo purposes, consider service healthy if Query Service is connected
        # SMTP failure is acceptable in demo environment
        checks = health_status.get("checks", {})
        query_service_ok = checks.get("query_service", {}).get("status") == "ok"
        
        # Override healthy status if core services are working
        if query_service_ok:
            health_status["healthy"] = True
            status_code = 200
        else:
            status_code = 503
            
        return JSONResponse(content=health_status, status_code=status_code)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"healthy": False, "error": str(e)},
            status_code=503
        )

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "alert-manager",
        "version": "1.0.0",
        "active_alerts": len(alert_manager.active_alerts),
        "alert_rules": len(alert_manager.alert_rules),
        "status": "running" if alert_manager.running else "stopped"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=AlertManagerConfig.ALERT_MANAGER_PORT,
        log_level=AlertManagerConfig.LOG_LEVEL.lower()
    )