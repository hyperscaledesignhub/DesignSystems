import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI, setApiToken } from '../services/api';
import wsService from '../services/websocket';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
      setApiToken(savedToken); // Set token in API on initial load
      
      // Connect to WebSocket
      const userData = JSON.parse(savedUser);
      wsService.connect(userData.user_id, savedToken);
    }
    setLoading(false);
  }, []);

  const login = async (credentials) => {
    try {
      const response = await authAPI.login(credentials);
      const { access_token, token_type } = response.data;
      
      // Store token and set it in API immediately
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setApiToken(access_token); // Set token in axios defaults immediately
      
      // Get user profile - now the token is available in API
      const profileResponse = await authAPI.getProfile();
      const userData = profileResponse.data;
      
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Connect to WebSocket
      wsService.connect(userData.user_id, access_token);
      
      toast.success('Successfully logged in!');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const register = async (userData) => {
    try {
      const response = await authAPI.register(userData);
      toast.success('Account created successfully! Please log in.');
      return { success: true, data: response.data };
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration failed';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setToken(null);
      setApiToken(null); // Clear token from API
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // Disconnect WebSocket
      wsService.disconnect();
      
      toast.success('Successfully logged out!');
    }
  };

  const updateProfile = async (profileData) => {
    try {
      const response = await authAPI.updateProfile(profileData);
      const updatedUser = response.data;
      
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      toast.success('Profile updated successfully!');
      return { success: true, data: updatedUser };
    } catch (error) {
      const message = error.response?.data?.detail || 'Profile update failed';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    updateProfile,
    isAuthenticated: !!user && !!token,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export default AuthContext;