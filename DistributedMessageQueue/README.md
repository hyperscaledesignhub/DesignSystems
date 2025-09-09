# Distributed Message Queue Demo

## Overview
This demo showcases a fully functional distributed message queue system with individual Docker containers for each service.

## Architecture
- **3 Broker Instances** - Message storage with replication
- **1 Producer Service** - Sends messages to topics
- **2 Consumer Instances** - Consume messages in groups
- **1 Coordinator Service** - Manages cluster coordination
- **1 API Gateway** - Unified API entry point
- **1 Monitoring Service** - Metrics and health monitoring
- **1 UI Dashboard** - Interactive demo interface

## Quick Start

### Prerequisites
- Docker installed and running
- Port range 8080, 19001-19006 available

### Start All Services
```bash
cd demo
./scripts/startup.sh
```

### Access the Demo
Open your browser to: **http://localhost:8080**

### Stop All Services
```bash
./scripts/stop.sh
```

## Demo Features

### 1. Basic Operations
- Create topics with partitions
- Produce messages (single and batch)
- Consume messages with consumer groups
- Monitor system metrics in real-time

### 2. Distributed Features
- **Partitioning**: Messages distributed across 3 partitions
- **Replication**: 3-way replication for fault tolerance
- **Consumer Groups**: Load-balanced consumption
- **Offset Management**: Track consumption progress

### 3. UI Dashboard Features
- Real-time metrics display
- Interactive demo controls
- Activity log visualization
- System health monitoring
- WebSocket-based live updates

## Service Ports
- **UI Dashboard**: http://localhost:8080
- **API Gateway**: http://localhost:19005
- **Monitoring**: http://localhost:19006
- **Coordinator**: http://localhost:19004
- **Broker 1**: http://localhost:19001
- **Broker 2**: http://localhost:19002
- **Broker 3**: http://localhost:19003
- **Producer**: http://localhost:19002
- **Consumer 1**: http://localhost:19003
- **Consumer 2**: http://localhost:19004

## Demo Workflow

### Step 1: Initialize System
1. Click "Create Demo Topics" to create sample topics
2. Verify topics are created in the metrics panel

### Step 2: Produce Messages
1. Select a topic from the dropdown
2. Click "Produce Messages" to send 10 messages
3. Or click "Produce Batch" for 100 messages
4. Watch the message counter increase

### Step 3: Consume Messages
1. Select a topic to consume from
2. Click "Consume Messages" to pull messages
3. Or use "Start Auto-Consume" for continuous consumption
4. Messages appear in the activity log

### Step 4: Advanced Features
- **Demo Partitioning**: Shows message distribution
- **Demo Replication**: Demonstrates fault tolerance
- **Demo Consumer Groups**: Shows load balancing
- **Simulate Failure**: Explains failure handling

## Docker Management

### View Running Containers
```bash
docker ps --filter "name=msgqueue-"
```

### View Container Logs
```bash
# View broker logs
docker logs msgqueue-broker-1

# View producer logs
docker logs msgqueue-producer

# View UI logs
docker logs msgqueue-ui
```

### Clean Up Everything
```bash
# Stop and remove containers
./scripts/stop.sh

# Remove Docker images
docker rmi msgqueue-ui msgqueue-monitoring msgqueue-gateway \
           msgqueue-consumer msgqueue-producer msgqueue-broker \
           msgqueue-coordinator

# Remove data volumes
docker volume rm msgqueue-broker-data-1 msgqueue-broker-data-2 msgqueue-broker-data-3
```

## Troubleshooting

### Port Already in Use
If you get port binding errors, check for conflicting services:
```bash
lsof -i :8080
lsof -i :19001-19006
```

### Container Won't Start
Check container logs:
```bash
docker logs msgqueue-[service-name]
```

### Network Issues
Recreate the network:
```bash
docker network rm msgqueue-network
docker network create msgqueue-network
```

## Implementation Details

### Technologies Used
- **Backend**: Python with FastAPI
- **Storage**: File-based WAL (Write-Ahead Log)
- **Communication**: REST APIs over HTTP
- **UI**: HTML5 with WebSocket for real-time updates
- **Containerization**: Docker with individual containers

### Key Features Implemented
✅ Topic and partition management  
✅ Message production with batching  
✅ Consumer groups with offset tracking  
✅ Basic replication (3 replicas)  
✅ Pull-based consumption model  
✅ API Gateway with rate limiting  
✅ Monitoring and metrics collection  
✅ Interactive web UI dashboard  

### Features Not Included (MVP Scope)
❌ Complex ISR algorithms  
❌ Message compression/encryption  
❌ Zero-copy optimizations  
❌ Exactly-once delivery semantics  
❌ Dynamic partition scaling  
❌ SSL/TLS security  
❌ Advanced failure recovery  

## Support
For issues or questions, check the container logs or restart the services using the stop and startup scripts.