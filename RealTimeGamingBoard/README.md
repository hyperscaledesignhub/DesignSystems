# 🎮 Real-time Gaming Leaderboard - Demo System

## Overview

This demo showcases a comprehensive real-time gaming leaderboard system built with microservices architecture, featuring distributed tracing, real-time WebSocket updates, tournament management, and stress testing capabilities.

## 🚀 Quick Start

```bash
# Start the entire demo system
./demo/start-demo.sh

# Or manually with docker-compose
cd demo
docker-compose up -d
```

## 🏗️ Architecture

### Microservices

1. **User Service** (Port 23451)
   - User registration and authentication
   - Profile management
   - JWT token generation

2. **Game Service** (Port 23452)
   - Game catalog management
   - Game metadata and rules

3. **Leaderboard Service** (Port 23453)
   - Real-time ranking calculations
   - Global and per-game leaderboards
   - Caching with Redis

4. **Score Service** (Port 23454)
   - Score submission and validation
   - Score history tracking
   - Integration with leaderboard updates

5. **API Gateway** (Port 23455)
   - Central entry point for all services
   - Request routing and authentication
   - Service orchestration

6. **WebSocket Service** (Port 23456)
   - Real-time event streaming
   - Live score updates
   - Tournament notifications

7. **Tournament Service** (Port 23457)
   - Tournament creation and management
   - Player registration
   - Prize distribution

8. **Demo Generator** (Port 23458)
   - Automated data generation
   - Simulation of player activities
   - Stress testing capabilities

### Infrastructure

- **PostgreSQL**: Primary database for all services
- **Redis**: Caching and pub/sub messaging
- **Jaeger**: Distributed tracing
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization

## 📊 Demo Use Cases

### 1. Live Leaderboard
- Real-time score updates
- Global rankings across all games
- Per-game leaderboards
- Player statistics

### 2. Tournament System
- Create and join tournaments
- Real-time tournament standings
- Automated prize distribution
- Multiple tournament formats

### 3. Real-time Updates
- WebSocket-based live feed
- Score update notifications
- Tournament progress tracking
- System-wide event streaming

### 4. Stress Testing
- Configurable load generation
- Concurrent user simulation
- Performance metrics tracking
- System behavior under load

### 5. Distributed Tracing
- Request flow visualization
- Service dependency mapping
- Performance bottleneck identification
- Error tracking and debugging

## 🔍 Accessing the Demo

### Web Interfaces
- **Demo UI**: http://localhost:3000
- **Jaeger Tracing**: http://localhost:16686
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

### API Endpoints

#### User Management
```bash
# Register new user
curl -X POST http://localhost:23455/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"username":"player1","email":"player1@demo.com","password":"demo123"}'

# Login
curl -X POST http://localhost:23455/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"username":"player1","password":"demo123"}'
```

#### Score Submission
```bash
# Submit score
curl -X POST http://localhost:23455/api/v1/scores \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id":"<user_id>","game_id":"<game_id>","score":1000}'
```

#### Leaderboard
```bash
# Get global leaderboard
curl http://localhost:23455/api/v1/leaderboard/global

# Get game-specific leaderboard
curl http://localhost:23455/api/v1/leaderboard/game/<game_id>
```

#### Tournaments
```bash
# List tournaments
curl http://localhost:23455/api/v1/tournaments

# Create tournament
curl -X POST http://localhost:23455/api/v1/tournaments \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Weekend Championship",
    "game_id":"<game_id>",
    "max_participants":100,
    "prize_pool":5000,
    "start_time":"2024-01-01T10:00:00Z",
    "end_time":"2024-01-01T14:00:00Z"
  }'

# Join tournament
curl -X POST http://localhost:23455/api/v1/tournaments/register \
  -H "Content-Type: application/json" \
  -d '{"tournament_id":"<tournament_id>","user_id":"<user_id>"}'
```

### WebSocket Connection

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:23456/ws/main');

// Subscribe to channels
ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['leaderboard', 'tournament', 'game', 'score']
}));

// Handle messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## 🧪 Testing Scenarios

### 1. Basic Flow Test
1. Open Demo UI (http://localhost:3000)
2. Click "Populate Demo Data"
3. Click "Start Simulation"
4. Observe real-time updates in Live Feed

### 2. Tournament Test
1. Navigate to Tournaments tab
2. Click "Create Tournament"
3. Join tournament with different users
4. Watch real-time standings update

### 3. Stress Test
1. Navigate to Stress Testing tab
2. Set concurrent users (100-1000)
3. Set actions per second (10-100)
4. Click "Start Stress Test"
5. Monitor throughput and system behavior

### 4. Tracing Analysis
1. Perform various actions in the UI
2. Open Jaeger (http://localhost:16686)
3. Select a service and find traces
4. Analyze request flow and latencies

## 📈 Monitoring

### Jaeger Tracing
- View distributed traces across all services
- Identify performance bottlenecks
- Track error propagation
- Analyze service dependencies

### Prometheus Metrics
- Service health metrics
- Request rates and latencies
- Database connection pools
- Cache hit rates

### Grafana Dashboards
- Real-time metrics visualization
- Custom dashboards for each service
- Alert configuration
- Historical trend analysis

## 🛠️ Development

### Adding New Features

1. **New Service**: Create service in `demo/services/`
2. **Add Tracing**: Import and setup tracing from `shared/tracing.py`
3. **Update Docker Compose**: Add service to `docker-compose.yml`
4. **Update API Gateway**: Add routing in gateway configuration

### Running Individual Services

```bash
# Start only infrastructure
docker-compose up postgres redis jaeger -d

# Run specific service locally
cd demo/services/<service-name>
pip install -r requirements.txt
python main.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**
   - Check Docker memory allocation (minimum 4GB recommended)
   - Ensure ports 23451-23458, 3000, 3001, 9090, 16686 are available

2. **Database connection errors**
   - Wait for PostgreSQL to fully initialize
   - Check DATABASE_URL in docker-compose.yml

3. **WebSocket connection failures**
   - Verify WebSocket service is running
   - Check browser console for CORS errors

4. **No traces in Jaeger**
   - Ensure Jaeger is running
   - Verify JAEGER_HOST environment variable

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f <service-name>

# Last 100 lines
docker-compose logs --tail=100 <service-name>
```

### Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (clean database)
docker-compose down -v

# Complete cleanup
./demo/cleanup.sh
```

## 📚 Key Features Demonstrated

1. **Microservices Architecture**
   - Service isolation and independence
   - Inter-service communication
   - Service discovery through API Gateway

2. **Real-time Capabilities**
   - WebSocket for live updates
   - Redis pub/sub for event distribution
   - Immediate leaderboard updates

3. **Scalability**
   - Horizontal scaling ready
   - Caching strategies
   - Database connection pooling

4. **Observability**
   - Distributed tracing with Jaeger
   - Metrics collection with Prometheus
   - Centralized logging

5. **Resilience**
   - Health checks for all services
   - Automatic restart on failure
   - Graceful degradation

6. **Security**
   - JWT-based authentication
   - Service-to-service authentication
   - Input validation and sanitization

## 📄 License

This is a demonstration system for educational purposes.