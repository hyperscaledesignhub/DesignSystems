# News Feed UI Service

A modern React-based user interface for the News Feed System.

## Features

### 🔐 Authentication
- **User Registration**: Create new accounts with username/email/password
- **User Login**: Secure JWT-based authentication
- **Protected Routes**: Automatic redirection for unauthenticated users
- **Token Management**: Automatic token refresh and validation

### 📰 News Feed
- **Real-time Feed**: Personalized news feed from friends' posts
- **Post Creation**: Rich text post creation with instant publishing
- **Post Management**: Delete your own posts with confirmation
- **Feed Refresh**: Manual feed refresh to get latest posts
- **Infinite Scrolling**: Load more posts as you scroll (future enhancement)

### 👥 Social Features
- **Friends Management**: Add/remove friends by user ID
- **Friends List**: View all your current friends
- **Friend Suggestions**: Discover new friends to connect with
- **User Profiles**: View user details and activity

### 🔔 Notifications
- **Real-time Notifications**: Get notified of friend requests and new posts
- **Notification Center**: View all notifications with read/unread status
- **Batch Actions**: Mark all notifications as read
- **Notification Types**: Support for different notification types with icons

### 🎨 User Interface
- **Material-UI Design**: Modern, responsive design using MUI components
- **Responsive Layout**: Works on desktop, tablet, and mobile devices
- **Dark/Light Themes**: Automatic theme switching based on system preferences
- **Interactive Elements**: Smooth animations and user feedback
- **Accessibility**: Full keyboard navigation and screen reader support

## Tech Stack

- **Frontend**: React 18 with Hooks and Context API
- **UI Library**: Material-UI (MUI) v5
- **Routing**: React Router v6 with protected routes
- **State Management**: React Context + Local State
- **HTTP Client**: Axios with interceptors for authentication
- **Icons**: Material-UI Icons
- **Build Tool**: Create React App

## Getting Started

### Prerequisites
- Node.js 16+ and npm
- Backend services running on their respective ports

### Installation

```bash
cd ui-service
npm install
```

### Development Server

```bash
npm start
```

The UI will be available at `http://localhost:3000`

### Production Build

```bash
npm run build
```

## API Integration

The UI service communicates with all backend services through the API Gateway at `http://localhost:8370`.

### Service Endpoints Used:
- **Authentication**: `/api/v1/auth/*` (User Service)
- **User Management**: `/api/v1/users/*` (User Service)
- **Posts**: `/api/v1/posts/*` (Post Service)
- **Social Graph**: `/api/v1/graph/*` (Graph Service)
- **News Feed**: `/api/v1/feed/*` (News Feed Service)
- **Notifications**: `/api/v1/notifications/*` (Notification Service)

## Component Structure

```
src/
├── components/          # Reusable UI components
│   ├── CreatePost.js   # Post creation form
│   ├── PostCard.js     # Individual post display
│   ├── FriendsPanel.js # Friends management sidebar
│   ├── NotificationPanel.js # Notifications sidebar
│   └── PrivateRoute.js # Route protection
├── pages/              # Main application pages
│   ├── Login.js        # Login page
│   ├── Register.js     # Registration page
│   └── Dashboard.js    # Main dashboard
├── services/           # API service layer
│   └── api.js         # Axios configuration and API calls
├── hooks/              # Custom React hooks
│   └── useAuth.js     # Authentication context and logic
└── utils/              # Helper functions
```

## Features Demo

### Authentication Flow
1. **New User**: Register → Auto-login → Dashboard
2. **Returning User**: Login → Dashboard
3. **Token Expiry**: Auto-logout → Login page

### Social Interactions
1. **Add Friend**: Enter user ID → Send friend request
2. **Create Post**: Type content → Publish → Auto-distribute to friends
3. **View Feed**: See friends' posts in chronological order
4. **Manage Notifications**: View and mark as read

### Responsive Design
- **Desktop**: Full 3-column layout (Friends | Feed | Notifications)
- **Tablet**: 2-column layout with collapsible panels
- **Mobile**: Single column with toggle panels

## Environment Configuration

The UI automatically proxies API requests to the backend gateway through the `proxy` setting in `package.json`:

```json
{
  "proxy": "http://localhost:8370"
}
```

This ensures all `/api/*` requests are forwarded to the API Gateway.

## Performance Features

- **Component Memoization**: Prevent unnecessary re-renders
- **Code Splitting**: Lazy load components (future enhancement)
- **Image Optimization**: Compressed avatars and media (future enhancement)
- **Caching**: Client-side caching of user data and posts
- **Bundle Optimization**: Tree shaking and minification

## Security Features

- **JWT Token Management**: Secure token storage and automatic refresh
- **CORS Protection**: Cross-origin request validation
- **Input Sanitization**: XSS prevention on all user inputs
- **Route Protection**: Authentication required for sensitive routes
- **Logout on Token Expiry**: Automatic security cleanup

## Browser Support

- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

## Future Enhancements

- [ ] Real-time notifications via WebSocket
- [ ] Image upload and media posts
- [ ] Post reactions (like, share, comment)
- [ ] Direct messaging between users
- [ ] Advanced search functionality
- [ ] Dark/light theme toggle
- [ ] Offline support with PWA
- [ ] Push notifications
- [ ] Mobile app with React Native