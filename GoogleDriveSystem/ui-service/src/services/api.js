import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:9010' 
  : window.location.origin;

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for file uploads
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      toast.error('Session expired. Please login again.');
    } else if (error.response?.status === 429) {
      toast.error('Rate limit exceeded. Please wait a moment.');
    } else if (error.message.includes('timeout')) {
      toast.error('Request timed out. Please try again.');
    }
    return Promise.reject(error);
  }
);

// Function to manually set token for API
export const setApiToken = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// Auth API
export const authAPI = {
  register: (userData) => api.post('/auth/register', userData),
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  getProfile: () => api.get('/auth/profile'),
  updateProfile: (userData) => api.put('/auth/profile', userData),
  lookupUser: (emailOrUserId) => api.get(`/auth/lookup?q=${encodeURIComponent(emailOrUserId)}`),
};

// File API
export const fileAPI = {
  upload: (formData, onProgress) => api.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
  }),
  list: (path = '/') => api.get('/files'),
  download: (fileId) => api.get(`/files/download/${fileId}`, { responseType: 'blob' }),
  delete: (fileId) => api.delete(`/files/${fileId}`),
  rename: (fileId, newName) => api.put(`/files/${fileId}?filename=${encodeURIComponent(newName)}`),
  share: (fileId, shareData) => api.post(`/files/${fileId}/share`, shareData),
  getSharedFiles: () => api.get('/files/shared'),
};

// Metadata API
export const metadataAPI = {
  create: (metadata) => api.post('/metadata/metadata', metadata),
  get: (fileId) => api.get(`/metadata/metadata/${fileId}`),
  update: (fileId, metadata) => api.put(`/metadata/metadata/${fileId}`, metadata),
  delete: (fileId) => api.delete(`/metadata/metadata/${fileId}`),
  search: (query) => api.get(`/metadata/search?query=${encodeURIComponent(query)}`),
  createFolder: (folderData) => api.post('/metadata/folders', folderData),
  getFolders: (parentPath = '/') => api.get(`/metadata/folders?parent_path=${encodeURIComponent(parentPath)}`),
  getVersions: (fileId) => api.get(`/metadata/metadata/${fileId}/versions`),
};

// Block API
export const blockAPI = {
  upload: (formData, onProgress) => api.post('/blocks/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
  }),
  download: (fileId) => api.get(`/blocks/download/${fileId}`, { responseType: 'blob' }),
  getBlocks: (fileId) => api.get(`/blocks/files/${fileId}/blocks`),
  getStats: () => api.get('/blocks/stats'),
};

// Notification API
export const notificationAPI = {
  send: (notification) => api.post('/notifications/notify', notification),
  getHistory: (userId) => api.get(`/notifications/notifications/${userId}`),
  markAsRead: (notificationId) => api.put(`/notifications/notifications/${notificationId}/read`),
  updateStatus: (userId, status) => api.put(`/notifications/status/${userId}`, { status }),
  getStatus: (userId) => api.get(`/notifications/status/${userId}`),
  getOnlineUsers: () => api.get('/notifications/online-users'),
  broadcast: (message) => api.post(`/notifications/broadcast?message=${encodeURIComponent(message)}`),
};

// Gateway API
export const gatewayAPI = {
  getHealth: () => api.get('/health'),
  getStats: () => api.get('/gateway/stats'),
  getServices: () => api.get('/gateway/services'),
};

export default api;