# AdClick Demo System

A comprehensive demo system showcasing the Ad Click Event Aggregation platform with a React UI and enhanced backend services for customer demonstrations.

## 🚀 Quick Start

```bash
cd demo
docker-compose up -d
```

Visit http://localhost:3000 to access the demo dashboard.

## 🎯 Demo Use Cases

### 1. Real-time Ad Performance Dashboard
- Live click tracking and metrics
- Top performing ads visualization
- Geographic distribution of clicks
- Real-time event stream monitoring

### 2. Campaign Analytics
- Campaign performance comparison
- Click-through rate analysis
- Time-based trend analysis
- A/B testing results visualization

### 3. Fraud Detection Showcase
- Suspicious click pattern detection
- IP-based anomaly detection
- Geographic anomaly visualization
- Real-time fraud alerts

### 4. Business Intelligence
- Revenue impact visualization
- Cost-per-click optimization
- ROI analysis by campaign
- Predictive analytics

### 5. System Health Monitoring
- Service health dashboards
- Performance metrics visualization
- Alert management system
- System capacity monitoring

## 🏗️ Architecture

```
[Demo UI (React)] ← → [Demo API Gateway] ← → [Core Services]
       ↓                      ↓                    ↓
[WebSocket Client]    [Event Simulator]    [Original AdClick System]
```

## 📊 Demo Features

- **Interactive Dashboard**: Real-time metrics and visualizations
- **Live Event Simulation**: Generate realistic ad click events
- **Multiple Demo Scenarios**: Pre-configured use cases
- **Real-time Updates**: WebSocket-based live data
- **Export Capabilities**: Download reports and data
- **Admin Panel**: Control demo parameters and scenarios

## 🛠️ Services

| Service | Port | Purpose |
|---------|------|---------|
| Demo UI | 3000 | React dashboard |
| Demo API | 8900 | Enhanced query service |
| Event Simulator | 8901 | Generate test data |
| WebSocket Server | 8902 | Real-time updates |

## 🎬 Running Demos

1. **Start the system**: `docker-compose up -d`
2. **Open dashboard**: http://localhost:3000
3. **Select demo scenario** from the dropdown
4. **Start data simulation** using the control panel
5. **Showcase features** using different tabs

## 📈 Demo Scenarios

### Scenario 1: E-commerce Holiday Sale
- High-volume click events
- Multiple campaigns running
- Geographic targeting showcase
- Real-time bidding simulation

### Scenario 2: Mobile Gaming Campaign
- Gaming app ad clicks
- User behavior analytics
- Fraud detection patterns
- Performance optimization

### Scenario 3: Financial Services
- Conservative click patterns
- Compliance monitoring
- Risk assessment tools
- ROI optimization focus

### Scenario 4: Social Media Platform
- Viral campaign effects
- Influencer marketing impact
- Demographic targeting
- Real-time engagement metrics

## 🔧 Configuration

Environment variables in `demo/.env`:
- `DEMO_MODE=true`
- `SIMULATION_SPEED=1x` (1x, 2x, 5x, 10x)
- `DEFAULT_SCENARIO=ecommerce`
- `AUTO_START_SIMULATION=false`

## 🎯 Customer Demo Script

1. **Introduction** (2 min)
   - Show system architecture
   - Explain core capabilities

2. **Live Demo** (15 min)
   - Start with real-time dashboard
   - Demonstrate different use cases
   - Show fraud detection in action
   - Highlight scalability features

3. **Deep Dive** (10 min)
   - System health monitoring
   - Performance metrics
   - Alert management

4. **Q&A and Customization** (5 min)
   - Address specific requirements
   - Discuss implementation timeline

## 🔍 Monitoring URLs

- Demo Dashboard: http://localhost:3000
- API Health: http://localhost:8900/health
- System Metrics: http://localhost:8900/metrics
- WebSocket Status: http://localhost:8902/status