import axios from 'axios';

const API_BASE_URL = 'http://localhost:8370';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (userData) => api.post('/api/v1/auth/register', userData),
  login: (credentials) => api.post('/api/v1/auth/login', credentials),
  validate: () => api.get('/api/v1/auth/validate'),
};

export const userAPI = {
  getUser: (userId) => api.get(`/api/v1/users/${userId}`),
  addFriend: (userId, friendId) => api.post(`/api/v1/users/${userId}/friends/${friendId}`),
  removeFriend: (userId, friendId) => api.delete(`/api/v1/users/${userId}/friends/${friendId}`),
};

export const postAPI = {
  createPost: (postData) => api.post('/api/v1/posts', postData),
  getPost: (postId) => api.get(`/api/v1/posts/${postId}`),
  getUserPosts: (userId, params = {}) => api.get(`/api/v1/users/${userId}/posts`, { params }),
  deletePost: (postId) => api.delete(`/api/v1/posts/${postId}`),
};

export const graphAPI = {
  getFriends: (userId) => api.get(`/api/v1/graph/users/${userId}/friends`),
  getFriendSuggestions: (userId) => api.get(`/api/v1/graph/users/${userId}/suggestions`),
};

export const feedAPI = {
  getUserFeed: (userId, params = {}) => api.get(`/api/v1/feed/${userId}`, { params }),
  refreshFeed: (userId) => api.get(`/api/v1/feed/${userId}/refresh`),
};

export const notificationAPI = {
  getUserNotifications: (userId, params = {}) => api.get(`/api/v1/notifications/${userId}`, { params }),
  markAsRead: (userId, notificationId) => api.patch(`/api/v1/notifications/${userId}/${notificationId}/read`),
  markAllAsRead: (userId) => api.patch(`/api/v1/notifications/${userId}/read-all`),
};

export default api;