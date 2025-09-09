# Distributed Message Queue System - Data Flow Diagrams

## System Architecture Overview

```mermaid
graph TB
    %% External Layer
    UI[Web UI Interface<br/>Port: 8080]
    Client[External Clients<br/>API Consumers]
    
    %% Gateway Layer
    Gateway[API Gateway<br/>Port: 19005<br/>Authentication & Rate Limiting]
    
    %% Core Services Layer
    Producer[Producer Service<br/>Port: 19007<br/>Message Publishing]
    Consumer1[Consumer Service 1<br/>Port: 19008<br/>Message Consumption]
    Consumer2[Consumer Service 2<br/>Port: 19009<br/>Message Consumption]
    
    %% Broker Cluster
    Broker1[Broker 1 - Leader<br/>Port: 19001<br/>Message Storage]
    Broker2[Broker 2 - Follower<br/>Port: 19002<br/>Message Replication]
    Broker3[Broker 3 - Follower<br/>Port: 19006<br/>Message Replication]
    
    %% Coordination & Monitoring
    Coordinator[Coordinator Service<br/>Port: 19004<br/>Leader Election & Metadata]
    Monitor[Monitoring Service<br/>Port: 19010<br/>Metrics Collection]
    
    %% Storage Layer
    WAL1[(Write-Ahead Log<br/>Broker 1)]
    WAL2[(Write-Ahead Log<br/>Broker 2)]
    WAL3[(Write-Ahead Log<br/>Broker 3)]
    
    %% Data Flow Connections
    UI --> Gateway
    Client --> Gateway
    
    Gateway --> Producer
    Gateway --> Consumer1
    Gateway --> Consumer2
    Gateway --> Broker1
    Gateway --> Coordinator
    
    Producer --> Broker1
    Producer --> Broker2
    Producer --> Broker3
    
    Consumer1 --> Broker1
    Consumer1 --> Broker2
    Consumer1 --> Broker3
    
    Consumer2 --> Broker1
    Consumer2 --> Broker2
    Consumer2 --> Broker3
    
    Broker1 --> WAL1
    Broker2 --> WAL2
    Broker3 --> WAL3
    
    Broker1 -.-> Broker2
    Broker1 -.-> Broker3
    Broker2 -.-> Broker1
    Broker3 -.-> Broker1
    
    Monitor --> Broker1
    Monitor --> Broker2
    Monitor --> Broker3
    Monitor --> Producer
    Monitor --> Consumer1
    Monitor --> Consumer2
    
    Coordinator --> Broker1
    Coordinator --> Broker2
    Coordinator --> Broker3
    
    %% Styling
    classDef ui fill:#e1f5fe
    classDef gateway fill:#f3e5f5
    classDef service fill:#e8f5e8
    classDef broker fill:#fff3e0
    classDef storage fill:#fce4ec
    classDef coord fill:#f1f8e9
    
    class UI,Client ui
    class Gateway gateway
    class Producer,Consumer1,Consumer2 service
    class Broker1,Broker2,Broker3 broker
    class WAL1,WAL2,WAL3 storage
    class Coordinator,Monitor coord
```

## Message Production Flow

```mermaid
flowchart LR
    %% Input Sources
    WebUI[Web UI<br/>User Input]
    APIClient[API Client<br/>External System]
    
    %% Processing Pipeline
    Gateway[API Gateway<br/>Auth + Rate Limit]
    Producer[Producer Service<br/>Message Processing]
    
    %% Partitioning Logic
    Partitioner{Partition Logic<br/>Hash(key) % partitions}
    
    %% Broker Cluster
    P0[Partition 0<br/>Broker 1]
    P1[Partition 1<br/>Broker 2]
    P2[Partition 2<br/>Broker 3]
    
    %% Replication
    R0A[Replica 0A<br/>Broker 2]
    R0B[Replica 0B<br/>Broker 3]
    R1A[Replica 1A<br/>Broker 1]
    R1B[Replica 1B<br/>Broker 3]
    R2A[Replica 2A<br/>Broker 1]
    R2B[Replica 2B<br/>Broker 2]
    
    %% Storage
    WAL[(Write-Ahead<br/>Log Files)]
    
    %% Flow Connections
    WebUI --> Gateway
    APIClient --> Gateway
    Gateway --> Producer
    Producer --> Partitioner
    
    Partitioner -->|key hash % 3 = 0| P0
    Partitioner -->|key hash % 3 = 1| P1
    Partitioner -->|key hash % 3 = 2| P2
    
    P0 --> R0A
    P0 --> R0B
    P1 --> R1A
    P1 --> R1B
    P2 --> R2A
    P2 --> R2B
    
    P0 --> WAL
    P1 --> WAL
    P2 --> WAL
    R0A --> WAL
    R0B --> WAL
    R1A --> WAL
    R1B --> WAL
    R2A --> WAL
    R2B --> WAL
    
    %% Styling
    classDef input fill:#e3f2fd
    classDef process fill:#e8f5e8
    classDef partition fill:#fff3e0
    classDef replica fill:#f3e5f5
    classDef storage fill:#fce4ec
    
    class WebUI,APIClient input
    class Gateway,Producer,Partitioner process
    class P0,P1,P2 partition
    class R0A,R0B,R1A,R1B,R2A,R2B replica
    class WAL storage
```

## Message Consumption Flow

```mermaid
flowchart RL
    %% Storage Layer
    WAL[(Write-Ahead<br/>Log Files)]
    
    %% Broker Partitions
    P0[Partition 0<br/>Messages 0,3,6,9...]
    P1[Partition 1<br/>Messages 1,4,7,10...]
    P2[Partition 2<br/>Messages 2,5,8,11...]
    
    %% Consumer Groups
    CG1[Consumer Group 1<br/>demo-group]
    CG2[Consumer Group 2<br/>analytics-group]
    
    %% Consumer Instances
    C1[Consumer 1<br/>Processes P0,P1]
    C2[Consumer 2<br/>Processes P2]
    C3[Consumer 3<br/>Processes P0,P1,P2]
    
    %% Offset Management
    OffsetStore[(Consumer Offsets<br/>Per Group/Partition)]
    
    %% Processing Pipeline
    Gateway[API Gateway<br/>Load Balancing]
    
    %% Output
    WebUI[Web UI<br/>Real-time Updates]
    APIClient[API Client<br/>Message Processing]
    
    %% Flow Connections
    WAL --> P0
    WAL --> P1
    WAL --> P2
    
    P0 --> CG1
    P1 --> CG1
    P2 --> CG1
    
    P0 --> CG2
    P1 --> CG2
    P2 --> CG2
    
    CG1 --> C1
    CG1 --> C2
    CG2 --> C3
    
    C1 --> OffsetStore
    C2 --> OffsetStore
    C3 --> OffsetStore
    
    C1 --> Gateway
    C2 --> Gateway
    C3 --> Gateway
    
    Gateway --> WebUI
    Gateway --> APIClient
    
    %% Offset Tracking
    OffsetStore -.-> P0
    OffsetStore -.-> P1
    OffsetStore -.-> P2
    
    %% Styling
    classDef storage fill:#fce4ec
    classDef partition fill:#fff3e0
    classDef consumer fill:#e8f5e8
    classDef group fill:#f3e5f5
    classDef output fill:#e3f2fd
    classDef offset fill:#f1f8e9
    
    class WAL,OffsetStore storage
    class P0,P1,P2 partition
    class C1,C2,C3 consumer
    class CG1,CG2 group
    class WebUI,APIClient output
    class Gateway offset
```

## Replication and Fault Tolerance Flow

```mermaid
flowchart TB
    %% Leader Election
    Coordinator[Coordinator Service<br/>Leader Election & Metadata]
    
    %% Broker Cluster States
    Leader[Broker 1 - LEADER<br/>Handles Writes]
    Follower1[Broker 2 - FOLLOWER<br/>Replicates Data]
    Follower2[Broker 3 - FOLLOWER<br/>Replicates Data]
    
    %% Failure Scenarios
    FailureDetection{Health Check<br/>Failure Detection}
    
    %% Recovery Process
    LeaderElection{New Leader<br/>Election Process}
    DataSync[Data Synchronization<br/>Catch-up Process]
    
    %% Client Redirection
    ClientRedirect[Client Request<br/>Redirection]
    
    %% Monitoring
    Monitor[Monitoring Service<br/>Health Metrics]
    
    %% Normal Operation Flow
    Coordinator --> Leader
    Coordinator --> Follower1
    Coordinator --> Follower2
    
    Leader --> Follower1
    Leader --> Follower2
    
    Monitor --> Leader
    Monitor --> Follower1
    Monitor --> Follower2
    Monitor --> FailureDetection
    
    %% Failure Handling Flow
    FailureDetection -->|Broker Failure Detected| LeaderElection
    LeaderElection -->|New Leader Selected| Follower1
    LeaderElection -->|New Leader Selected| Follower2
    
    %% Recovery Flow
    Follower1 -->|Becomes New Leader| DataSync
    DataSync --> ClientRedirect
    
    %% Failed Broker Recovery
    FailureDetection -.->|Broker Restart| DataSync
    DataSync -.->|Rejoin Cluster| Follower1
    DataSync -.->|Rejoin Cluster| Follower2
    
    %% Styling
    classDef coordinator fill:#f1f8e9
    classDef leader fill:#c8e6c9
    classDef follower fill:#fff3e0
    classDef failure fill:#ffcdd2
    classDef recovery fill:#e1f5fe
    classDef monitor fill:#f3e5f5
    
    class Coordinator coordinator
    class Leader leader
    class Follower1,Follower2 follower
    class FailureDetection,LeaderElection failure
    class DataSync,ClientRedirect recovery
    class Monitor monitor
```

## Topic and Partition Management Flow

```mermaid
flowchart TD
    %% Topic Creation Request
    TopicRequest[Topic Creation Request<br/>name, partitions, replication]
    
    %% Validation
    Validation{Topic Validation<br/>Name, Config Check}
    
    %% Metadata Storage
    MetadataStore[(Topic Metadata<br/>Configuration Store)]
    
    %% Partition Assignment
    PartitionAssignment[Partition Assignment<br/>Distribute Across Brokers]
    
    %% Broker Cluster
    B1[Broker 1<br/>Partitions: 0,3,6...]
    B2[Broker 2<br/>Partitions: 1,4,7...]
    B3[Broker 3<br/>Partitions: 2,5,8...]
    
    %% Replication Setup
    ReplicationSetup[Replication Setup<br/>Leader/Follower Assignment]
    
    %% Storage Initialization
    StorageInit[Storage Initialization<br/>WAL Files Creation]
    
    %% Client Notification
    ClientNotify[Client Notification<br/>Topic Ready for Use]
    
    %% Data Flow
    TopicRequest --> Validation
    
    Validation -->|Valid| MetadataStore
    Validation -->|Invalid| ClientNotify
    
    MetadataStore --> PartitionAssignment
    
    PartitionAssignment --> B1
    PartitionAssignment --> B2
    PartitionAssignment --> B3
    
    B1 --> ReplicationSetup
    B2 --> ReplicationSetup
    B3 --> ReplicationSetup
    
    ReplicationSetup --> StorageInit
    StorageInit --> ClientNotify
    
    %% Cross-broker replication setup
    B1 -.->|Replicate to| B2
    B1 -.->|Replicate to| B3
    B2 -.->|Replicate to| B1
    B2 -.->|Replicate to| B3
    B3 -.->|Replicate to| B1
    B3 -.->|Replicate to| B2
    
    %% Styling
    classDef request fill:#e3f2fd
    classDef validation fill:#fff3e0
    classDef metadata fill:#f1f8e9
    classDef broker fill:#e8f5e8
    classDef replication fill:#f3e5f5
    classDef storage fill:#fce4ec
    classDef notify fill:#e1f5fe
    
    class TopicRequest request
    class Validation validation
    class MetadataStore metadata
    class B1,B2,B3 broker
    class PartitionAssignment,ReplicationSetup replication
    class StorageInit storage
    class ClientNotify notify
```

## Monitoring and Health Check Flow

```mermaid
flowchart LR
    %% Monitoring Service
    MonitorService[Monitoring Service<br/>Health Collector]
    
    %% Service Health Checks
    ProducerHealth[Producer Health<br/>Status: Healthy/Unhealthy]
    Consumer1Health[Consumer 1 Health<br/>Status: Healthy/Unhealthy]
    Consumer2Health[Consumer 2 Health<br/>Status: Healthy/Unhealthy]
    Broker1Health[Broker 1 Health<br/>Status: Healthy/Unhealthy]
    Broker2Health[Broker 2 Health<br/>Status: Healthy/Unhealthy]
    Broker3Health[Broker 3 Health<br/>Status: Healthy/Unhealthy]
    GatewayHealth[Gateway Health<br/>Status: Healthy/Unhealthy]
    CoordHealth[Coordinator Health<br/>Status: Healthy/Unhealthy]
    
    %% Metrics Collection
    MetricsAgg[Metrics Aggregation<br/>Performance Data]
    
    %% Health Dashboard
    HealthDash{Health Dashboard<br/>System Status Overview}
    
    %% Alert System
    AlertSystem[Alert System<br/>Failure Notifications]
    
    %% Recovery Actions
    AutoRecovery[Auto Recovery<br/>Service Restart]
    
    %% UI Updates
    WebSocketUpdate[WebSocket Updates<br/>Real-time UI Refresh]
    
    %% Data Collection Flow
    MonitorService --> ProducerHealth
    MonitorService --> Consumer1Health
    MonitorService --> Consumer2Health
    MonitorService --> Broker1Health
    MonitorService --> Broker2Health
    MonitorService --> Broker3Health
    MonitorService --> GatewayHealth
    MonitorService --> CoordHealth
    
    %% Aggregation
    ProducerHealth --> MetricsAgg
    Consumer1Health --> MetricsAgg
    Consumer2Health --> MetricsAgg
    Broker1Health --> MetricsAgg
    Broker2Health --> MetricsAgg
    Broker3Health --> MetricsAgg
    GatewayHealth --> MetricsAgg
    CoordHealth --> MetricsAgg
    
    %% Dashboard and Alerts
    MetricsAgg --> HealthDash
    HealthDash --> AlertSystem
    HealthDash --> WebSocketUpdate
    
    %% Recovery Actions
    AlertSystem --> AutoRecovery
    AutoRecovery -.-> Broker2Health
    AutoRecovery -.-> ProducerHealth
    AutoRecovery -.-> Consumer1Health
    
    %% Styling
    classDef monitor fill:#f1f8e9
    classDef health fill:#e8f5e8
    classDef metrics fill:#fff3e0
    classDef dashboard fill:#e3f2fd
    classDef alert fill:#ffcdd2
    classDef recovery fill:#c8e6c9
    classDef websocket fill:#f3e5f5
    
    class MonitorService monitor
    class ProducerHealth,Consumer1Health,Consumer2Health,Broker1Health,Broker2Health,Broker3Health,GatewayHealth,CoordHealth health
    class MetricsAgg metrics
    class HealthDash dashboard
    class AlertSystem alert
    class AutoRecovery recovery
    class WebSocketUpdate websocket
```

## Key Data Flow Characteristics

### 1. **High Availability**
- 3-broker cluster with replication factor of 3
- Leader-follower replication pattern
- Automatic failover and recovery

### 2. **Load Distribution**
- Round-robin partition assignment
- Consumer group load balancing
- Gateway-based request distribution

### 3. **Data Persistence**
- Write-Ahead Logging (WAL) for durability
- Partition-based message storage
- Offset tracking for consumption resumption

### 4. **Fault Tolerance**
- Health monitoring with automatic recovery
- Leader election for broker failures
- Client request redirection during failures

### 5. **Scalability**
- Horizontal scaling through partition addition
- Multiple consumer instances per group
- Load balancing across broker instances