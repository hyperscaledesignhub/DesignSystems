# 🌐 S3 Storage System - Web UI Guide

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start all services including UI
docker-compose -f docker-compose-with-ui.yml up -d

# Wait for services to start
sleep 60

# Get API key
API_KEY=$(docker-compose -f docker-compose-with-ui.yml logs identity-service | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //')

echo "🌐 Web UI: http://localhost:9347"
echo "🔑 API Key: $API_KEY"
```

### Option 2: Manual Setup

```bash
# 1. Start backend services
docker-compose up -d

# 2. Start Web UI
cd web-ui
pip install -r requirements.txt
S3_API_URL=http://localhost:7841 python app.py

# 3. Access UI at http://localhost:9347
```

## 📱 User Interface Features

### 🔐 **Login Page**
- **API Key Authentication**: Enter your S3 API key to access the system
- **Secure Login**: API key validation against identity service
- **Help Section**: Instructions for obtaining API keys
- **Responsive Design**: Works on desktop, tablet, and mobile

### 📊 **Dashboard**
- **Storage Statistics**: Total buckets, objects, and storage usage
- **Quick Actions**: Create bucket, view buckets
- **Recent Activity**: Overview of your latest buckets
- **Visual Stats**: Color-coded statistics cards

### 🪣 **Bucket Management**
- **Create Buckets**: Simple bucket creation with validation
- **List Buckets**: Grid view of all your buckets
- **Bucket Details**: Click to view bucket contents
- **Delete Buckets**: Safe bucket deletion with confirmation

### 📁 **File Operations**
- **Upload Files**: Drag & drop or browse to upload
- **Download Files**: One-click file downloads
- **Delete Files**: Individual or bulk file deletion
- **File Preview**: Visual file type icons
- **Folder Support**: Organize files in virtual folders

### 🎯 **Advanced Features**
- **Search & Filter**: Find files quickly
- **Bulk Operations**: Select multiple files for actions
- **Grid/List View**: Switch between viewing modes
- **Progress Tracking**: Real-time upload progress
- **Error Handling**: Graceful error messages

## 🖥️ How to Use the UI

### 1. **Getting Started**

1. **Obtain API Key**:
   ```bash
   # Docker Compose
   docker-compose logs identity-service | grep "Admin API Key"
   
   # Kubernetes  
   kubectl logs -n s3-storage -l app=identity-service | grep "Admin API Key"
   ```

2. **Access Web UI**: Open http://localhost:9347 in your browser

3. **Login**: Enter your API key on the login page

### 2. **Creating Your First Bucket**

1. Click **"Create Bucket"** on dashboard or buckets page
2. Enter a bucket name (3-63 chars, lowercase, numbers, hyphens)
3. Click **"Create Bucket"**
4. Your bucket appears in the list

### 3. **Uploading Files**

1. Navigate to your bucket
2. Click **"Upload Files"**
3. **Drag & drop** files or click **"Select Files"**
4. Optionally specify a folder path
5. Click **"Upload Files"**
6. Watch progress bar for completion

### 4. **Managing Files**

- **Download**: Click the download icon next to any file
- **Delete**: Click the trash icon (with confirmation)
- **Bulk Actions**: Check multiple files and use "Delete Selected"
- **Search**: Use the search box to find files quickly
- **View Modes**: Switch between grid and list views

### 5. **Navigation**

- **Breadcrumbs**: Click to navigate back to parent folders
- **Sidebar**: Quick access to dashboard and buckets
- **Account Menu**: View API key info and logout

## 🎨 UI Screenshots Guide

### Login Page
```
┌─────────────────────────────────────┐
│  🌐 S3 Storage System              │
│                                     │
│  🔑 API Key: [s3_key_...........  ]│
│     [Show/Hide] [Login]            │
│                                     │
│  💡 How to get API Key:            │
│     docker-compose logs...          │
└─────────────────────────────────────┘
```

### Dashboard
```
┌─────────────────────────────────────┐
│ 📊 Dashboard                        │
├─────────────────────────────────────┤
│ [📦 5] [📄 23] [💾 1.2GB]          │
│ Buckets Objects Storage            │
├─────────────────────────────────────┤
│ 🚀 Quick Actions                   │
│ [Create Bucket] [View Buckets]     │
├─────────────────────────────────────┤
│ 🪣 Your Buckets                    │
│ my-bucket-1  my-bucket-2  ...      │
└─────────────────────────────────────┘
```

### Bucket Detail
```
┌─────────────────────────────────────┐
│ 🪣 my-bucket > folder1 > folder2   │
│ [Upload] [New Folder] [Refresh]    │
├─────────────────────────────────────┤
│ 🔍 [Search...] [Grid] [List]       │
├─────────────────────────────────────┤
│ ☑ Name          Size     Modified   │
│ ☐ 📁 images/    -        -          │
│ ☐ 📄 doc.pdf    1.2MB   2024-01-15 │
│ ☐ 🖼️ pic.jpg    856KB   2024-01-14 │
│ [Download] [Delete] for each file   │
└─────────────────────────────────────┘
```

## 🔧 Configuration

### Environment Variables

**Web UI Service**:
- `S3_API_URL`: Backend API Gateway URL (default: http://localhost:7841)
- `FLASK_ENV`: development/production
- `SECRET_KEY`: Flask session secret (auto-generated)

### Customization

**Themes**: The UI supports light/dark mode detection
**Responsive**: Automatically adapts to screen size
**Icons**: Uses Bootstrap Icons for consistent design

## 🚨 Troubleshooting

### Common Issues

#### "Cannot connect to API"
```bash
# Check if backend services are running
curl http://localhost:7841/health

# Check Docker containers
docker-compose ps

# Check Web UI logs
docker-compose logs web-ui
```

#### "Invalid API Key"
```bash
# Get fresh API key
docker-compose logs identity-service | grep "Admin API Key"

# Try the new key in the UI
```

#### "Upload fails"
- Check file size (max 100MB by default)
- Verify bucket name is valid
- Check network connectivity
- Look at browser developer tools for errors

#### "UI doesn't load"
```bash
# Check if web-ui container is running
docker-compose ps web-ui

# Check web-ui logs
docker-compose logs web-ui

# Try restarting web-ui
docker-compose restart web-ui
```

### Browser Compatibility

**Supported Browsers**:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Required Features**:
- JavaScript enabled
- Local storage support
- File API support (for uploads)

## 🧪 Testing the UI

### Automated Testing

```bash
# Install Selenium (for automated testing)
pip install selenium

# Download ChromeDriver
# https://chromedriver.chromium.org/

# Run UI tests
API_KEY="your_api_key" python test-ui.py
```

### Manual Testing Checklist

**Login Flow**:
- [ ] Login page loads
- [ ] Invalid API key shows error
- [ ] Valid API key redirects to dashboard
- [ ] Logout works correctly

**Bucket Operations**:
- [ ] Create bucket with valid name
- [ ] Create bucket with invalid name shows error
- [ ] List buckets displays correctly
- [ ] Open bucket shows detail page
- [ ] Delete bucket works with confirmation

**File Operations**:
- [ ] Upload single file
- [ ] Upload multiple files
- [ ] Upload to folder
- [ ] Download file
- [ ] Delete file
- [ ] Bulk select and delete

**UI/UX**:
- [ ] Responsive design on mobile
- [ ] Search functionality
- [ ] Grid/list view toggle
- [ ] Progress indicators
- [ ] Error messages
- [ ] Navigation breadcrumbs

## 📊 Performance Considerations

### Frontend Optimization
- **Lazy Loading**: Large file lists load progressively
- **Caching**: API responses cached where appropriate
- **Compression**: Assets served compressed
- **CDN**: Bootstrap/icons served from CDN

### Upload Performance
- **Chunked Uploads**: Large files uploaded in chunks (TODO)
- **Progress Tracking**: Real-time upload progress
- **Error Recovery**: Failed uploads can be retried
- **Background Processing**: Multiple uploads in parallel

### Scalability
- **Stateless**: Web UI is completely stateless
- **Load Balancing**: Can run multiple UI instances
- **Session Storage**: Uses secure session cookies
- **API Calls**: Efficient API usage with minimal requests

## 🔐 Security Features

### Authentication
- **API Key Based**: Secure API key authentication
- **Session Management**: Secure session handling
- **Auto Logout**: Sessions expire for security

### Data Security
- **HTTPS Ready**: Supports TLS/SSL in production
- **Input Validation**: All inputs validated client and server side
- **XSS Protection**: Template escaping prevents XSS
- **CSRF Protection**: Flask CSRF tokens

### Privacy
- **No Data Storage**: UI doesn't store user data locally
- **Minimal Logging**: Only essential logs kept
- **Secure Headers**: Security headers in HTTP responses

This Web UI provides a complete, user-friendly interface for your S3 Storage System! 🎉