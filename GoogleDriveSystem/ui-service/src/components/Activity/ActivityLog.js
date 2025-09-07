import React, { useState, useEffect } from 'react';
import { notificationAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { 
  Activity, 
  Upload, 
  Download, 
  Share, 
  Trash2, 
  Bell, 
  User,
  Calendar,
  RefreshCw,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

const ActivityLog = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all', 'unread', 'file_actions'
  const [stats, setStats] = useState({
    total: 0,
    unread: 0,
    today: 0
  });

  useEffect(() => {
    loadActivity();
  }, [user]);

  const loadActivity = async () => {
    try {
      setLoading(true);
      const response = await notificationAPI.getHistory(user.user_id);
      const data = response.data;
      
      setNotifications(data.notifications || []);
      setStats({
        total: data.total || 0,
        unread: data.unread_count || 0,
        today: getTodayCount(data.notifications || [])
      });
    } catch (error) {
      console.error('Failed to load activity:', error);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  const getTodayCount = (notifications) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    return notifications.filter(notification => {
      const notificationDate = new Date(notification.created_at);
      notificationDate.setHours(0, 0, 0, 0);
      return notificationDate.getTime() === today.getTime();
    }).length;
  };

  const markAsRead = async (notificationId) => {
    try {
      await notificationAPI.markAsRead(notificationId);
      setNotifications(notifications.map(n => 
        n.notification_id === notificationId ? { ...n, read: true } : n
      ));
      setStats(prev => ({ ...prev, unread: Math.max(0, prev.unread - 1) }));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      const unreadNotifications = notifications.filter(n => !n.read);
      await Promise.all(
        unreadNotifications.map(n => notificationAPI.markAsRead(n.notification_id))
      );
      setNotifications(notifications.map(n => ({ ...n, read: true })));
      setStats(prev => ({ ...prev, unread: 0 }));
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const getFilteredNotifications = () => {
    switch (filter) {
      case 'unread':
        return notifications.filter(n => !n.read);
      case 'file_actions':
        return notifications.filter(n => 
          ['file_upload', 'file_download', 'file_delete', 'file_share'].includes(n.type)
        );
      default:
        return notifications;
    }
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'file_upload':
        return <Upload className="h-5 w-5 text-green-600" />;
      case 'file_download':
        return <Download className="h-5 w-5 text-blue-600" />;
      case 'file_delete':
        return <Trash2 className="h-5 w-5 text-red-600" />;
      case 'file_share':
        return <Share className="h-5 w-5 text-purple-600" />;
      case 'system_message':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      default:
        return <Bell className="h-5 w-5 text-gray-600" />;
    }
  };

  const getActivityColor = (type) => {
    switch (type) {
      case 'file_upload': return 'bg-green-50 border-green-200';
      case 'file_download': return 'bg-blue-50 border-blue-200';
      case 'file_delete': return 'bg-red-50 border-red-200';
      case 'file_share': return 'bg-purple-50 border-purple-200';
      case 'system_message': return 'bg-yellow-50 border-yellow-200';
      default: return 'bg-gray-50 border-gray-200';
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    // Less than a minute ago
    if (diff < 60000) {
      return 'Just now';
    }
    
    // Less than an hour ago
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000);
      return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
    }
    
    // Less than a day ago
    if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000);
      return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    }
    
    // More than a day ago
    return date.toLocaleDateString() + ' at ' + date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredNotifications = getFilteredNotifications();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Activity Log</h1>
          <p className="text-gray-600">Track all your file operations and system notifications</p>
        </div>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={loadActivity}
            className="btn btn-secondary flex items-center space-x-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
          
          {stats.unread > 0 && (
            <button
              onClick={markAllAsRead}
              className="btn btn-primary flex items-center space-x-2"
            >
              <CheckCircle className="h-4 w-4" />
              <span>Mark All Read</span>
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100">
              <Activity className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Activities</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-red-100">
              <Bell className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Unread</p>
              <p className="text-2xl font-bold text-gray-900">{stats.unread}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100">
              <Calendar className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Today</p>
              <p className="text-2xl font-bold text-gray-900">{stats.today}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border p-4">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-gray-700">Filter:</span>
          <div className="flex space-x-2">
            {[
              { id: 'all', label: 'All Activities' },
              { id: 'unread', label: 'Unread' },
              { id: 'file_actions', label: 'File Actions' }
            ].map((filterOption) => (
              <button
                key={filterOption.id}
                onClick={() => setFilter(filterOption.id)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  filter === filterOption.id
                    ? 'bg-google-blue text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {filterOption.label}
                {filterOption.id === 'unread' && stats.unread > 0 && (
                  <span className="ml-1 bg-red-500 text-white text-xs px-1 py-0.5 rounded-full">
                    {stats.unread}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Activity List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-google-blue"></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="max-h-96 overflow-y-auto">
            {filteredNotifications.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No activities</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {filter === 'all' 
                    ? 'Start using the system to see your activity here.'
                    : `No ${filter.replace('_', ' ')} activities found.`}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredNotifications.map((notification) => (
                  <div
                    key={notification.notification_id}
                    className={`p-4 hover:bg-gray-50 transition-colors ${
                      !notification.read ? 'border-l-4 border-blue-500 bg-blue-50/50' : ''
                    }`}
                  >
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        {getActivityIcon(notification.type)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-900">
                            {notification.message}
                          </p>
                          {!notification.read && (
                            <button
                              onClick={() => markAsRead(notification.notification_id)}
                              className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                            >
                              Mark read
                            </button>
                          )}
                        </div>
                        
                        <div className="mt-1 flex items-center space-x-4 text-xs text-gray-500">
                          <span>{formatDate(notification.created_at)}</span>
                          <span className="capitalize">{notification.type.replace('_', ' ')}</span>
                          {!notification.read && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800">
                              New
                            </span>
                          )}
                        </div>
                        
                        {notification.data && (
                          <div className="mt-2 p-2 bg-gray-100 rounded text-xs">
                            <pre className="whitespace-pre-wrap text-gray-600">
                              {JSON.stringify(notification.data, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ActivityLog;