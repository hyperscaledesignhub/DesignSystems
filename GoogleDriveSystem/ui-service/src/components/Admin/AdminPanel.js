import React, { useState, useEffect } from 'react';
import { gatewayAPI, authAPI, notificationAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { 
  Users, 
  Server, 
  Database, 
  Activity,
  Settings,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Trash2,
  Shield,
  Clock
} from 'lucide-react';
import toast from 'react-hot-toast';

const AdminPanel = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [systemStats, setSystemStats] = useState({});
  const [users, setUsers] = useState([]);
  const [services, setServices] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAdminData();
  }, [activeTab]);

  const loadAdminData = async () => {
    try {
      setLoading(true);
      
      if (activeTab === 'overview' || activeTab === 'services') {
        const healthResponse = await gatewayAPI.getHealth();
        setServices(healthResponse.data.services || []);
        
        const statsResponse = await gatewayAPI.getStats();
        setSystemStats(statsResponse.data || {});
      }
      
      if (activeTab === 'users') {
        try {
          const usersResponse = await authAPI.getAllUsers();
          setUsers(usersResponse.data.users || []);
        } catch (error) {
          console.warn('Users endpoint not available:', error);
          setUsers([]);
        }
      }
      
      if (activeTab === 'notifications') {
        const notifResponse = await notificationAPI.getAll();
        setNotifications(notifResponse.data.notifications || []);
      }
    } catch (error) {
      console.error('Failed to load admin data:', error);
      toast.error('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleRestartService = async (serviceName) => {
    try {
      await gatewayAPI.restartService(serviceName);
      toast.success(`${serviceName} service restart initiated`);
      loadAdminData();
    } catch (error) {
      console.error('Failed to restart service:', error);
      toast.error(`Failed to restart ${serviceName} service`);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) {
      return;
    }
    
    try {
      await authAPI.deleteUser(userId);
      setUsers(users.filter(u => u.user_id !== userId));
      toast.success('User deleted successfully');
    } catch (error) {
      console.error('Failed to delete user:', error);
      toast.error('Failed to delete user');
    }
  };

  const handleClearNotifications = async () => {
    try {
      await notificationAPI.clearAll();
      setNotifications([]);
      toast.success('All notifications cleared');
    } catch (error) {
      console.error('Failed to clear notifications:', error);
      toast.error('Failed to clear notifications');
    }
  };

  const getServiceStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'up':
        return 'text-green-600';
      case 'degraded':
        return 'text-yellow-600';
      case 'down':
      case 'unhealthy':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getServiceStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'up':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'down':
      case 'unhealthy':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Server className="h-5 w-5 text-gray-600" />;
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatUptime = (seconds) => {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const tabs = [
    { id: 'overview', label: 'System Overview', icon: Activity },
    { id: 'services', label: 'Services', icon: Server },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'notifications', label: 'Notifications', icon: Settings }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
          <p className="text-gray-600">System administration and monitoring</p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <Shield className="h-4 w-4" />
            <span>Admin: {user?.username}</span>
          </div>
          <button
            onClick={loadAdminData}
            className="btn btn-secondary flex items-center space-x-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <div className="flex space-x-0">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-4 text-sm font-medium flex items-center space-x-2 border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-google-blue text-google-blue'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-google-blue"></div>
            </div>
          ) : (
            <>
              {/* System Overview */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
                      <div className="flex items-center">
                        <div className="p-3 rounded-full bg-blue-100">
                          <Database className="h-6 w-6 text-blue-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600">Total Files</p>
                          <p className="text-2xl font-bold text-gray-900">{systemStats.total_files || 0}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-green-50 p-6 rounded-lg border border-green-200">
                      <div className="flex items-center">
                        <div className="p-3 rounded-full bg-green-100">
                          <Users className="h-6 w-6 text-green-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600">Active Users</p>
                          <p className="text-2xl font-bold text-gray-900">{systemStats.active_users || 0}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
                      <div className="flex items-center">
                        <div className="p-3 rounded-full bg-yellow-100">
                          <Server className="h-6 w-6 text-yellow-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600">Services</p>
                          <p className="text-2xl font-bold text-gray-900">{services.length}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-purple-50 p-6 rounded-lg border border-purple-200">
                      <div className="flex items-center">
                        <div className="p-3 rounded-full bg-purple-100">
                          <Clock className="h-6 w-6 text-purple-600" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600">System Uptime</p>
                          <p className="text-2xl font-bold text-gray-900">{formatUptime(systemStats.uptime)}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-white border rounded-lg">
                      <div className="px-6 py-4 border-b">
                        <h3 className="text-lg font-medium">Service Status</h3>
                      </div>
                      <div className="p-6 space-y-4">
                        {services.slice(0, 5).map((service) => (
                          <div key={service.name} className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              {getServiceStatusIcon(service.status)}
                              <span className="font-medium">{service.name}</span>
                            </div>
                            <span className={`text-sm ${getServiceStatusColor(service.status)}`}>
                              {service.status || 'Unknown'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="bg-white border rounded-lg">
                      <div className="px-6 py-4 border-b">
                        <h3 className="text-lg font-medium">System Metrics</h3>
                      </div>
                      <div className="p-6 space-y-4">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Storage Usage</span>
                          <span className="font-medium">{systemStats.storage_used || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">API Requests (24h)</span>
                          <span className="font-medium">{systemStats.api_requests || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Error Rate</span>
                          <span className="font-medium">{systemStats.error_rate || '0%'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Last Restart</span>
                          <span className="font-medium">{systemStats.last_restart || 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Services Tab */}
              {activeTab === 'services' && (
                <div className="space-y-6">
                  <div className="grid gap-6">
                    {services.map((service) => (
                      <div key={service.name} className="bg-gray-50 rounded-lg p-6 border">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            {getServiceStatusIcon(service.status)}
                            <div>
                              <h3 className="text-lg font-medium">{service.name}</h3>
                              <p className="text-sm text-gray-600">{service.url || 'No URL configured'}</p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-4">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                              service.status === 'healthy' ? 'bg-green-100 text-green-800' :
                              service.status === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {service.status || 'Unknown'}
                            </span>
                            <button
                              onClick={() => handleRestartService(service.name)}
                              className="btn btn-secondary btn-sm"
                            >
                              Restart
                            </button>
                          </div>
                        </div>
                        
                        {service.metadata && (
                          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-gray-600">Version:</span>
                              <span className="ml-2 font-medium">{service.metadata.version || 'Unknown'}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Uptime:</span>
                              <span className="ml-2 font-medium">{formatUptime(service.metadata.uptime)}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Memory:</span>
                              <span className="ml-2 font-medium">{service.metadata.memory_usage || 'N/A'}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">CPU:</span>
                              <span className="ml-2 font-medium">{service.metadata.cpu_usage || 'N/A'}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Users Tab */}
              {activeTab === 'users' && (
                <div className="space-y-6">
                  <div className="bg-white rounded-lg border overflow-hidden">
                    <div className="px-6 py-4 border-b">
                      <h3 className="text-lg font-medium">User Management</h3>
                    </div>
                    
                    {users.length === 0 ? (
                      <div className="p-12 text-center">
                        <Users className="mx-auto h-12 w-12 text-gray-400" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No users found</h3>
                        <p className="mt-1 text-sm text-gray-500">User management endpoint may not be available</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200">
                            {users.map((userItem) => (
                              <tr key={userItem.user_id} className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <div className="flex items-center">
                                    <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center">
                                      <Users className="h-4 w-4 text-gray-500" />
                                    </div>
                                    <div className="ml-4">
                                      <div className="text-sm font-medium text-gray-900">{userItem.username}</div>
                                      <div className="text-sm text-gray-500">ID: {userItem.user_id}</div>
                                    </div>
                                  </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {userItem.email || 'N/A'}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                                    Active
                                  </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                  {userItem.created_at ? formatDate(userItem.created_at) : 'N/A'}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                  <button
                                    onClick={() => handleDeleteUser(userItem.user_id)}
                                    className="text-red-600 hover:text-red-800"
                                    disabled={userItem.user_id === user?.user_id}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Notifications Tab */}
              {activeTab === 'notifications' && (
                <div className="space-y-6">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-medium">System Notifications</h3>
                    {notifications.length > 0 && (
                      <button
                        onClick={handleClearNotifications}
                        className="btn btn-secondary btn-sm flex items-center space-x-2"
                      >
                        <Trash2 className="h-4 w-4" />
                        <span>Clear All</span>
                      </button>
                    )}
                  </div>

                  <div className="bg-white rounded-lg border">
                    {notifications.length === 0 ? (
                      <div className="p-12 text-center">
                        <Settings className="mx-auto h-12 w-12 text-gray-400" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No notifications</h3>
                        <p className="mt-1 text-sm text-gray-500">System notifications will appear here</p>
                      </div>
                    ) : (
                      <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                        {notifications.map((notification) => (
                          <div key={notification.notification_id} className="p-4">
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0">
                                <AlertCircle className="h-5 w-5 text-blue-500" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900">{notification.message}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                  {formatDate(notification.created_at)} • Type: {notification.type}
                                </p>
                                {notification.data && (
                                  <pre className="mt-2 text-xs bg-gray-100 p-2 rounded whitespace-pre-wrap">
                                    {JSON.stringify(notification.data, null, 2)}
                                  </pre>
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
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;