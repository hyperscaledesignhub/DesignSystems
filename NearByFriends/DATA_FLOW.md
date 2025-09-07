# Nearby Friends System - Data Flow Documentation

This document illustrates all data flows in the Nearby Friends system using Mermaid diagrams.

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Demo UI<br/>JavaScript/HTML]
    end
    
    subgraph "Gateway Layer"
        AG[API Gateway<br/>:8900]
        WS[WebSocket Gateway<br/>:8904]
    end
    
    subgraph "Microservices"
        US[User Service<br/>:8901]
        FS[Friend Service<br/>:8902]
        LS[Location Service<br/>:8903]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL<br/>:5732)]
        RD[(Redis<br/>:6679)]
    end
    
    UI -->|HTTP/WebSocket| AG
    UI -->|WebSocket| WS
    AG --> US
    AG --> FS
    AG --> LS
    WS --> US
    WS --> FS
    WS --> LS
    US --> PG
    FS --> PG
    LS --> PG
    LS --> RD
    WS --> RD
```

## 2. User Authentication Flow

```mermaid
flowchart TD
    A[Client Requests Login] --> B[API Gateway<br/>POST /api/auth/login]
    B --> C[User Service<br/>Validate Credentials]
    C --> D[Query User Database]
    D --> E{User Exists?}
    E -->|Yes| F[Generate JWT Token]
    E -->|No| G[Return 401 Unauthorized]
    F --> H[Store Session in Redis]
    H --> I[Return JWT Token]
    I --> J[Client Stores Token]
    J --> K[Token Used for Future Requests]
    G --> L[Login Failed]
    
    style F fill:#e1f5fe
    style I fill:#c8e6c9
    style G fill:#ffcdd2
```

## 3. User Registration Flow

```mermaid
flowchart TD
    A[Client Submits Registration] --> B[API Gateway<br/>POST /api/auth/register]
    B --> C[User Service<br/>Validate Input]
    C --> D{Username/Email<br/>Available?}
    D -->|No| E[Return 409 Conflict]
    D -->|Yes| F[Hash Password]
    F --> G[Insert User Record]
    G --> H[PostgreSQL Database]
    H --> I[Return User ID]
    I --> J[Generate JWT Token]
    J --> K[Return Success + Token]
    E --> L[Registration Failed]
    
    style J fill:#e1f5fe
    style K fill:#c8e6c9
    style E fill:#ffcdd2
```

## 4. Friend Relationship Management

```mermaid
flowchart TD
    A[Send Friend Request] --> B[API Gateway<br/>POST /api/friends/request]
    B --> C[Friend Service<br/>Validate Users]
    C --> D[Check Existing Relationship]
    D --> E{Already Friends?}
    E -->|Yes| F[Return 409 Conflict]
    E -->|No| G[Create Friend Record]
    G --> H[PostgreSQL<br/>friends table]
    H --> I[Bidirectional Relationship]
    I --> J[Notify Both Users]
    J --> K[WebSocket Notification]
    F --> L[Already Friends]
    
    M[Accept Friend Request] --> N[Update Status to 'accepted']
    N --> O[Both Users Now Friends]
    
    style G fill:#e1f5fe
    style I fill:#c8e6c9
    style K fill:#fff3e0
```

## 5. Location Update Flow

```mermaid
flowchart TD
    A[Client Updates Location] --> B[API Gateway<br/>POST /api/location/update]
    B --> C[Location Service<br/>Validate Token]
    C --> D[Extract User ID from JWT]
    D --> E[Update Location in PostgreSQL]
    E --> F[Cache Location in Redis]
    F --> G[Calculate Nearby Friends]
    G --> H[Query Friend Relationships]
    H --> I[Find Friends Within Range]
    I --> J[WebSocket Notifications]
    J --> K[Notify Friends of Update]
    K --> L[Real-time UI Updates]
    
    style E fill:#e1f5fe
    style F fill:#fff3e0
    style J fill:#c8e6c9
```

## 6. Nearby Friends Query Flow

```mermaid
flowchart TD
    A[Client Requests Nearby Friends] --> B[API Gateway<br/>GET /api/location/nearby/:userId]
    B --> C[Location Service<br/>Validate Authorization]
    C --> D[Get User's Current Location]
    D --> E[Query Friend Relationships]
    E --> F[Friend Service<br/>Get Friend List]
    F --> G[Get Friends' Locations]
    G --> H[Calculate Distances]
    H --> I[Filter by Distance Threshold]
    I --> J[Sort by Distance]
    J --> K[Return Nearby Friends List]
    
    L[Redis Cache] --> D
    L --> G
    
    style H fill:#e1f5fe
    style I fill:#fff3e0
    style K fill:#c8e6c9
```

## 7. Real-time WebSocket Communication

```mermaid
flowchart TD
    A[Client Connects to WebSocket] --> B[WebSocket Gateway<br/>ws://localhost:8904/ws]
    B --> C[Authenticate Connection]
    C --> D[Store Connection in Redis]
    D --> E[Subscribe to User Channel]
    
    F[Location Update Triggers] --> G[Publish to Redis Channel]
    G --> H[WebSocket Gateway Receives]
    H --> I[Find Connected Friends]
    I --> J[Send to Connected Clients]
    J --> K[Client Receives Update]
    K --> L[Update UI in Real-time]
    
    style D fill:#e1f5fe
    style G fill:#fff3e0
    style J fill:#c8e6c9
```

## 8. Distance Calculation Algorithm

```mermaid
flowchart TD
    A[User Location Update] --> B[Get User's Friend List]
    B --> C[For Each Friend]
    C --> D[Get Friend's Location]
    D --> E[Calculate Haversine Distance]
    E --> F{Distance < 5 miles?}
    F -->|Yes| G[Add to Nearby List]
    F -->|No| H[Skip Friend]
    G --> I[Include Distance & Last Updated]
    H --> J[Next Friend]
    I --> J
    J --> K{More Friends?}
    K -->|Yes| C
    K -->|No| L[Return Nearby Friends]
    
    style E fill:#e1f5fe
    style G fill:#c8e6c9
```

## 9. Cache Management Flow

```mermaid
flowchart TD
    A[Location Update] --> B[Update PostgreSQL]
    B --> C[Update Redis Cache]
    C --> D[Set TTL: 1 hour]
    
    E[Nearby Query] --> F{Location in Cache?}
    F -->|Yes| G[Use Cached Data]
    F -->|No| H[Query PostgreSQL]
    H --> I[Cache Result]
    I --> G
    G --> J[Return Data]
    
    K[Cache Expiry] --> L[Remove from Redis]
    L --> M[Next Query Hits Database]
    
    style C fill:#fff3e0
    style G fill:#e1f5fe
    style I fill:#c8e6c9
```

## 10. Demo Data Flow

```mermaid
flowchart TD
    A[Demo Initialization] --> B[Create 10 Demo Users]
    B --> C[Generate JWT Tokens]
    C --> D[Set Initial Locations]
    D --> E[Create Friend Relationships]
    E --> F[Save to demo_config.json]
    
    G[UI Loads Config] --> H[Populate User Dropdown]
    H --> I[User Selects Account]
    I --> J[Login with Pre-generated Token]
    J --> K[Load Nearby Friends]
    K --> L[Display on Map]
    
    M[Demo Scenarios] --> N{Scenario Type}
    N -->|Moving| O[Update User Location]
    N -->|Rush Hour| P[Move All Users]
    N -->|Meetup| Q[Converge to Point]
    
    O --> R[Real-time Updates]
    P --> R
    Q --> R
    
    style F fill:#e1f5fe
    style L fill:#c8e6c9
    style R fill:#fff3e0
```

## 11. Error Handling Flow

```mermaid
flowchart TD
    A[API Request] --> B{Token Valid?}
    B -->|No| C[Return 401 Unauthorized]
    B -->|Yes| D{User Exists?}
    D -->|No| E[Return 404 Not Found]
    D -->|Yes| F{Service Available?}
    F -->|No| G[Return 503 Service Unavailable]
    F -->|Yes| H[Process Request]
    H --> I{Request Valid?}
    I -->|No| J[Return 400 Bad Request]
    I -->|Yes| K[Execute Business Logic]
    K --> L{Success?}
    L -->|Yes| M[Return 200 OK]
    L -->|No| N[Return 500 Internal Error]
    
    style C fill:#ffcdd2
    style E fill:#ffcdd2
    style G fill:#fff3e0
    style M fill:#c8e6c9
```

## 12. Database Schema Data Flow

```mermaid
erDiagram
    USERS {
        int id PK
        string username
        string email
        string password_hash
        timestamp created_at
        timestamp updated_at
    }
    
    FRIENDS {
        int id PK
        int user_id FK
        int friend_id FK
        string status
        timestamp created_at
    }
    
    LOCATIONS {
        int id PK
        int user_id FK
        decimal latitude
        decimal longitude
        timestamp last_updated
    }
    
    USERS ||--o{ FRIENDS : "user_id"
    USERS ||--o{ FRIENDS : "friend_id"
    USERS ||--|| LOCATIONS : "user_id"
```

## 13. Service Communication Patterns

```mermaid
flowchart LR
    subgraph "Synchronous (HTTP)"
        A[API Gateway] -->|REST| B[User Service]
        A -->|REST| C[Friend Service]
        A -->|REST| D[Location Service]
    end
    
    subgraph "Asynchronous (WebSocket + Redis)"
        E[Location Service] -->|Publish| F[Redis PubSub]
        F -->|Subscribe| G[WebSocket Gateway]
        G -->|Broadcast| H[Connected Clients]
    end
    
    subgraph "Inter-service (HTTP)"
        D -->|Friend List| C
        C -->|User Info| B
    end
    
    style F fill:#fff3e0
    style G fill:#e1f5fe
    style H fill:#c8e6c9
```

---

## Key Data Flow Characteristics

### 1. **High Availability**
- Multiple service instances can run behind load balancers
- Redis provides session persistence and caching
- PostgreSQL handles transactional data with ACID properties

### 2. **Real-time Performance**
- WebSocket connections for instant notifications
- Redis caching reduces database queries
- Efficient distance calculations with spatial indexing

### 3. **Scalability**
- Microservices can be scaled independently
- Stateless services enable horizontal scaling
- Redis handles high-frequency location updates

### 4. **Data Consistency**
- PostgreSQL ensures transactional integrity
- Redis provides eventual consistency for real-time data
- JWT tokens maintain stateless authentication

This documentation provides a complete view of how data flows through the Nearby Friends system from user interactions to database storage and real-time notifications.