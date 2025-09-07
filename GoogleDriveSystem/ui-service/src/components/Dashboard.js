import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { gatewayAPI, fileAPI, notificationAPI, blockAPI } from '../services/api';
import { 
  Activity, 
  HardDrive, 
  Users, 
  FileText, 
  Upload, 
  Download,
  Server,
  Zap,
  Clock,
  Shield
} from 'lucide-react';

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    files: 0,
    storage: 0,
    notifications: 0,
    connections: 0
  });
  const [systemHealth, setSystemHealth] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load system health
      const healthResponse = await gatewayAPI.getServices();
      setSystemHealth(healthResponse.data);

      // Load gateway stats
      const statsResponse = await gatewayAPI.getStats();
      
      // Load file count
      try {
        const filesResponse = await fileAPI.list();
        setStats(prev => ({ ...prev, files: filesResponse.data.files?.length || 0 }));
      } catch (error) {
        console.log('Files API not available');
      }

      // Load notifications
      try {
        const notifResponse = await notificationAPI.getHistory(user.user_id);
        setStats(prev => ({ 
          ...prev, 
          notifications: notifResponse.data.total || 0 
        }));
        
        // Set recent activity from notifications
        setRecentActivity(notifResponse.data.notifications?.slice(0, 5) || []);
      } catch (error) {
        console.log('Notifications API not available');
      }

      // Load block service stats
      try {
        const blockResponse = await blockAPI.getStats();
        setStats(prev => ({ 
          ...prev, 
          storage: blockResponse.data.total_storage || 0 
        }));
      } catch (error) {
        console.log('Block API not available');
      }

      // Set rate limit info
      if (statsResponse.data.rate_limit) {
        setStats(prev => ({ 
          ...prev, 
          rateLimitRemaining: statsResponse.data.rate_limit.requests_remaining || 0 
        }));
      }

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getServiceStatus = (services) => {
    if (!services) return { total: 0, healthy: 0 };
    
    let total = 0;
    let healthy = 0;
    
    Object.values(services).forEach(serviceInstances => {
      Object.values(serviceInstances).forEach(status => {
        total++;
        if (status) healthy++;
      });
    });
    
    return { total, healthy };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-google-blue"></div>
      </div>
    );
  }

  const serviceStatus = getServiceStatus(systemHealth);

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-google-blue to-google-green rounded-lg p-6 text-white">
        <h1 className="text-3xl font-bold">Welcome back, {user?.username}!</h1>
        <p className="text-blue-100 mt-2">
          Here's what's happening with your Google Drive MVP system today.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Files</p>
              <p className="text-2xl font-bold text-gray-900">{stats.files}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100">
              <HardDrive className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Storage Used</p>
              <p className="text-2xl font-bold text-gray-900">{formatBytes(stats.storage)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-yellow-100">
              <Activity className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Notifications</p>
              <p className="text-2xl font-bold text-gray-900">{stats.notifications}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-red-100">
              <Zap className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Rate Limit</p>
              <p className="text-2xl font-bold text-gray-900">{stats.rateLimitRemaining || 60}/60</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Health */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Server className="h-5 w-5 mr-2" />
            System Health
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Services Status</span>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  serviceStatus.healthy === serviceStatus.total ? 'bg-green-500' : 'bg-yellow-500'
                }`}></div>
                <span className="text-sm text-gray-900">
                  {serviceStatus.healthy}/{serviceStatus.total} Healthy
                </span>
              </div>
            </div>

            <div className="space-y-2">
              {systemHealth && Object.entries(systemHealth).map(([service, instances]) => (
                <div key={service} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 capitalize">{service} Service</span>
                  <div className="flex items-center space-x-2">
                    {Object.entries(instances).map(([url, status]) => (
                      <div
                        key={url}
                        className={`w-2 h-2 rounded-full ${
                          status ? 'bg-green-500' : 'bg-red-500'
                        }`}
                        title={url}
                      ></div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Clock className="h-5 w-5 mr-2" />
            Recent Activity
          </h3>
          
          <div className="space-y-3">
            {recentActivity.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">
                No recent activity
              </p>
            ) : (
              recentActivity.map((activity) => (
                <div
                  key={activity.notification_id}
                  className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex-shrink-0">
                    {activity.type === 'file_upload' && (
                      <Upload className="h-4 w-4 text-green-600" />
                    )}
                    {activity.type === 'file_download' && (
                      <Download className="h-4 w-4 text-blue-600" />
                    )}
                    {activity.type === 'file_delete' && (
                      <Shield className="h-4 w-4 text-red-600" />
                    )}
                    {!['file_upload', 'file_download', 'file_delete'].includes(activity.type) && (
                      <Activity className="h-4 w-4 text-gray-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900">{activity.message}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(activity.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Features Overview */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Available Features
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">File Management</h4>
            <p className="text-sm text-blue-700">
              Upload, download, organize and share your files with advanced metadata support.
            </p>
          </div>
          
          <div className="p-4 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-900 mb-2">Real-time Notifications</h4>
            <p className="text-sm text-green-700">
              Get instant notifications about file changes and system events.
            </p>
          </div>
          
          <div className="p-4 bg-purple-50 rounded-lg">
            <h4 className="font-medium text-purple-900 mb-2">Block Storage</h4>
            <p className="text-sm text-purple-700">
              Advanced file splitting, compression, and encryption for optimal storage.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;