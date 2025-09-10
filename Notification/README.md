# Notification System Demo

A complete demonstration of a scalable notification system supporting Email, SMS, and Push notifications.

## 🚀 Quick Start

### Prerequisites
- Docker installed and running
- Node.js (v14+) and npm
- Port availability: 7841-7847, 3000

### Start the System

```bash
cd demo/scripts
./startup.sh
```

This will:
1. Create Docker network
2. Start Redis (port 7847)
3. Build and start all services as individual Docker containers
4. Start the UI on http://localhost:3000

### Stop the System

```bash
cd demo/scripts
./stop.sh
```

## 🏗️ Architecture

### Services and Ports

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 7841 | Entry point for all notifications |
| Notification Server | 7842 | Core processing and routing |
| Email Worker | 7843 | Email delivery via SMTP |
| SMS Worker | 7844 | SMS delivery via Twilio |
| Push Worker | 7845 | Push notifications via FCM |
| User Database | 7846 | SQLite user and device storage |
| Redis | 7847 | Message queuing |
| UI | 3000 | Demo interface |

### Data Flow

```
User → UI → API Gateway → Notification Server → Redis Queue → Workers → External Services
                              ↓
                         User Database
```

## 🎯 Features

### Implemented ✅
- Multi-channel notifications (Email, SMS, Push)
- User management with contact information
- Device token management for push notifications
- Message queuing with Redis
- Basic retry mechanism (3 attempts)
- Service health monitoring
- Notification status tracking
- RESTful API endpoints
- Worker-based asynchronous processing

### Not Implemented 🚫
- Authentication & rate limiting
- Notification templates
- User preferences & opt-out
- Scheduled notifications
- Analytics & tracking
- Dead letter queues
- Advanced retry strategies

## 🖥️ Using the Demo UI

### Access the UI
Open http://localhost:3000 in your browser

### Main Features

1. **Service Status Panel**
   - Real-time health check of all services
   - Green = Online, Red = Offline

2. **User Management**
   - Create users with email/phone
   - Add device tokens for push notifications

3. **Send Notifications**
   - Select notification type (Email/SMS/Push)
   - Enter user ID and message
   - Send individual notifications

4. **Demo Scenarios**
   - **Single Email**: Create user and send email
   - **Bulk SMS**: Send SMS to multiple users
   - **Push Broadcast**: Send to multiple devices
   - **Multi-Channel**: Send via all channels
   - **Stress Test**: Send 10 notifications rapidly

5. **Notification History**
   - View sent notifications by user ID
   - Check notification status

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the scripts directory:

```bash
# Email Configuration (Gmail example)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# SMS Configuration (Twilio)
SMS_API_URL=https://api.twilio.com
SMS_API_KEY=your-twilio-account-sid
SMS_API_SECRET=your-twilio-auth-token

# Push Configuration (FCM)
FCM_SERVER_KEY=your-fcm-server-key
FCM_API_URL=https://fcm.googleapis.com/fcm/send
```

## 📝 API Documentation

### Send Notification
```http
POST http://localhost:7841/api/v1/notifications/send
Content-Type: application/json

{
  "user_id": 1,
  "type": "email",
  "subject": "Test Subject",
  "message": "Test message",
  "metadata": {}
}
```

### Create User
```http
POST http://localhost:7846/users
Content-Type: application/json

{
  "email": "user@example.com",
  "phone_number": "+1234567890",
  "country_code": "+1"
}
```

### Add Device
```http
POST http://localhost:7846/users/{user_id}/devices
Content-Type: application/json

{
  "device_token": "token123",
  "device_type": "ios"
}
```

## 🐛 Troubleshooting

### Services not starting
- Check Docker is running: `docker ps`
- Check port availability: `lsof -i :7841-7847`
- View logs: `docker logs <container-name>`

### Cannot send emails
- Configure SMTP credentials in environment variables
- For Gmail, use App Passwords, not regular password

### Redis connection issues
- Ensure Redis container is running: `docker ps | grep redis`
- Check Redis logs: `docker logs redis-service`

### UI not loading
- Check Node.js installation: `node --version`
- Install dependencies: `cd ui && npm install`
- Check console for errors (F12 in browser)

## 🧪 Testing

### Manual Testing
1. Open the UI at http://localhost:3000
2. Create a test user
3. Send a notification
4. Check notification history

### Load Testing
Use the "Stress Test" scenario in the UI to send multiple notifications rapidly.

### Health Checks
```bash
# Check all services
curl http://localhost:7841/health
curl http://localhost:7842/health
curl http://localhost:7843/health
curl http://localhost:7844/health
curl http://localhost:7845/health
curl http://localhost:7846/health
```

## 📚 Additional Resources

- [System Design Specification](../spec)
- [Minimal Features Documentation](../minimal_features/)
- [Skipped Features List](../minimal_features/skipped_features.md)

## 🤝 Contributing

This is a demo project for educational purposes. Feel free to extend and modify as needed for your learning.