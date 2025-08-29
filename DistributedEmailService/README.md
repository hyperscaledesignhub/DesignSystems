# Distributed Email Service - Complete Demo

A comprehensive demonstration of microservices architecture for distributed email service with full observability, tracing, and real-world features.

## 🏗️ Architecture Overview

This demo showcases a production-ready distributed email system built with:

### Core Services
- **API Gateway** - Request routing, load balancing, and cross-cutting concerns
- **Authentication Service** - JWT-based user authentication and authorization
- **Email Service** - Email composition, storage, and management
- **Spam Detection Service** - ML-based spam filtering and scoring
- **Notification Service** - Real-time notifications via WebSocket
- **Attachment Service** - File upload/download with cloud storage
- **Search Service** - Full-text search with advanced filtering

### Infrastructure Components
- **PostgreSQL** - Primary database for user and email data
- **Redis** - Caching and session management
- **Elasticsearch** - Full-text search and analytics
- **MinIO** - S3-compatible object storage for attachments
- **Jaeger** - Distributed tracing and observability

### Frontend
- **React UI** - Modern responsive web application
- **Material-UI** - Professional component library
- **Real-time Updates** - WebSocket integration for notifications

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ available RAM
- Ports 3000, 8000-8006, 5432, 6379, 9000-9001, 9200, 16686 available

### Start the Demo
```bash
# Navigate to demo directory
cd demo

# Start all services with one command
./scripts/start-demo.sh
```

The startup script will:
1. Clean up any existing containers
2. Build all services from source
3. Start infrastructure services (DB, Cache, Storage)
4. Start application services with health checks
5. Create demo user and sample data
6. Display all access points

### Access the Demo
- **Main Application**: http://localhost:3000
- **Demo Login**: `demo@example.com` / `password`

## 🔍 Observability & Monitoring

### Jaeger Distributed Tracing
- **URL**: http://localhost:16686
- **Features**: End-to-end request tracing across all microservices
- **Usage**: Make requests through the UI to generate traces

### Service Health Monitoring
- **API Gateway Health**: http://localhost:8000/health
- **Individual Service Docs**: 
  - Auth: http://localhost:8001/docs
  - Email: http://localhost:8002/docs
  - Spam: http://localhost:8003/docs
  - Notification: http://localhost:8004/docs
  - Attachment: http://localhost:8005/docs
  - Search: http://localhost:8006/docs

### Infrastructure Monitoring
- **MinIO Console**: http://localhost:9001 (`minioaccess`/`miniosecret`)
- **Elasticsearch**: http://localhost:9200
- **Direct DB Access**: `postgresql://emailuser:emailpass@localhost:5432/emaildb`

## 🎯 Demo Use Cases

### 1. Email Composition & Sending
**Scenario**: Create and send emails with attachments and spam detection

**Steps**:
1. Login to the web UI
2. Click "Compose" to create a new email
3. Add recipients, subject, and body
4. Upload attachments (files are stored in MinIO)
5. Send the email (triggers spam detection)
6. View the email in "Sent" folder

**Observability**: 
- View traces in Jaeger showing email → spam → attachment → notification flow
- Check spam scores and attachment metadata

### 2. Advanced Search & Filtering
**Scenario**: Search emails with full-text search and faceted filtering

**Steps**:
1. Navigate to "Search" in the sidebar
2. Enter search terms (subject, body, sender)
3. Apply filters (folder, date range, read status)
4. View aggregated facets (folder counts, label distributions)
5. Click results to view full emails

**Observability**:
- Elasticsearch query performance in traces
- Search result scoring and relevance

### 3. Real-time Notifications
**Scenario**: Receive instant notifications for email events

**Steps**:
1. Open the application in multiple browser tabs
2. Send an email from one tab
3. Observe real-time notifications in other tabs
4. Check notification history in the UI
5. Mark notifications as read

**Observability**:
- WebSocket connection traces
- Notification delivery metrics

### 4. Spam Detection & Filtering
**Scenario**: Demonstrate ML-based spam detection

**Steps**:
1. Compose an email with spam keywords:
   - Subject: "URGENT!!! Free Money!!!"
   - Body: "Click here now! 100% guaranteed! No risk! Win $1000000!"
2. Send the email
3. Check the spam score in email details
4. View emails in "Spam" folder if score > 0.7

**Observability**:
- Spam detection service traces
- Score calculation and threshold application

### 5. File Attachment Management
**Scenario**: Upload, download, and manage email attachments

**Steps**:
1. Compose email and upload multiple files
2. Send email with attachments
3. View attachment list in received emails
4. Download attachments (served from MinIO)
5. Check storage usage in user profile

**Observability**:
- File upload/download traces
- MinIO storage operations
- Storage quota management

### 6. Multi-folder Email Management
**Scenario**: Organize emails across different folders

**Steps**:
1. View emails in "Inbox"
2. Star important emails
3. Move emails to "Archive"
4. Delete emails (moved to "Trash")
5. Search across all folders

**Observability**:
- Database operations for email status updates
- Search index maintenance

## 🔧 Technical Architecture

### Service Communication
```
Client → API Gateway → Microservices
                    ↓
               Distributed Tracing (Jaeger)
                    ↓
Infrastructure Services (DB, Cache, Storage)
```

### Data Flow Examples

**Email Creation Flow**:
1. UI → API Gateway → Auth Service (validate token)
2. API Gateway → Email Service → Spam Service (check content)
3. Email Service → Database (store email)
4. Email Service → Search Service (index for search)
5. Email Service → Notification Service (notify recipient)

**File Upload Flow**:
1. UI → API Gateway → Attachment Service
2. Attachment Service → Auth Service (validate)
3. Attachment Service → MinIO (store file)
4. Attachment Service → Database (store metadata)

### Database Schema
- **Users**: Authentication, profiles, storage quotas
- **Emails**: Message content, metadata, relationships
- **Attachments**: File metadata with S3 references
- **Notifications**: Real-time event messages
- **Folders**: Email organization structure

## 🛠️ Development & Customization

### Adding New Services
1. Create service directory under `services/`
2. Implement with FastAPI and tracing
3. Add to `docker-compose.yml`
4. Update API Gateway routing
5. Add health checks and documentation

### Extending the UI
1. Add new components under `ui/src/components/`
2. Update routing in `Dashboard.js`
3. Integrate with backend APIs
4. Add to navigation menu

### Custom Tracing
```python
# In any service
from shared.tracing import tracer, create_span_attributes

@app.post("/endpoint")
async def my_endpoint():
    with tracer.start_as_current_span("operation_name", 
         attributes=create_span_attributes(param="value")):
        # Your business logic
        pass
```

## 🐛 Troubleshooting

### Common Issues

**Services Not Starting**:
```bash
# Check service logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Full cleanup and restart
./scripts/stop-demo.sh
./scripts/start-demo.sh
```

**Memory Issues**:
- Ensure at least 8GB RAM available
- Adjust Elasticsearch memory: `ES_JAVA_OPTS=-Xms256m -Xmx256m`

**Port Conflicts**:
- Check if ports are in use: `netstat -tlnp | grep :8000`
- Modify port mappings in `docker-compose.yml`

**Database Connection Issues**:
- Wait for PostgreSQL health check to pass
- Check database logs: `docker-compose logs postgres`

### Debugging Traces
1. Open Jaeger UI: http://localhost:16686
2. Search by service name or operation
3. View trace timeline and spans
4. Check for errors or performance bottlenecks

### Performance Optimization
- Adjust service replicas in `docker-compose.yml`
- Tune database connection pools
- Configure caching strategies
- Optimize Elasticsearch mappings

## 📊 Metrics & Analytics

### Key Performance Indicators
- **Request Latency**: P95 response times across services
- **Error Rates**: HTTP 4xx/5xx error percentages
- **Throughput**: Requests per second per service
- **Resource Usage**: CPU, memory, disk per service

### Business Metrics
- **Email Volume**: Emails sent/received per day
- **Spam Detection**: Accuracy and false positive rates
- **Storage Usage**: Attachment storage growth
- **User Engagement**: Active users and feature usage

## 🚦 Production Considerations

### Security
- Replace demo JWT secret with strong random key
- Enable HTTPS/TLS for all communications
- Implement rate limiting and API quotas
- Add input validation and sanitization
- Use secrets management for credentials

### Scalability
- Implement horizontal pod autoscaling
- Add database read replicas
- Use Redis clustering for cache
- Implement message queues for async processing
- Add load balancers with health checks

### Reliability
- Add circuit breakers between services
- Implement retry policies with backoff
- Use distributed locks for critical sections
- Add comprehensive error handling
- Implement graceful shutdown procedures

### Monitoring
- Add Prometheus for metrics collection
- Implement alerting with AlertManager
- Create dashboards with Grafana
- Add structured logging with ELK stack
- Monitor business KPIs and SLAs

## 🛑 Cleanup

### Stop the Demo
```bash
./scripts/stop-demo.sh
```

### Complete Cleanup (removes all Docker resources)
```bash
./scripts/stop-demo.sh
# Answer 'y' when prompted to clean up Docker resources
```

## 📚 Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Tracing Tutorial](https://www.jaegertracing.io/docs/getting-started/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

## 💡 Next Steps

1. **Explore the UI**: Login and test all features
2. **Generate Traces**: Use the application to create distributed traces
3. **View Observability**: Check Jaeger for request flows
4. **Customize**: Extend services or add new features
5. **Deploy**: Adapt for Kubernetes or cloud deployment

---

**Happy exploring! 🎉**

This demo represents a production-ready microservices architecture with comprehensive observability, perfect for understanding distributed systems concepts and demonstrating system design skills to customers.