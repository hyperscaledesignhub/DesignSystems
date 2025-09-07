import { io } from 'socket.io-client';
import toast from 'react-hot-toast';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.listeners = new Map();
  }

  connect(userId, token) {
    // Temporarily disable WebSocket to get basic demo working
    console.log('WebSocket connection disabled for demo');
    return;
    
    if (this.socket && this.connected) {
      return;
    }

    const url = process.env.NODE_ENV === 'development' 
      ? 'http://localhost:9005' 
      : window.location.origin.replace(/:\d+/, ':9005');

    this.socket = io(url, {
      query: { token },
      transports: ['websocket', 'polling']
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.connected = true;
      toast.success('Connected to real-time notifications');
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      this.connected = false;
      toast.error('Disconnected from real-time notifications');
    });

    this.socket.on('notification', (notification) => {
      console.log('Received notification:', notification);
      this.emit('notification', notification);
      
      // Show toast notification
      const message = notification.message || 'New notification';
      switch (notification.type) {
        case 'file_upload':
          toast.success(`📁 ${message}`, { icon: '📁' });
          break;
        case 'file_delete':
          toast.error(`🗑️ ${message}`, { icon: '🗑️' });
          break;
        case 'file_share':
          toast.success(`🤝 ${message}`, { icon: '🤝' });
          break;
        case 'system_message':
          toast(`📢 ${message}`, { icon: '📢', duration: 5000 });
          break;
        default:
          toast(`🔔 ${message}`, { icon: '🔔' });
      }
    });

    this.socket.on('broadcast', (data) => {
      console.log('Received broadcast:', data);
      this.emit('broadcast', data);
      toast(`📢 ${data.message}`, { 
        icon: '📢', 
        duration: 5000,
        style: {
          background: '#f3f4f6',
          border: '1px solid #d1d5db'
        }
      });
    });

    this.socket.on('user_status', (data) => {
      console.log('User status update:', data);
      this.emit('user_status', data);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      toast.error('Failed to connect to notifications');
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      this.listeners.clear();
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      const index = eventListeners.indexOf(callback);
      if (index > -1) {
        eventListeners.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => callback(data));
    }
  }

  sendMessage(type, data) {
    if (this.socket && this.connected) {
      this.socket.emit(type, data);
    }
  }

  isConnected() {
    return this.connected;
  }
}

const wsService = new WebSocketService();
export default wsService;