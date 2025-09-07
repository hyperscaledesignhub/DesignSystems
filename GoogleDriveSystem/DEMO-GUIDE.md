# Google Drive MVP - Demo Guide 🚀

A complete microservices-based file storage system with a modern React UI for demonstration.

## 🎯 Quick Start Demo

### 1. Start All Services
```bash
./start-all.sh
```

This will:
- Start all infrastructure services (PostgreSQL, Redis, MinIO)
- Build and start all microservices  
- Install and start the React UI
- Verify all services are healthy

### 2. Access the Demo UI
Once started, open: **http://localhost:3000**

**Demo Credentials (use email to login):**
- Email: `demo@example.com`
- Password: `demo123`

**Alternative Test Account:**
- Email: `test@example.com`
- Password: `test123`

### 3. Features to Demo

#### 🔐 Authentication
- Login/Register with JWT tokens
- Session management with automatic token refresh

#### 📁 File Management  
- **Upload Files**: Drag & drop or select files
- **Download Files**: Click download on any file
- **Rename Files**: Edit file names inline
- **Share Files**: Share with other users
- **Delete Files**: Remove files safely

#### 🔍 Search & Discovery
- **Search Files**: Find files by name, content, or metadata
- **Search History**: Recent searches are saved
- **Metadata Filtering**: Filter by file type, size, date

#### 🔔 Real-time Notifications
- **Live Updates**: WebSocket notifications for all file operations
- **Activity Log**: Complete history of all operations
- **System Notifications**: Upload progress, errors, success messages

#### 📊 Dashboard & Monitoring
- **System Health**: Real-time service status
- **Storage Stats**: File counts, storage usage, user activity  
- **Service Metrics**: Response times, error rates

#### 🛠️ Admin Panel
- **Service Management**: Monitor and restart services
- **User Management**: View and manage users
- **System Stats**: Detailed system metrics
- **Notification Management**: View all system notifications

#### 🏗️ Architecture Demo
- **Multiple Upload Methods**: File Service vs Block Service
- **Microservices**: Each service operates independently
- **Load Balancing**: API Gateway routes requests
- **Data Consistency**: Cross-service data synchronization

## 🎨 UI Features

### Modern Design
- **Responsive Layout**: Works on desktop and mobile
- **Google Material Design**: Clean, professional interface
- **Real-time Updates**: Live data without page refresh
- **Progress Indicators**: Visual feedback for all operations

### Interactive Components
- **Drag & Drop**: Intuitive file uploads
- **Breadcrumb Navigation**: Easy folder navigation
- **Modal Dialogs**: Clean forms and confirmations
- **Toast Notifications**: Non-intrusive feedback

## 🔧 Service Architecture

The UI demonstrates integration with:

| Service | Port | Purpose |
|---------|------|---------|
| **UI Service** | 3000 | React frontend |
| **API Gateway** | 9010 | Request routing & rate limiting |
| **Auth Service** | 9011 | User authentication |
| **File Service** | 9012 | File upload/download |
| **Metadata Service** | 9003 | File metadata & search |
| **Block Service** | 9004 | Advanced file processing |
| **Notification Service** | 9005 | Real-time notifications |

## 🎪 Demo Scenarios

### Basic File Operations
1. Upload a file using drag & drop
2. See real-time notification
3. View file in File Manager
4. Download the file
5. Check activity log

### Advanced Features  
1. Upload large file to see progress
2. Search for files using metadata
3. Share file with another user
4. Use Block Service upload mode
5. Monitor system in Admin panel

### Real-time Collaboration
1. Open UI in multiple browser tabs
2. Upload file in one tab
3. See instant notification in other tab
4. Demonstrate WebSocket real-time updates

## 🛑 Stopping the Demo

```bash
./stop-all.sh
```

This will cleanly stop:
- React UI service
- All microservices containers
- Infrastructure containers
- Clean up resources

## 💡 Customization

### Demo Data
- Login as different users to see isolated data
- Create test files of different sizes and types
- Test error scenarios (invalid files, network issues)

### Development Mode
- UI runs in development mode with hot reload
- API calls go through the Gateway service
- WebSocket connects directly to Notification service
- All logs available in `ui-service/ui-service.log`

## 🐛 Troubleshooting

### UI Won't Start
```bash
cd ui-service
npm install
npm start
```

### Services Not Responding
```bash
docker ps
docker logs <service-name>
```

### Port Conflicts
Check if ports 3000, 9000-9012 are available:
```bash
lsof -i :3000
```

---

**🎉 Ready to Demo!** The UI provides a comprehensive view of all MVP features in an intuitive, professional interface perfect for showcasing the microservices architecture.