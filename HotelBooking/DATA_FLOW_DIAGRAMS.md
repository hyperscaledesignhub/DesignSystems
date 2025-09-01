# Hotel Booking System - Complete Data Flow Diagrams

## System Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Frontend<br/>Port 3000]
    end
    
    subgraph "Microservices Layer"
        HS[Hotel Service<br/>Port 8001]
        RS[Room Service<br/>Port 8002]
        GS[Guest Service<br/>Port 8003]
        IS[Inventory Service<br/>Port 8004]
        RES[Reservation Service<br/>Port 8005]
        PS[Payment Service<br/>Port 8006]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Multiple DBs)]
        RD[(Redis Cache)]
    end
    
    UI --> HS
    UI --> RS
    UI --> GS
    UI --> IS
    UI --> RES
    UI --> PS
    
    HS --> PG
    HS --> RD
    RS --> PG
    GS --> PG
    IS --> PG
    RES --> PG
    RES --> IS
    RES --> HS
    RES --> RS
    PS --> PG
    PS --> RES
```

---

## 1. User Registration & Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as React Frontend
    participant GS as Guest Service
    participant DB as guest_db

    Note over U,DB: New User Registration
    U->>UI: Fill registration form<br/>(name, email, phone)
    UI->>UI: Validate form data
    UI->>GS: POST /guests/register
    activate GS
    GS->>DB: INSERT guest record
    DB-->>GS: Return guest_id
    GS-->>UI: Return guest object<br/>{id, name, email, phone}
    deactivate GS
    UI->>UI: Store user in localStorage
    UI-->>U: Show success message<br/>Navigate to dashboard

    Note over U,DB: Returning User Login
    U->>UI: Enter email
    UI->>GS: GET /guests/{email}
    activate GS
    GS->>DB: SELECT by email
    DB-->>GS: Return guest record
    GS-->>UI: Return guest object
    deactivate GS
    UI->>UI: Store user in localStorage
    UI-->>U: Navigate to dashboard
```

**Key Data Points:**
- Guest ID generation using UUID
- Email as unique identifier
- No password authentication (demo system)
- Local storage for session management

---

## 2. Hotel Search & Browsing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as React Frontend
    participant HS as Hotel Service
    participant RS as Room Service
    participant RD as Redis Cache
    participant DB as hotel_db/room_db

    Note over U,DB: Browse Hotels
    U->>UI: Access hotels page
    UI->>HS: GET /api/v1/hotels
    activate HS
    HS->>RD: Check cache for hotels
    alt Cache Hit
        RD-->>HS: Return cached hotels
    else Cache Miss
        HS->>DB: SELECT hotels
        DB-->>HS: Return hotel records
        HS->>RD: Cache hotels (TTL: 300s)
    end
    HS-->>UI: Return hotels array
    deactivate HS
    UI-->>U: Display hotels grid

    Note over U,DB: View Hotel Details & Rooms
    U->>UI: Click on hotel
    UI->>HS: GET /api/v1/hotels/{hotel_id}
    activate HS
    HS->>DB: SELECT hotel details
    DB-->>HS: Return hotel record
    HS-->>UI: Return hotel object
    deactivate HS
    
    UI->>RS: GET /api/v1/hotels/{hotel_id}/room-types
    activate RS
    RS->>DB: SELECT room types by hotel_id
    DB-->>RS: Return room types
    RS-->>UI: Return room types array
    deactivate RS
    UI-->>U: Display hotel details + room types
```

**Key Data Points:**
- Redis caching for improved performance
- Hotel details include: name, address, location
- Room types include: name, max_occupancy, base_price

---

## 3. Room Booking & Reservation Flow

### 3A. Check Availability
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Inventory
    participant Database

    User->>Frontend: Select dates & rooms
    Frontend->>Inventory: GET /availability
    Inventory->>Database: Check room availability
    Database-->>Inventory: Available rooms count
    Inventory-->>Frontend: Availability status
    Frontend-->>User: Show available rooms
```

### 3B. Create Reservation (Atomic Transaction)
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Reservation
    participant Inventory
    participant Database

    User->>Frontend: Click "Book Now"
    Frontend->>Reservation: POST /reservations
    
    Note over Reservation,Database: Atomic Transaction
    Reservation->>Database: 1. Insert reservation
    Reservation->>Inventory: 2. Reserve rooms
    Inventory->>Database: 3. Update inventory
    
    alt Success
        Database-->>Frontend: Booking confirmed
        Frontend-->>User: Show confirmation
    else Failure
        Database-->>Frontend: Booking failed
        Frontend-->>User: Show error
    end
```

**Key Features:**
- ✅ Concurrency control prevents overbooking
- ✅ Atomic transactions ensure data consistency
- ✅ Real-time availability checking
- ✅ Database constraints for safety

---

## 4. Payment Processing Flow

### 4A. Load Payment Page
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Payment

    User->>Frontend: Click "Pay Now"
    Frontend->>Payment: GET /payments (history)
    Payment-->>Frontend: Payment history
    Frontend-->>User: Show payment form
```

### 4B. Process Payment
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Payment
    participant Reservation

    User->>Frontend: Submit payment form
    Frontend->>Payment: POST /payments/process
    
    Note over Payment: Mock Processing (Always Success)
    Payment->>Payment: Create payment record
    Payment->>Reservation: Update status to 'paid'
    Reservation-->>Payment: Status updated
    
    Payment-->>Frontend: Payment successful
    Frontend-->>User: Show success message
```

**Key Features:**
- 💳 Mock payment processing (demo purposes)
- 🌍 Multi-currency support (USD, EUR, GBP, JPY, CAD)
- 📱 Multiple payment methods (Card, PayPal, etc.)
- 🔄 Automatic reservation status update
- 📊 Payment history tracking

---

## 5. Reservation Management Flow

### 5A. Load Reservations with Data Enrichment
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Reservation
    participant Hotel
    participant Room

    User->>Frontend: Visit "My Reservations"
    Frontend->>Reservation: GET /reservations
    Reservation->>Hotel: GET hotel names
    Reservation->>Room: GET room type names
    Hotel-->>Reservation: Hotel details
    Room-->>Reservation: Room details
    Reservation-->>Frontend: Enriched reservations
    Frontend-->>User: Show reservations with names
```

### 5B. Cancel Reservation
```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Reservation
    participant Inventory

    User->>Frontend: Click "Cancel"
    Frontend->>Frontend: Show confirmation
    User->>Frontend: Confirm cancellation
    
    Frontend->>Reservation: POST /cancel
    Reservation->>Inventory: Release rooms
    Inventory-->>Reservation: Rooms released
    Reservation-->>Frontend: Cancellation confirmed
    Frontend-->>User: Show "Cancelled" status
```

**Key Features:**
- 🔍 Real-time data enrichment (hotel/room names)
- 🔗 Cross-service communication
- 📊 Status tracking (confirmed, paid, cancelled)
- 🔄 Automatic inventory release on cancellation

---

## 6. Inventory Management Flow (Admin)

### 6A. Add New Hotel & Rooms
```mermaid
sequenceDiagram
    participant Admin
    participant Frontend
    participant Hotel
    participant Room
    participant Inventory

    Admin->>Frontend: Create hotel form
    Frontend->>Hotel: POST /hotels
    Hotel-->>Frontend: Hotel created
    
    Admin->>Frontend: Add room types
    Frontend->>Room: POST /room-types
    Room->>Inventory: Auto-create 365 days inventory
    Inventory-->>Room: Inventory created
    Room-->>Frontend: Room type created
    Frontend-->>Admin: Success notification
```

### 6B. Monitor Availability
```mermaid
sequenceDiagram
    participant Admin
    participant Frontend
    participant Inventory

    Admin->>Frontend: Access availability reports
    Frontend->>Inventory: GET /availability
    Inventory-->>Frontend: Availability data
    Frontend-->>Admin: Show availability charts
```

**Key Features:**
- 🏨 Automatic hotel & room setup
- 📅 Auto-create 365 days inventory (10 rooms/day)
- 📊 Real-time availability monitoring
- 🛡️ Constraint-based overbooking prevention
- 💰 Dynamic pricing capability

---

## 7. System Architecture & Data Flow Summary

### Service Communication Patterns:
```mermaid
graph LR
    subgraph "Synchronous HTTP Communication"
        A[Frontend] --> B[All Services]
        C[Reservation] --> D[Hotel Service]
        C --> E[Room Service]
        C --> F[Inventory Service]
        G[Payment] --> C
        H[Room Service] --> F
    end
    
    subgraph "Database Per Service"
        I[hotel_db]
        J[room_db]
        K[guest_db]
        L[inventory_db]
        M[reservation_db]
        N[payment_db]
    end
    
    subgraph "Caching Layer"
        O[Redis Cache]
    end
```

### Key Technical Features Demonstrated:

1. **Microservices Architecture**
   - 6 independent services
   - Database per service pattern
   - Service-to-service communication

2. **Concurrency Control**
   - Database constraints prevent overbooking
   - Atomic transactions for reservations
   - Row-level locking in PostgreSQL

3. **Caching Strategy**
   - Redis for hotel data (5-minute TTL)
   - Reduces database load
   - Improved response times

4. **Data Consistency**
   - Cross-service data enrichment
   - Eventually consistent across services
   - Graceful error handling

5. **Scalability Patterns**
   - Stateless services
   - Horizontal scaling ready
   - Load balancer friendly

### Demo Flow Recommendations:

1. **Start with Registration** → Show user onboarding
2. **Hotel Browsing** → Demonstrate caching and search
3. **Booking Process** → Highlight concurrency control
4. **Payment Flow** → Show cross-service communication
5. **Reservation Management** → Display data enrichment
6. **Admin Functions** → Demonstrate inventory management

Each flow demonstrates specific microservices patterns and can be used to explain different architectural concepts in your demo presentations.

---

## 🎯 Quick Demo Reference Guide

### **Simple Flows (Start Here):**
1. **User Registration** → Simple CRUD operation
2. **Hotel Browsing** → Caching demonstration
3. **Payment Processing** → Cross-service communication

### **Complex Flows (Advanced Topics):**
4. **Room Booking** → Concurrency control & atomic transactions
5. **Reservation Management** → Data enrichment patterns
6. **Inventory Management** → Admin workflows & automation

### **Key Demo Points:**
- **Architecture**: Show system overview first
- **Scalability**: Highlight stateless services & caching
- **Reliability**: Demonstrate atomic transactions & constraints
- **Performance**: Show Redis caching in hotel browsing
- **Data Consistency**: Explain cross-service data enrichment

### **Technical Highlights:**
```
✅ Microservices (6 services)    ✅ PostgreSQL per service
✅ Redis caching                 ✅ Docker containerization  
✅ Atomic transactions          ✅ Cross-service communication
✅ Concurrency control          ✅ Real-time data enrichment
```