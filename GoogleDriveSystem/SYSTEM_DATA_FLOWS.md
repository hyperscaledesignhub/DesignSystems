# Google Drive MVP System - Data Flow Documentation

This document provides a comprehensive overview of all features and their data flows in the Google Drive-like MVP system.

## System Architecture Overview

The system consists of 6 microservices:
- **Auth Service** (Port 9011): User authentication and authorization
- **File Service** (Port 9012): File storage and retrieval
- **Metadata Service** (Port 9003): File metadata and folder management
- **Block Service** (Port 9004): Block-based file storage for large files
- **Notification Service** (Port 9005): Real-time notifications and messaging
- **API Gateway** (Port 9010): Request routing, load balancing, and authentication middleware
- **UI Service** (Port 3000): React frontend application

## Infrastructure Services
- **PostgreSQL** (Port 5432): Primary database
- **Redis** (Port 6379): Caching and rate limiting
- **MinIO** (Port 9000): Object storage

---

## Core Features and Data Flows

### 1. User Authentication & Authorization

#### User Registration Flow

```mermaid
flowchart TD
    A[User Submits Registration] --> B[UI Service]
    B --> C[API Gateway]
    C --> D{Auth Middleware}
    D -->|Public Endpoint| E[Auth Service]
    E --> F[Hash Password]
    F --> G[Store in PostgreSQL]
    G --> H[Return User Data]
    H --> I[JWT Token Generation]
    I --> J[Response to UI]
    J --> K[Store Token in LocalStorage]
    K --> L[Redirect to Dashboard]
```

**Data Flow:**
1. User fills registration form (email, username, password)
2. UI Service sends POST request to `/auth/register` via API Gateway
3. API Gateway routes to Auth Service (bypasses auth middleware for public endpoint)
4. Auth Service validates email uniqueness, hashes password with bcrypt
5. User data stored in PostgreSQL with auto-generated UUID
6. JWT token created with user_id and expiration
7. Response includes user data and token
8. UI stores token in localStorage and redirects to dashboard

#### User Login Flow

```mermaid
flowchart TD
    A[User Submits Login] --> B[UI Service]
    B --> C[API Gateway]
    C --> D[Auth Service]
    D --> E[Validate Credentials]
    E --> F{Password Match?}
    F -->|Yes| G[Generate JWT Token]
    F -->|No| H[Return 401 Error]
    G --> I[Return Token & User Data]
    I --> J[UI Stores Token]
    J --> K[Set Auth Context]
    K --> L[Redirect to Dashboard]
    H --> M[Display Error Message]
```

#### Token Verification Flow

```mermaid
flowchart TD
    A[Request with JWT Token] --> B[API Gateway]
    B --> C[Auth Middleware]
    C --> D[Extract Bearer Token]
    D --> E[Auth Service /verify]
    E --> F[Decode JWT]
    F --> G{Token Valid?}
    G -->|Yes| H[Return user_id]
    G -->|No| I[Return 401]
    H --> J[Add user_id to Request State]
    J --> K[Continue to Target Service]
    I --> L[Return Unauthorized Response]
```

### 2. File Management System

#### File Upload Flow

```mermaid
flowchart TD
    A[User Selects File] --> B[UI File Upload Component]
    B --> C[Create FormData with File]
    C --> D[API Gateway /files/upload]
    D --> E[Auth Middleware Verification]
    E --> F[File Service]
    F --> G[Validate File Size < 10GB]
    G --> H[Read File Content]
    H --> I[Generate SHA256 Checksum]
    I --> J[Detect MIME Type]
    J --> K[Generate UUID for file_id]
    K --> L[MinIO Storage Upload]
    L --> M[Store File Metadata in PostgreSQL]
    M --> N[Create Metadata Entry via HTTP]
    N --> O[Metadata Service]
    O --> P[Store File Metadata]
    P --> Q[Return File Response]
    Q --> R[Update UI File List]
```

**Key Data Points:**
- File metadata: `file_id`, `filename`, `size`, `content_type`, `checksum`, `upload_date`
- Storage path: `{user_id}/{file_id}`
- Maximum file size: 10GB

#### File Download Flow

```mermaid
flowchart TD
    A[User Clicks Download] --> B[UI Service]
    B --> C[API Gateway /files/download/{file_id}]
    C --> D[Auth Middleware]
    D --> E[File Service]
    E --> F[Query File from PostgreSQL]
    F --> G{File Exists & User Owns?}
    G -->|Yes| H[Get Storage Path]
    G -->|No| I[Return 404/403]
    H --> J[Download from MinIO]
    J --> K[Stream Response]
    K --> L[Browser Download]
```

#### File Listing Flow

```mermaid
flowchart TD
    A[UI Requests File List] --> B[API Gateway /files]
    B --> C[Auth Middleware]
    C --> D[File Service]
    D --> E[Query User Files from PostgreSQL]
    E --> F[Format File List Response]
    F --> G[Return to UI]
    G --> H[Display in FileManager Component]
```

### 3. Metadata Management System

#### Metadata Creation Flow

```mermaid
flowchart TD
    A[File Upload Triggers] --> B[File Service]
    B --> C[HTTP POST to Metadata Service]
    C --> D[/metadata/metadata endpoint]
    D --> E[Auth Token Verification]
    E --> F[Store in PostgreSQL]
    F --> G[Include: file_id, filename, size, type]
    G --> H[Add timestamps and user_id]
    H --> I[Return Metadata ID]
```

#### File Search Flow

```mermaid
flowchart TD
    A[User Enters Search Query] --> B[UI Search Component]
    B --> C[API Gateway /metadata/search]
    C --> D[Auth Middleware]
    D --> E[Metadata Service]
    E --> F[PostgreSQL LIKE Query on filename]
    F --> G[Filter by user_id]
    G --> H[Return Matching Files]
    H --> I[Display Search Results]
```

#### Folder Management Flow

```mermaid
flowchart TD
    A[Create Folder Request] --> B[UI Service]
    B --> C[API Gateway /metadata/folders]
    C --> D[Metadata Service]
    D --> E[Create Folder Entry]
    E --> F[Set parent_path and folder_name]
    F --> G[Store in PostgreSQL]
    G --> H[Return Folder Details]
    
    I[List Folders] --> J[API Gateway /metadata/folders]
    J --> K[Query by parent_path]
    K --> L[Return Folder Tree]
```

### 4. Block-Based Storage System

#### Block Upload Flow (Large Files)

```mermaid
flowchart TD
    A[Large File Upload] --> B[UI Service]
    B --> C[Split File into Blocks]
    C --> D[For Each Block]
    D --> E[API Gateway /blocks/upload]
    E --> F[Block Service]
    F --> G[Generate Block ID]
    G --> H[Encrypt Block Content]
    H --> I[Store in MinIO]
    I --> J[Record Block Metadata]
    J --> K[PostgreSQL Storage]
    K --> L[Link to Original File]
    L --> M[Return Block References]
```

#### Block Retrieval Flow

```mermaid
flowchart TD
    A[File Download Request] --> B[Block Service]
    B --> C[Query File Blocks from PostgreSQL]
    C --> D[Retrieve Block Order]
    D --> E[For Each Block]
    E --> F[Download from MinIO]
    F --> G[Decrypt Block]
    G --> H[Reassemble File]
    H --> I[Stream to User]
```

### 5. Real-time Notification System

#### Send Notification Flow

```mermaid
flowchart TD
    A[System Event Triggers] --> B[Service Calls Notification API]
    B --> C[API Gateway /notifications/notify]
    C --> D[Notification Service]
    D --> E[Create Notification Record]
    E --> F[Store in PostgreSQL]
    F --> G[Check User Online Status]
    G --> H{User Online?}
    H -->|Yes| I[Send WebSocket Message]
    H -->|No| J[Store for Later Retrieval]
    I --> K[Real-time UI Update]
    J --> L[User Gets on Next Login]
```

#### WebSocket Connection Flow

```mermaid
flowchart TD
    A[User Login] --> B[UI Establishes WebSocket]
    B --> C[Notification Service]
    C --> D[Store Connection in Redis]
    D --> E[Set User Status: Online]
    E --> F[Ready for Real-time Messages]
    
    G[User Logout/Disconnect] --> H[Remove from Redis]
    H --> I[Set Status: Offline]
```

#### Broadcast Message Flow

```mermaid
flowchart TD
    A[Admin Sends Broadcast] --> B[API Gateway /notifications/broadcast]
    B --> C[Notification Service]
    C --> D[Get All Online Users from Redis]
    D --> E[For Each Online User]
    E --> F[Send WebSocket Message]
    F --> G[Store Message in PostgreSQL]
    G --> H[Real-time UI Notification]
```

### 6. API Gateway Features

#### Request Routing Flow

```mermaid
flowchart TD
    A[Client Request] --> B[API Gateway]
    B --> C[CORS Middleware]
    C --> D[Request Logging]
    D --> E[Authentication Middleware]
    E --> F{Public Endpoint?}
    F -->|Yes| G[Skip Auth]
    F -->|No| H[Verify JWT Token]
    H --> I{Token Valid?}
    I -->|Yes| J[Rate Limiting Check]
    I -->|No| K[Return 401]
    J --> L{Rate Limit OK?}
    L -->|Yes| M[Load Balancer]
    L -->|No| N[Return 429]
    M --> O[Route to Target Service]
    O --> P[Proxy Response]
    G --> J
```

#### Load Balancing Flow

```mermaid
flowchart TD
    A[Incoming Request] --> B[Load Balancer]
    B --> C{Service Type}
    C -->|File Operations| D[Hash-based LB]
    C -->|Other Services| E[Round Robin LB]
    D --> F[Hash user_id]
    F --> G[Select File Service Instance]
    E --> H[Next Service in Rotation]
    G --> I[Forward Request]
    H --> I
    I --> J[Service Response]
    J --> K[Return to Client]
```

### 7. Dashboard and Analytics

#### Dashboard Data Flow

```mermaid
flowchart TD
    A[Dashboard Load] --> B[UI Dashboard Component]
    B --> C[Multiple API Calls in Parallel]
    C --> D[Gateway Health Check]
    C --> E[File Statistics]
    C --> F[Block Statistics]
    C --> G[Notification History]
    D --> H[System Health Data]
    E --> I[File Count & Storage Used]
    F --> J[Block Storage Stats]
    G --> K[Recent Notifications]
    H --> L[Render Dashboard]
    I --> L
    J --> L
    K --> L
```

#### Activity Logging Flow

```mermaid
flowchart TD
    A[User Action] --> B[Service Processing]
    B --> C[Log Action to Database]
    C --> D[Trigger Notification]
    D --> E[Real-time Activity Update]
    E --> F[UI Activity Feed Update]
```

### 8. File Sharing System

#### Share File Flow

```mermaid
flowchart TD
    A[User Shares File] --> B[UI Share Dialog]
    B --> C[API Gateway /files/{file_id}/share]
    C --> D[File Service]
    D --> E[Create Share Record]
    E --> F[Generate Share Token/Link]
    F --> G[Store in PostgreSQL]
    G --> H[Send Notification to Recipients]
    H --> I[Return Share Details]
    I --> J[Display Share Link/Status]
```

#### Access Shared File Flow

```mermaid
flowchart TD
    A[User Clicks Share Link] --> B[API Gateway /files/shared]
    B --> C[File Service]
    C --> D[Validate Share Token]
    D --> E{Share Valid & Active?}
    E -->|Yes| F[Check Permissions]
    E -->|No| G[Return 403 Forbidden]
    F --> H[Allow File Access]
    H --> I[Download/View File]
    G --> J[Display Error Message]
```

---

## Data Storage Schema

### PostgreSQL Tables

#### Users Table (Auth Service)
- `user_id` (UUID, Primary Key)
- `email` (VARCHAR, Unique)
- `username` (VARCHAR)
- `password_hash` (VARCHAR)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

#### Files Table (File Service)
- `file_id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `filename` (VARCHAR)
- `size` (BIGINT)
- `content_type` (VARCHAR)
- `checksum` (VARCHAR)
- `storage_path` (VARCHAR)
- `upload_date` (TIMESTAMP)
- `is_deleted` (BOOLEAN)

#### File Metadata Table (Metadata Service)
- `metadata_id` (UUID, Primary Key)
- `file_id` (UUID, Foreign Key)
- `user_id` (UUID, Foreign Key)
- `filename` (VARCHAR)
- `size` (BIGINT)
- `content_type` (VARCHAR)
- `tags` (TEXT)
- `folder_path` (VARCHAR)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

#### File Blocks Table (Block Service)
- `block_id` (UUID, Primary Key)
- `file_id` (UUID, Foreign Key)
- `user_id` (UUID, Foreign Key)
- `block_number` (INTEGER)
- `size` (INTEGER)
- `checksum` (VARCHAR)
- `storage_path` (VARCHAR)
- `encrypted` (BOOLEAN)
- `created_at` (TIMESTAMP)

#### Shared Files Table (File Service)
- `share_id` (UUID, Primary Key)
- `file_id` (UUID, Foreign Key)
- `owner_id` (UUID, Foreign Key)
- `shared_with` (UUID, Foreign Key)
- `permissions` (VARCHAR)
- `expires_at` (TIMESTAMP)
- `created_at` (TIMESTAMP)

#### Notifications Table (Notification Service)
- `notification_id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `type` (VARCHAR)
- `title` (VARCHAR)
- `message` (TEXT)
- `is_read` (BOOLEAN)
- `created_at` (TIMESTAMP)

### Redis Data Structures

#### User Sessions
- Key: `session:{user_id}`
- Type: String
- Value: JWT token data
- TTL: 24 hours

#### Rate Limiting
- Key: `rate_limit:{user_id}`
- Type: String
- Value: Request count
- TTL: 60 seconds

#### Online Users (WebSocket)
- Key: `online_users`
- Type: Set
- Value: Set of user_ids currently connected

#### User Status
- Key: `user_status:{user_id}`
- Type: Hash
- Fields: `status`, `last_seen`, `socket_id`

### MinIO Object Storage

#### File Storage Structure
```
bucket: gdrive-files
├── {user_id}/
│   ├── {file_id}
│   └── {file_id}
```

#### Block Storage Structure
```
bucket: gdrive-blocks
├── {user_id}/
│   ├── {file_id}/
│   │   ├── block_0
│   │   ├── block_1
│   │   └── block_n
```

---

## Security Features

### Authentication & Authorization Flow

```mermaid
flowchart TD
    A[Request] --> B[API Gateway]
    B --> C[Extract JWT Token]
    C --> D[Auth Service Verification]
    D --> E{Token Valid?}
    E -->|Yes| F[Extract user_id]
    E -->|No| G[Return 401]
    F --> H[Rate Limiting Check]
    H --> I{Within Limits?}
    I -->|Yes| J[Forward to Service]
    I -->|No| K[Return 429]
    J --> L[Service Authorization]
    L --> M{User Owns Resource?}
    M -->|Yes| N[Process Request]
    M -->|No| O[Return 403]
```

### Data Encryption Flow

```mermaid
flowchart TD
    A[File Upload] --> B[Generate AES Key]
    B --> C[Encrypt File Content]
    C --> D[Store Encrypted in MinIO]
    D --> E[Encrypt AES Key with Master Key]
    E --> F[Store Key in PostgreSQL]
    
    G[File Download] --> H[Retrieve Encrypted Key]
    H --> I[Decrypt with Master Key]
    I --> J[Retrieve Encrypted File]
    J --> K[Decrypt File Content]
    K --> L[Stream to User]
```

---

## Error Handling and Monitoring

### Error Flow

```mermaid
flowchart TD
    A[Error Occurs] --> B[Service Error Handler]
    B --> C[Log Error Details]
    C --> D[Determine Error Type]
    D --> E{Client Error 4xx?}
    E -->|Yes| F[Return User-Friendly Message]
    E -->|No| G{Server Error 5xx?}
    G -->|Yes| H[Log for Investigation]
    H --> I[Return Generic Error Message]
    F --> J[Client Handles Error]
    I --> J
```

### Health Check Flow

```mermaid
flowchart TD
    A[Health Check Request] --> B[Service Health Endpoint]
    B --> C[Check Database Connection]
    C --> D[Check External Dependencies]
    D --> E[Check Service Status]
    E --> F{All Healthy?}
    F -->|Yes| G[Return 200 OK]
    F -->|No| H[Return 503 Service Unavailable]
    G --> I[Load Balancer: Keep in Rotation]
    H --> J[Load Balancer: Remove from Rotation]
```

---

## Performance Optimizations

### Caching Strategy

```mermaid
flowchart TD
    A[Request] --> B[Check Redis Cache]
    B --> C{Cache Hit?}
    C -->|Yes| D[Return Cached Data]
    C -->|No| E[Query Database]
    E --> F[Store Result in Redis]
    F --> G[Return Fresh Data]
    D --> H[Fast Response < 10ms]
    G --> I[Normal Response ~100ms]
```

### File Chunking for Large Files

```mermaid
flowchart TD
    A[Large File > 100MB] --> B[Split into 10MB Chunks]
    B --> C[Upload Chunks in Parallel]
    C --> D[Block Service Processing]
    D --> E[Store Block Metadata]
    E --> F[Provide Download Resumability]
    F --> G[Reassemble on Download]
```

This comprehensive documentation covers all the major features and data flows in the Google Drive MVP system. Each flow shows how data moves through the system, what services are involved, and what data transformations occur at each step.