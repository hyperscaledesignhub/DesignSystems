# Hotel Booking System Demo

A comprehensive microservices-based hotel booking system with React frontend for demonstration purposes.

## 🏗️ Architecture

**Microservices:**
- **Hotel Service** (Port 8001): Hotel management and information
- **Room Service** (Port 8002): Room types and specifications  
- **Guest Service** (Port 8003): Guest registration and authentication
- **Inventory Service** (Port 8004): Room availability and reservation management
- **Reservation Service** (Port 8005): Booking coordination and management
- **Payment Service** (Port 8006): Payment processing (mock implementation)

**Infrastructure:**
- **PostgreSQL**: Separate databases per service
- **Redis**: Caching for hotel data
- **Docker**: Containerized services with custom networking
- **React**: Frontend UI with comprehensive workflow coverage

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js and npm
- PostgreSQL client (optional)

### Start Demo
```bash
./start-demo.sh
```
This single command starts all backend services in Docker containers and the React frontend locally.

### Stop Demo
```bash
./stop-demo.sh
```
This stops both the Docker containers and the React frontend.

## 🎯 Demo Features

### 1. Hotel Management Workflow
- **List Hotels**: Browse available hotels with location and details
- **View Hotel Details**: Get specific hotel information (name, address, location)
- **Demo Hotels**: Pre-loaded with Grand Plaza Hotel and City Center Inn

### 2. Room Management Workflow  
- **Browse Room Types**: View available room types for each hotel
- **View Room Details**: Room specifications (occupancy, price, amenities)
- **Create Room Types**: Add new room types with custom pricing and occupancy

### 3. Guest Registration Workflow
- **Register Guest**: Create new guest account with email, name, phone
- **Login Authentication**: Secure login with email uniqueness enforcement
- **Guest Profile**: Retrieve and manage guest information

### 4. Complete Booking Workflow (6 Steps)
1. **Guest Registration** → Login or create account
2. **Browse Hotels** → Select from available hotels  
3. **Select Room Type** → Choose room with pricing details
4. **Check Availability** → Real-time availability for date ranges
5. **Create Reservation** → Book rooms with concurrency control
6. **Process Payment** → Handle payment (mock implementation)

### 5. Inventory Management Workflow
- **Check Availability**: Real-time room availability for date ranges
- **Reserve Inventory**: Lock rooms during booking process with database constraints
- **Release Inventory**: Free up rooms on cancellation
- **Concurrency Demo**: Visual demonstration of database-level concurrency control

### 6. Payment Processing Workflow
- **Process Payment**: Handle payment for reservations (always successful for demo)
- **Payment Methods**: Credit card, debit card, PayPal, bank transfer, Apple Pay, Google Pay  
- **Multiple Currencies**: USD, EUR, GBP, JPY, CAD support
- **Payment History**: Complete audit trail with timestamps

### 7. Reservation Management Workflow
- **Create Reservation**: Book rooms with atomic operations and concurrency control
- **View Reservations**: Get booking details and status
- **Cancel Reservation**: Cancel existing bookings with inventory release
- **Status Tracking**: Confirmed, pending, cancelled status management

## 🔒 Concurrency Control Features

### Database-Level Protection
- **CHECK Constraints**: `total_reserved ≤ total_inventory` prevents overbooking
- **Atomic Updates**: Conditional updates only if sufficient inventory available
- **Row-Level Locking**: PostgreSQL handles concurrent access safely
- **Transaction Isolation**: READ COMMITTED isolation level for consistency

### Demonstration
The system includes a dedicated Concurrency Control demo page that shows:
- Real-time inventory status
- Reserve/Release actions that simulate booking/cancellation
- Visual feedback on database constraints
- Instructions for testing concurrent requests

## 🎮 Demo Usage

### Login Credentials
- **Email**: demo@example.com  
- **Password**: password123

### Test Workflows
1. **Start with Hotels**: Browse and select a hotel
2. **View Rooms**: Check available room types and pricing
3. **Make Booking**: Complete the 6-step booking process
4. **Check Inventory**: Test availability and concurrency features
5. **Process Payment**: Test payment workflow with multiple methods
6. **Manage Reservations**: View, cancel, and track reservation status

### Testing Concurrency
1. Navigate to Inventory Management
2. Select hotel, room type, and dates
3. Check availability to see current inventory
4. Use Reserve/Release buttons to simulate booking actions
5. Try multiple browser tabs for concurrent testing
6. Observe database constraints preventing overbooking

## 🌐 Service Endpoints

| Service | Port | Health Check |
|---------|------|--------------|
| Hotel | 8001 | http://localhost:8001/health |
| Room | 8002 | http://localhost:8002/health |  
| Guest | 8003 | http://localhost:8003/health |
| Inventory | 8004 | http://localhost:8004/health |
| Reservation | 8005 | http://localhost:8005/health |
| Payment | 8006 | http://localhost:8006/health |

## 🏷️ Key Technical Features

- **Microservices Architecture**: Independent, scalable services
- **Database Per Service**: Isolated data storage with PostgreSQL  
- **Service Mesh Communication**: HTTP-based inter-service communication
- **Container Networking**: Docker network for secure service communication
- **Caching Layer**: Redis for improved hotel data performance
- **Database Concurrency**: Prevents race conditions and data corruption
- **Mock Payment Processing**: Simulated payment gateway integration
- **React SPA**: Single-page application with routing and state management
- **RESTful APIs**: Standard HTTP methods and status codes
- **Error Handling**: Comprehensive error messages and user feedback

## 🔍 Monitoring and Debugging

### Service Logs
```bash
docker logs hotel-service
docker logs room-service  
docker logs guest-service
docker logs inventory-service
docker logs reservation-service
docker logs payment-service
```

### Database Access
```bash
docker exec -it postgres-db psql -U postgres -d hotel_db
docker exec -it postgres-db psql -U postgres -d guest_db
docker exec -it postgres-db psql -U postgres -d inventory_db  
docker exec -it postgres-db psql -U postgres -d reservation_db
docker exec -it postgres-db psql -U postgres -d payment_db
```

### Redis Access  
```bash
docker exec -it redis-cache redis-cli
```

## 🎨 Frontend Features

- **Responsive Design**: Works on desktop and mobile devices
- **Navigation**: React Router with protected routes
- **Authentication**: Login/logout with session management  
- **Form Validation**: Input validation and error handling
- **Real-time Updates**: Dynamic data fetching and state updates
- **Visual Feedback**: Loading states, success/error messages
- **Interactive Tables**: Sortable data with pagination
- **Status Badges**: Color-coded status indicators
- **Currency Formatting**: Proper currency display for multiple regions

## 🚨 Troubleshooting

### Services Won't Start
- Check Docker is running
- Verify ports 8001-8006 and 3000 are available  
- Wait for databases to initialize (15-20 seconds)

### Frontend Issues
- Run `npm install` in frontend directory
- Check Node.js version compatibility (14+ recommended)
- Clear browser cache and cookies

### Database Connection Issues
- Verify PostgreSQL container is running
- Check database initialization logs
- Ensure proper network connectivity

### Concurrency Testing
- Use multiple browser tabs or incognito windows
- Check database logs for constraint violations
- Monitor inventory levels in real-time

---

**Demo Status**: ✅ Ready for Presentation
**Last Updated**: January 2025  
**Version**: 1.0.0