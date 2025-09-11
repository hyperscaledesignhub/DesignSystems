# Incident Response Workflow Test Guide

This guide documents the comprehensive incident response testing capabilities for the Metrics Monitoring System.

## Overview

The system includes two complementary test scripts that verify all 9 steps of the incident response workflow:

1. **Alert triggered** (e.g., high memory usage)
2. **Email notification sent** to ops team
3. **Webhook triggers** incident management system
4. **Operator opens dashboard**
5. **Views real-time metrics** for affected service
6. **Queries historical data** for context
7. **Takes corrective action**
8. **Alert automatically resolves** when metric normalizes
9. **Resolution notification sent**

## Test Scripts

### 1. `test-incident-response-simple.py`
**Recommended for regular testing**

This script verifies incident response capabilities without complex setup dependencies.

**Features:**
- Quick execution (under 30 seconds)
- Tests all 9 workflow steps
- No external dependencies
- Verifies system readiness
- Generates detailed capability report

**Usage:**
```bash
cd /Users/vijayabhaskarv/python-projects/venv/sysdesign/14-MetricsMonitoring/demo
python3 test-incident-response-simple.py
```

**What it tests:**
- ✅ Alert detection and threshold monitoring
- ✅ Multi-channel notification configuration
- ✅ Webhook integration capability
- ✅ Dashboard accessibility during incidents
- ✅ Real-time metrics access
- ✅ Historical data analysis
- ✅ Corrective action workflow support
- ✅ Automatic alert resolution detection
- ✅ Resolution notification system

### 2. `test-incident-response.py`
**Full end-to-end simulation**

This script creates a realistic incident scenario with actual alert triggering and resolution.

**Features:**
- Complete incident lifecycle simulation
- Mock SMTP and webhook servers
- High-load metrics source simulation
- Real alert triggering and resolution
- Email and webhook notification capture
- Comprehensive incident report

**Usage:**
```bash
cd /Users/vijayabhaskarv/python-projects/venv/sysdesign/14-MetricsMonitoring/demo
python3 test-incident-response.py
```

**What it simulates:**
1. Starts mock notification servers (SMTP on port 1025, webhook on port 8080)
2. Creates high-load metrics source triggering real alerts
3. Captures email and webhook notifications
4. Tests dashboard access during incident
5. Verifies real-time and historical data access
6. Simulates corrective action by normalizing metrics
7. Waits for automatic alert resolution
8. Verifies resolution notifications

## System Architecture

The incident response system consists of:

- **Alert Manager** (`http://localhost:6428`) - Monitors thresholds and triggers alerts
- **Query Service** (`http://localhost:7539`) - Provides real-time and historical data
- **Dashboard** (`http://localhost:5317`) - Web interface for operators
- **Metrics Source** (`http://localhost:3000`) - Simulated application metrics

## Alert Rules Configuration

The system uses `/Users/vijayabhaskarv/python-projects/venv/sysdesign/14-MetricsMonitoring/demo/alert-rules.yaml` with rules for:

- **CPU Usage** > 80% (critical)
- **Memory Usage** > 85% (warning)  
- **Disk Usage** > 90% (critical)
- **Service Health** failures (critical)
- **Test Rule** > 30% CPU (info - for testing)

## Notification Channels

### Email Notifications
- SMTP configuration via environment variables
- Automatic alerts for threshold breaches
- Resolution notifications when metrics normalize
- Configurable recipient lists per alert rule

### Webhook Notifications  
- HTTP POST to configured webhook URLs
- JSON payload with alert details and metadata
- Integration with external incident management systems
- Automatic resolution updates

## Test Results Interpretation

### Successful Test Output
```
🏁 Incident Response Verification: 9/9 capabilities verified
🎉 INCIDENT RESPONSE SYSTEM VERIFIED!
🟢 System Status: OPERATIONAL - Ready for production incidents
```

### Partial Failure Output
```
🏁 Incident Response Verification: 7/9 capabilities verified
⚠️ Some incident response capabilities may be compromised
🟡 System Status: NEEDS ATTENTION - Some capabilities may be limited
```

## Key Capabilities Verified

### 1. Alert Detection & Triggering
- Threshold monitoring across multiple metrics
- Configurable alert rules with severity levels
- Duration-based alerting to prevent false positives

### 2. Multi-Channel Notifications
- Email alerts to operations teams
- Webhook integration with incident management
- Configurable notification routing

### 3. Real-Time Monitoring
- Live metrics access during incidents
- WebSocket updates for dashboard
- Sub-second response times via Redis caching

### 4. Historical Context Analysis
- Time-series queries for incident context
- Multiple time range analysis (30m, 1h, 6h)
- Trend analysis for root cause identification

### 5. Corrective Action Support
- Dashboard access during incidents
- Real-time metrics for impact assessment
- Historical data for informed decision making

### 6. Automatic Resolution
- Continuous monitoring of alert conditions
- Automatic resolution when metrics normalize
- Resolution notifications to close incident loop

## Troubleshooting

### Common Issues

**Dashboard Not Accessible**
```bash
# Check dashboard service
curl http://localhost:5317/health
```

**Metrics Not Available**
```bash
# Check query service
curl http://localhost:7539/health
```

**Alerts Not Triggering**
```bash
# Check alert manager
curl http://localhost:6428/alerts/active
```

**No Historical Data**
```bash
# Verify metrics collection
curl "http://localhost:7539/query/latest/cpu_usage_percent"
```

### Service Dependencies

The incident response system requires:
1. **InfluxDB** - Time-series database for metrics storage
2. **Redis** - Caching layer for query performance
3. **Kafka** - Message streaming for metrics collection
4. **Alert Manager** - Alert evaluation and notification
5. **Query Service** - Metrics API and aggregation
6. **Dashboard** - Web interface for operators

## Production Considerations

### Monitoring
- Regular testing with `test-incident-response-simple.py`
- Periodic full workflow testing with `test-incident-response.py`
- Health checks for all system components

### Scaling
- Alert evaluation can be scaled horizontally
- Query service supports read replicas
- Dashboard supports multiple concurrent operators

### Security
- Webhook endpoints should use HTTPS in production
- SMTP credentials should be properly secured
- Dashboard access should require authentication

## Metrics and KPIs

The system tracks incident response effectiveness:

- **Mean Time to Detection (MTTD)** - Alert triggering speed
- **Mean Time to Notification (MTTN)** - Notification delivery
- **Mean Time to Resolution (MTTR)** - End-to-end incident lifecycle
- **Dashboard Availability** - System uptime during incidents
- **Query Performance** - Response times for metrics access

## Integration Examples

### Webhook Payload Format
```json
{
  "alert": {
    "rule_name": "high_cpu_usage",
    "metric_name": "cpu_usage_percent", 
    "current_value": 85.5,
    "threshold": 80.0,
    "severity": "critical",
    "message": "CPU usage is above 80% threshold",
    "labels": {
      "team": "infrastructure",
      "service": "monitoring"
    }
  },
  "timestamp": "2025-09-10T12:00:00Z"
}
```

### Email Alert Format
```
Subject: ALERT: high_cpu_usage - CRITICAL

Alert: high_cpu_usage
Severity: CRITICAL
Metric: cpu_usage_percent
Current Value: 85.5
Threshold: 80.0
Message: CPU usage is above 80% threshold
Started: 2025-09-10T12:00:00Z
```

## Testing Best Practices

1. **Regular Testing** - Run capability tests weekly
2. **Full Simulation** - Monthly end-to-end testing
3. **Notification Verification** - Ensure delivery channels work
4. **Dashboard Testing** - Verify operator access during incidents
5. **Performance Monitoring** - Track query response times
6. **Resolution Testing** - Verify automatic alert resolution

This comprehensive testing framework ensures the incident response system is ready to handle production alerts effectively, giving operators the tools they need to respond quickly and accurately to system issues.