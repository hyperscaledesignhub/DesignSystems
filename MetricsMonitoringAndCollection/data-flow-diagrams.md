# Metrics Monitoring System - Data Flow Diagrams

This document illustrates the various data flows within the metrics monitoring system using Mermaid diagrams.

## 1. Core Metrics Collection Flow

```mermaid
flowchart TD
    A[Service Applications] -->|Expose /metrics endpoint| B[Metrics Collector]
    B -->|Service Discovery| C[etcd]
    B -->|Collect Metrics| D[Raw Metrics Data]
    D -->|Publish| E[Kafka Topic: metrics]
    E -->|Consume| F[Data Consumer]
    F -->|Store| G[InfluxDB]
    G -->|Query| H[Query Service]
    H -->|Cache| I[Redis]
    H -->|API Response| J[Dashboard/UI]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style E fill:#fff3e0
    style G fill:#e8f5e8
    style J fill:#fce4ec
```

## 2. Alert Processing Flow

```mermaid
flowchart TD
    A[Alert Rules YAML] -->|Load Rules| B[Alert Manager]
    B -->|Query Metrics| C[Query Service]
    C -->|Fetch Data| D[InfluxDB]
    D -->|Return Metrics| C
    C -->|Metrics Data| B
    B -->|Evaluate Conditions| E{Threshold Breached?}
    E -->|Yes| F[Create Alert]
    E -->|No| G[Continue Monitoring]
    F -->|Send Notification| H[Email/Webhook]
    F -->|Update State| I[Alert State Store]
    
    style A fill:#fff9c4
    style B fill:#ffebee
    style F fill:#ffcdd2
    style H fill:#c8e6c9
```

## 3. Query Service Data Flow

```mermaid
flowchart TD
    A[Dashboard Request] -->|API Call| B[Query Service]
    B -->|Check Cache| C{Cache Hit?}
    C -->|Yes| D[Return Cached Data]
    C -->|No| E[Build Flux Query]
    E -->|Execute Query| F[InfluxDB]
    F -->|Raw Data| G[Process Results]
    G -->|Format Response| H[JSON Response]
    H -->|Cache Result| I[Redis Cache]
    H -->|Return to Client| J[Dashboard/UI]
    
    style B fill:#e3f2fd
    style C fill:#fff3e0
    style F fill:#e8f5e8
    style I fill:#fce4ec
```

## 4. Real-time Dashboard Update Flow

```mermaid
flowchart TD
    A[Live Metrics Generation] -->|WebSocket| B[Demo UI Server]
    B -->|Broadcast| C[Connected Clients]
    C -->|Update Charts| D[Chart.js Visualization]
    
    E[Periodic Status Check] -->|HTTP Request| F[Service Health Endpoints]
    F -->|Health Status| B
    B -->|Status Update| C
    
    G[User Actions] -->|WebSocket Events| B
    B -->|Control Commands| H[Data Generators]
    H -->|Generated Data| B
    
    style B fill:#f3e5f5
    style C fill:#e1f5fe
    style D fill:#fce4ec
```

## 5. Service Discovery Flow

```mermaid
flowchart TD
    A[New Service Instance] -->|Register| B[etcd Key-Value Store]
    B -->|Service Info| C[/services/{service}/{instance}]
    C -->|Watch Changes| D[Metrics Collector]
    D -->|Update Target List| E[Collection Targets]
    E -->|Start Collection| F[Periodic Metrics Pull]
    F -->|HTTP GET /metrics| A
    
    G[Service Shutdown] -->|Deregister| B
    B -->|Delete Key| C
    C -->|Notify Change| D
    D -->|Remove Target| E
    
    style B fill:#e8f5e8
    style D fill:#f3e5f5
    style E fill:#fff3e0
```

## 6. Data Storage and Retention Flow

```mermaid
flowchart TD
    A[Raw Metrics Data] -->|30s intervals| B[InfluxDB Raw Bucket]
    B -->|Retention: 7 days| C{Data Age Check}
    C -->|> 7 days| D[Delete Raw Data]
    C -->|< 7 days| E[Keep Raw Data]
    
    B -->|Continuous Aggregation| F[Hourly Aggregation Task]
    F -->|GROUP BY 1h| G[InfluxDB Hourly Bucket]
    G -->|Retention: 30 days| H{Data Age Check}
    H -->|> 30 days| I[Delete Hourly Data]
    H -->|< 30 days| J[Keep Hourly Data]
    
    G -->|Daily Aggregation| K[Daily Aggregation Task]
    K -->|GROUP BY 1d| L[InfluxDB Daily Bucket]
    L -->|Retention: 1 year| M[Long-term Storage]
    
    style B fill:#e8f5e8
    style G fill:#e8f5e8
    style L fill:#e8f5e8
```

## 7. Error Handling and Resilience Flow

```mermaid
flowchart TD
    A[Service Request] -->|Try| B{Service Available?}
    B -->|Yes| C[Process Request]
    B -->|No| D[Circuit Breaker]
    D -->|Open| E[Return Cached Data]
    D -->|Half-Open| F[Test Request]
    F -->|Success| G[Close Circuit]
    F -->|Failure| H[Keep Circuit Open]
    
    C -->|Success| I[Update Health Status]
    C -->|Error| J[Log Error]
    J -->|Retry Logic| K{Retry Count < Max?}
    K -->|Yes| L[Wait & Retry]
    K -->|No| M[Fail Request]
    
    style D fill:#ffcdd2
    style E fill:#fff3e0
    style J fill:#ffebee
```

## 8. Load Balancing and Scaling Flow

```mermaid
flowchart TD
    A[Incoming Requests] -->|Load Balancer| B{Route Request}
    B -->|Round Robin| C[Query Service Instance 1]
    B -->|Round Robin| D[Query Service Instance 2]
    B -->|Round Robin| E[Query Service Instance N]
    
    C -->|High Load| F{CPU > 80%?}
    D -->|High Load| G{CPU > 80%?}
    E -->|High Load| H{CPU > 80%?}
    
    F -->|Yes| I[Scale Out Signal]
    G -->|Yes| I
    H -->|Yes| I
    I -->|Trigger| J[Container Orchestrator]
    J -->|Deploy| K[New Service Instance]
    K -->|Register| L[Service Discovery]
    
    style B fill:#e3f2fd
    style I fill:#fff3e0
    style J fill:#f3e5f5
```

## 9. Kafka Message Processing Flow

```mermaid
flowchart TD
    A[Metrics Collector] -->|Produce| B[Kafka Topic: metrics]
    B -->|Partition 0| C[Data Consumer Group 1]
    B -->|Partition 1| D[Data Consumer Group 1]
    B -->|Partition 2| E[Data Consumer Group 1]
    
    C -->|Batch Process| F[Batch Writer]
    D -->|Batch Process| G[Batch Writer]
    E -->|Batch Process| H[Batch Writer]
    
    F -->|Bulk Insert| I[InfluxDB]
    G -->|Bulk Insert| I
    H -->|Bulk Insert| I
    
    I -->|Commit Offset| J[Kafka Offset Management]
    J -->|Update Position| B
    
    style B fill:#fff3e0
    style C fill:#e8f5e8
    style D fill:#e8f5e8
    style E fill:#e8f5e8
```

## 10. Configuration Management Flow

```mermaid
flowchart TD
    A[Environment Variables] -->|Load| B[Config Service]
    A -->|Load| C[Service Instances]
    
    D[YAML Config Files] -->|Parse| B
    E[etcd Config Store] -->|Watch| B
    
    B -->|Distribute Config| F[Metrics Collector Config]
    B -->|Distribute Config| G[Query Service Config]
    B -->|Distribute Config| H[Alert Manager Config]
    B -->|Distribute Config| I[Data Consumer Config]
    
    J[Config Change] -->|Update| E
    E -->|Notify| B
    B -->|Hot Reload| C
    
    style B fill:#e1f5fe
    style E fill:#e8f5e8
    style J fill:#fff3e0
```

## Architecture Overview

The system follows a microservices architecture with the following key components:

- **Metrics Collector**: Pull-based metrics collection with service discovery
- **Kafka**: Message queue for decoupling data ingestion from storage
- **Data Consumer**: Batch processing and data transformation
- **InfluxDB**: Time-series database optimized for metrics storage
- **Query Service**: High-performance API with Redis caching
- **Alert Manager**: Rule-based alerting with multiple notification channels
- **Dashboard**: Real-time visualization with WebSocket updates

## Data Flow Characteristics

- **Throughput**: Supports 10M+ metrics per day
- **Query Performance**: < 100ms average response time with caching
- **Reliability**: Circuit breakers and retry logic for fault tolerance
- **Scalability**: Horizontal scaling with Kafka partitioning
- **Real-time**: WebSocket connections for live dashboard updates