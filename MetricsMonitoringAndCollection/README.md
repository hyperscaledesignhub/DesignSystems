# 📊 Metrics Monitoring System - Interactive Demo

## Overview

This demo showcases a production-ready metrics monitoring system with all services running as individual Docker containers. The system demonstrates comprehensive monitoring, alerting, and visualization capabilities through an interactive web interface.

## 🚀 Quick Start

### Prerequisites
- Docker installed and running
- 8GB+ RAM available
- Ports 2379, 2181, 5317, 6379, 6428, 7539, 8026, 8080, 9293, 9847, 4692 available

### Start the Demo

```bash
# Make scripts executable
chmod +x demo/scripts/*.sh

# Start all services
./demo/scripts/startup.sh

# Access the demo UI
open http://localhost:8080
```

### Stop the Demo

```bash
./demo/scripts/stop.sh
```

## 🏗️ Architecture

All services run as individual Docker containers connected via a custom network:

```
demo-etcd          : Service discovery (Port 2379)
demo-redis         : Cache layer (Port 6379)
demo-zookeeper     : Kafka coordination (Port 2181)
demo-kafka         : Message queue (Port 9293)
demo-influxdb      : Time-series database (Port 8026)
demo-metrics-collector : Metrics collection (Port 9847)
demo-data-consumer : Data processing (Port 4692)
demo-query-service : Query API (Port 7539)
demo-alert-manager : Alert management (Port 6428)
demo-dashboard     : Main dashboard (Port 5317)
demo-ui           : Interactive demo UI (Port 8080)
```

## 🎯 Demo Features

### Interactive Demo UI (http://localhost:8080)

The demo UI provides:

1. **Service Status Panel** - Real-time health monitoring of all services
2. **Workflow Demonstrations** - Step-by-step visualization of:
   - Metric Collection Flow
   - Alert Trigger Flow
   - Dashboard Query Flow
   - Service Discovery Flow
   - Historical Query Flow

3. **Live Metrics Display** - Real-time chart updates with generated data
4. **Alert Management** - Trigger and resolve test alerts
5. **Feature Showcase** - Interactive demos of each component
6. **System Performance** - Live performance metrics
7. **System Console** - Real-time activity log

### Main Dashboard (http://localhost:5317)

The production dashboard provides:
- Real-time metric visualization
- Multiple chart types
- Alert status monitoring
- WebSocket live updates

## 📝 Supported Workflows

### 1. Metric Collection Flow
```
Service Registration → Discovery → Pull Metrics → Send to Kafka → Store in InfluxDB
```

### 2. Alert Workflow
```
Load Rules → Query Metrics → Evaluate → Create Alert → Send Notifications
```

### 3. Dashboard Query
```
Request → Check Cache → Query DB → Cache Result → Display
```

### 4. Service Discovery
```
Service Startup → Register with etcd → Collector Notified → Update Targets → Start Collection
```

### 5. Historical Query
```
Request → Check Retention → Fetch Aggregated → Downsample → Return Results
```

## 🧪 Testing with Data Generator

Generate realistic test data:

```bash
# Basic generation
python demo/data/generator.py

# Continuous generation of specific metrics
python demo/data/generator.py --types cpu memory network --interval 5

# Run scenario simulations
python demo/data/generator.py --mode scenario
```

Available scenarios:
- Normal load
- Traffic spike
- Memory leak
- Disk full
- Network issues
- Database slowdown

## 🔧 Individual Service Management

### Check Service Status
```bash
docker ps | grep demo-
```

### View Service Logs
```bash
docker logs demo-metrics-collector
docker logs demo-alert-manager
docker logs demo-query-service
```

### Restart Individual Service
```bash
docker restart demo-metrics-collector
```

### Access Service Health Endpoints
```bash
curl http://localhost:9847/health  # Metrics Collector
curl http://localhost:7539/health  # Query Service
curl http://localhost:6428/health  # Alert Manager
```

## 📊 Service Endpoints

### Metrics Collector (9847)
- `GET /health` - Health check
- `GET /api/metrics` - Current metrics
- `POST /api/metrics` - Submit metrics

### Query Service (7539)
- `GET /health` - Health check
- `GET /api/metrics` - Query metrics
- `GET /api/metrics/aggregated` - Aggregated data

### Alert Manager (6428)
- `GET /health` - Health check
- `GET /api/alerts` - Current alerts
- `POST /api/alerts/test` - Trigger test alert

### Demo UI (8080)
- `GET /` - Interactive demo interface
- `GET /api/status` - Service status
- `POST /api/demo/workflow/:name` - Run workflow demo
- `POST /api/demo/generate-data` - Start data generation

## 🎨 Demo UI Features

### Service Monitoring
- Real-time health checks every 10 seconds
- Visual status indicators (green = healthy, red = unhealthy)
- Port and connection information

### Workflow Visualization
- Step-by-step execution display
- Timing and data flow visualization
- Console logging of all activities

### Live Metrics
- Real-time chart updates via WebSocket
- Multiple metric types (CPU, Memory, Network, Errors)
- Configurable data generation

### Alert Management
- Trigger warning and critical alerts
- View active alerts
- Resolve alerts with one click

### Performance Metrics
- Metrics collected counter
- Queries per second
- Active alerts count
- Cache hit rate

## 🛠️ Troubleshooting

### Service Won't Start
```bash
# Check if port is in use
lsof -i :9847  # Replace with service port

# Check Docker logs
docker logs demo-metrics-collector

# Restart individual service
docker restart demo-metrics-collector
```

### Connection Issues
```bash
# Verify network exists
docker network ls | grep metrics-network

# Check service connectivity
docker exec demo-metrics-collector ping demo-kafka
```

### Data Not Flowing
```bash
# Check Kafka topics
docker exec demo-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check InfluxDB
curl -XGET "http://localhost:8026/api/v2/buckets" \
  -H "Authorization: Token demo-token-123"
```

## 📈 Performance Optimization

### Resource Limits
Each container runs with default Docker resources. For production:

```bash
# Add to docker run commands:
--memory="1g" --cpus="0.5"
```

### Scaling Services
```bash
# Run multiple instances
docker run -d --name demo-metrics-collector-2 ...
docker run -d --name demo-data-consumer-2 ...
```

## 🔍 Monitoring the Demo

### Container Stats
```bash
docker stats $(docker ps -q --filter "name=demo-")
```

### Network Traffic
```bash
docker network inspect metrics-network
```

### Volume Usage
```bash
docker system df
```

## 🎯 Key Capabilities Demonstrated

- **Scale**: 10M+ metrics/day processing
- **Performance**: Sub-second query response
- **Reliability**: Automatic retry and error handling
- **Flexibility**: Multiple metric types and sources
- **Visualization**: Real-time charts and dashboards
- **Alerting**: Threshold-based with multiple channels
- **Caching**: Redis-powered query optimization
- **Storage**: Time-series optimized with retention policies

## 📚 Additional Resources

- [System Overview](../SYSTEM_OVERVIEW.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)
- [UI Guide](../UI_GUIDE.md)

## 🤝 Contributing

To extend the demo:

1. Add new metric types in `data/generator.py`
2. Create new workflow demos in `ui/server.js`
3. Enhance visualizations in `ui/public/demo.js`
4. Add new scenarios for testing

## 📝 License

This demo is part of the Metrics Monitoring System project and follows the same license terms.