# Distributed Systems Design Portfolio

A comprehensive collection of distributed system designs and implementations showcasing various architectural patterns, scalability solutions, and modern infrastructure technologies.

## 📚 Project Overview

This repository contains multiple distributed system implementations demonstrating real-world architecture patterns used by major tech companies. Each system is designed with scalability, reliability, and performance in mind.

## 🏗️ Systems Included

### Core Distributed Systems

1. **IntelliKV-DB**: A distributed key-value database with consistent hashing, replication, and fault tolerance
2. **DistributedMessageQueue**: Message queue system with pub/sub patterns and guaranteed delivery
3. **GoogleMaps**: Location-based services with geospatial indexing and routing algorithms
4. **GoogleDriveSystem**: Distributed file storage with chunking, deduplication, and sync capabilities
5. **S3-LikeObjectStorage**: Object storage service with multi-part uploads and versioning
6. **MetricsMonitoringAndCollection**: Time-series metrics collection and aggregation system
7. **Notification**: Real-time notification delivery system with multiple channels

### Application Systems

1. **HotelBooking**: Microservices-based booking system with inventory management
2. **PaymentSystem**: Secure payment processing with fraud detection
3. **StockExchange**: High-frequency trading system with order matching engine
4. **DistributedEmailService**: Email delivery service with queue management
5. **AdClickEvents**: Click stream processing and analytics
6. **Digital-Wallet**: Digital wallet with transaction management
7. **NearByFriends**: Location-based social features
8. **NewsFeedService**: Personalized news feed generation
9. **ProximityService**: Geospatial proximity search service
10. **RateLimiter**: Distributed rate limiting service
11. **RealTimeGamingBoard**: Real-time leaderboard system
12. **SearchAutoComplete**: Search suggestion service with trie data structures
13. **WebCrawler**: Distributed web crawling system

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js and npm (v14+)
- Python 3.8+
- PostgreSQL client (optional)
- Redis (for caching layers)
- Kubernetes (for k8s deployments)

### Running Systems

#### Start All Services
```bash
./start-services.sh
```

#### Start Individual Systems
Each system can be run independently. Navigate to the specific directory and follow the README instructions.

#### Using Docker Compose
Most systems include docker-compose configurations:
```bash
cd [system-directory]
docker-compose up -d
```

#### Kubernetes Deployments
For systems with k8s support:
```bash
cd IntelliKV-DB/local-k8s
./build-and-deploy.sh
```

## 🎯 Key Features

### Distributed System Patterns
- **Consistent Hashing**: Used in IntelliKV-DB for data distribution
- **Replication & Fault Tolerance**: Multi-node replication with automatic failover
- **Load Balancing**: Multiple load balancing algorithms implemented
- **Service Discovery**: Dynamic service registration and discovery
- **Circuit Breakers**: Failure handling and graceful degradation
- **Rate Limiting**: Token bucket and sliding window implementations
- **Caching Strategies**: Multi-level caching with Redis and in-memory stores

### Data Management
- **Sharding**: Horizontal partitioning for scalability
- **Event Sourcing**: Event-driven architectures in multiple systems
- **CQRS**: Command Query Responsibility Segregation patterns
- **Distributed Transactions**: 2PC and Saga patterns
- **Data Consistency**: Eventual and strong consistency models

### Infrastructure & DevOps
- **Containerization**: Docker containers for all services
- **Orchestration**: Kubernetes deployments with StatefulSets
- **Service Mesh**: Inter-service communication patterns
- **Monitoring**: Metrics collection and observability
- **CI/CD**: Automated testing and deployment scripts
- **Infrastructure as Code**: Declarative infrastructure definitions

## 🌐 Technologies Used

### Languages
- **Python**: Primary language for distributed systems (IntelliKV-DB, ML services)
- **Go**: High-performance services (GoogleMaps, ProximityService)
- **Java**: Enterprise systems (StockExchange, PaymentSystem)
- **Node.js/TypeScript**: Microservices and real-time systems
- **React**: Frontend applications

### Databases
- **PostgreSQL**: Relational data storage
- **Redis**: Caching and session management
- **MongoDB**: Document storage for flexible schemas
- **Cassandra**: Wide-column store for time-series data
- **ElasticSearch**: Full-text search capabilities

### Infrastructure
- **Docker**: Containerization of all services
- **Kubernetes**: Container orchestration
- **Apache Kafka**: Event streaming platform
- **RabbitMQ**: Message queuing
- **Nginx**: Load balancing and reverse proxy
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization

## 📖 System Highlights

### IntelliKV-DB
- Distributed key-value store with consistent hashing
- Multi-node replication with configurable replication factor
- Automatic failover and recovery
- Support for offline nodes and dynamic node addition
- Kubernetes StatefulSet deployment

### GoogleMaps
- Geospatial indexing using QuadTree/R-Tree
- Route calculation with Dijkstra/A* algorithms
- Real-time traffic updates
- POI search and recommendations
- Map tile serving and caching

### S3-Like Object Storage
- Multi-part upload support
- Object versioning and lifecycle management
- Erasure coding for data durability
- CDN integration for content delivery
- S3-compatible API

### DistributedMessageQueue
- Pub/Sub and Point-to-Point messaging
- Message persistence and replay
- Dead letter queues
- Exactly-once delivery semantics
- Horizontal scaling with partitioning

### StockExchange
- Order matching engine with sub-millisecond latency
- Support for multiple order types (Market, Limit, Stop)
- Real-time price feeds
- Risk management and circuit breakers
- Historical data storage and replay

## 📊 Documentation

### System Design Documents
- `DATA_FLOW_DIAGRAMS.md`: Data flow architecture diagrams
- `DEMO_FLOW_DIAGRAMS.md`: Demo workflow visualizations
- `DEMO_GUIDE.md`: Step-by-step demo instructions

### Individual System READMEs
Each system directory contains its own README with:
- Architecture overview
- Setup instructions
- API documentation
- Testing procedures
- Performance benchmarks

## 🔧 Development

### Running Tests
```bash
# Unit tests
cd [system-directory]
npm test  # or pytest, go test, mvn test

# Integration tests
docker-compose -f docker-compose.test.yml up
```

### Building from Source
```bash
# Python projects
pip install -r requirements.txt

# Node.js projects
npm install

# Go projects
go mod download

# Java projects
mvn clean install
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Submit a pull request

## 📝 License

This project is for educational and demonstration purposes.

---

**Status**: ✅ Active Development
**Last Updated**: September 2025  
**Version**: 2.0.0