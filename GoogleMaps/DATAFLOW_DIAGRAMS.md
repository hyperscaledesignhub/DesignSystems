# Google Maps Clone - Data Flow Diagrams

Simple and clear data flow diagrams showing how the UI interacts with backend services.

## System Architecture

```mermaid
graph LR
    UI[Web UI] --> LS[Location Service]
    UI --> NS[Navigation Service] 
    UI --> PS[Places Service]
    UI --> TS[Traffic Service]
    
    PS --> DB[(Redis DB)]
    LS --> DB
    
    style UI fill:#e1f5fe
    style DB fill:#ffecb3
```

## 1. Traffic Flow

### User Views Traffic on Map
```mermaid
flowchart LR
    A[User Opens Map] --> B[Request Traffic Data]
    B --> C[Location Service]
    C --> D[Return Traffic Areas]
    D --> E[Show Colored Circles]
    
    style A fill:#e3f2fd
    style E fill:#c8e6c9
```

### Background Traffic Updates
```mermaid
flowchart LR
    A[Timer Every 5s] --> B[Fetch New Traffic]
    B --> C[Update Circle Colors]
    C --> A
    
    style A fill:#fff3e0
    style C fill:#ffcdd2
```

## 2. Places Discovery Flow

### User Discovers Places
```mermaid
flowchart LR
    A[Click Discover] --> B[Choose Category]
    B --> C[Places Service]
    C --> D[Show Business List]
    D --> E[Click Business]
    E --> F[Show Details]
    
    style A fill:#e8f5e8
    style F fill:#f3e5f5
```

### Available Categories
```mermaid
graph LR
    A[Categories] --> B[🍽️ Restaurants]
    A --> C[⛽ Gas Stations]
    A --> D[🏨 Hotels]
    A --> E[🛍️ Shopping]
    A --> F[🏥 Hospitals]
    
    style A fill:#fff3e0
```

## 3. Search Flow

### User Searches Places
```mermaid
flowchart LR
    A[Type Search] --> B[Send Query]
    B --> C[Places Service]
    C --> D[Match Keywords]
    D --> E[Show Results]
    E --> F[Click Marker]
    F --> G[Show Details]
    
    style A fill:#e1f5fe
    style G fill:#ffcdd2
```

## 4. Navigation Flow

### Route Planning
```mermaid
flowchart LR
    A[Set Start & End] --> B[Navigation Service]
    B --> C[Calculate Route]
    C --> D[Draw Line on Map]
    D --> E[Show Directions]
    
    style A fill:#e8f5e8
    style E fill:#f3e5f5
```

### Turn-by-Turn Navigation
```mermaid
flowchart LR
    A[Start Navigation] --> B[Get GPS Position]
    B --> C[Update Progress]
    C --> D[Show Next Turn]
    D --> B
    
    style A fill:#e3f2fd
    style D fill:#c8e6c9
```

## 5. Map Interactions

### Basic Map Controls
```mermaid
flowchart LR
    A[User Action] --> B{Click Type}
    B -->|Click| C[Show Address]
    B -->|Drag| D[Move Map]  
    B -->|Zoom| E[Change Detail Level]
    
    style A fill:#e1f5fe
    style C fill:#c8e6c9
    style D fill:#fff3e0
    style E fill:#f3e5f5
```

## 6. Error Handling

### When Services Fail
```mermaid
flowchart LR
    A[API Call] --> B{Service OK?}
    B -->|No| C[Show Error]
    B -->|Yes| D[Show Data]
    C --> E[Use Demo Data]
    
    style C fill:#ffcdd2
    style D fill:#c8e6c9
    style E fill:#fff3e0
```

## 7. Real-Time Updates

### Background Timers
```mermaid
graph LR
    A[UI Started] --> B[Traffic Timer: 5s]
    A --> C[Location Timer: 15s]
    A --> D[Places Timer: 30s]
    
    style A fill:#e3f2fd
    style B fill:#ffcdd2
    style C fill:#fff3e0
    style D fill:#c8e6c9
```

---

## API Endpoints Summary

### Location Service (Port 8086)
- `GET /api/traffic/data` - Get real-time traffic information
- `POST /api/traffic/start-simulation` - Start traffic simulation
- `GET /api/locations/stats` - Get location service statistics
- `GET /health` - Service health check

### Navigation Service (Port 8081)  
- `POST /api/navigation/route` - Calculate route between points
- `POST /api/navigation/reroute` - Recalculate route from current position
- `GET /health` - Service health check

### Places Service (Port 8083)
- `GET /api/v1/places/listings` - Get business listings by category/location
- `POST /api/v1/places/search` - Search places by query
- `GET /api/v1/places/{id}/details` - Get detailed place information
- `GET /api/v1/places/{id}/reviews` - Get place reviews and ratings
- `GET /health` - Service health check

### Traffic Service (Port 8084)
- `GET /api/traffic/realtime` - Get real-time traffic updates
- `GET /health` - Service health check

### Web UI (Port 3002)
- `/` - Main application interface
- `/maps` - Interactive map view
- WebSocket connections for real-time updates

---

*This dataflow diagram provides a comprehensive view of all data flows supported by the Google Maps Clone UI, showing the complete journey from user interactions to backend services and data storage.*