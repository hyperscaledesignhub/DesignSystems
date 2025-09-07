import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { notificationAPI, gatewayAPI } from '../services/api';
import wsService from '../services/websocket';
import { 
  User, 
  LogOut, 
  Bell, 
  Settings, 
  Home, 
  FolderOpen, 
  Upload,
  Search,
  Activity,
  Server,
  Wifi,
  WifiOff
} from 'lucide-react';
import toast from 'react-hot-toast';

const Layout = ({ children, activeTab, onTabChange }) => {
  const { user, logout } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [systemStats, setSystemStats] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Load notifications
    if (user?.user_id) {
      loadNotifications();
      loadOnlineUsers();
      loadSystemStats();
    }

    // WebSocket connection status
    const checkConnection = () => {
      setIsConnected(wsService.isConnected());
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);

    // Listen for new notifications
    const handleNotification = (notification) => {
      setNotifications(prev => [notification, ...prev.slice(0, 9)]);
    };

    const handleBroadcast = (data) => {
      console.log('Broadcast received in layout:', data);
    };

    wsService.on('notification', handleNotification);
    wsService.on('broadcast', handleBroadcast);

    return () => {
      clearInterval(interval);
      wsService.off('notification', handleNotification);
      wsService.off('broadcast', handleBroadcast);
    };
  }, [user]);

  const loadNotifications = async () => {
    try {
      const response = await notificationAPI.getHistory(user.user_id);
      setNotifications(response.data.notifications?.slice(0, 10) || []);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  };

  const loadOnlineUsers = async () => {
    try {
      const response = await notificationAPI.getOnlineUsers();
      setOnlineUsers(response.data.online_users || []);
    } catch (error) {
      console.error('Failed to load online users:', error);
    }
  };

  const loadSystemStats = async () => {
    try {
      const response = await gatewayAPI.getStats();
      setSystemStats(response.data);
    } catch (error) {
      console.error('Failed to load system stats:', error);
    }
  };

  const handleLogout = async () => {
    await logout();
  };

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'files', label: 'Files', icon: FolderOpen },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'search', label: 'Search', icon: Search },
    { id: 'activity', label: 'Activity', icon: Activity },
    { id: 'admin', label: 'Admin', icon: Server },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-gradient-to-r from-google-blue to-google-green rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">GD</span>
                </div>
                <span className="text-xl font-semibold text-gray-900">Google Drive MVP</span>
              </div>
            </div>

            {/* Connection Status */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                {isConnected ? (
                  <Wifi className="h-4 w-4 text-green-500" />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-500" />
                )}
                <span className={`text-sm ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>

              {/* System Stats */}
              {systemStats && (
                <div className="text-sm text-gray-600">
                  <span>Rate Limit: {systemStats.rate_limit?.requests_remaining || 0}/60</span>
                </div>
              )}

              {/* User Menu */}
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <User className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium text-gray-700">{user?.username}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-900"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex space-x-6">
          {/* Sidebar */}
          <div className="w-64 flex-shrink-0">
            <nav className="space-y-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => onTabChange(tab.id)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-google-blue text-white'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>

            {/* Recent Notifications */}
            <div className="mt-8">
              <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                <Bell className="h-4 w-4 mr-2" />
                Recent Notifications
              </h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="text-sm text-gray-500">No notifications</p>
                ) : (
                  notifications.map((notification) => (
                    <div
                      key={notification.notification_id}
                      className="bg-white p-3 rounded-lg shadow-sm border text-sm"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-gray-900">{notification.message}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(notification.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                        {!notification.read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-1"></div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Online Users */}
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                Online Users ({onlineUsers.length})
              </h3>
              <div className="space-y-1">
                {onlineUsers.length === 0 ? (
                  <p className="text-sm text-gray-500">No users online</p>
                ) : (
                  onlineUsers.map((userId) => (
                    <div key={userId} className="flex items-center space-x-2 text-sm">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-gray-600">{userId.substring(0, 8)}...</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Layout;