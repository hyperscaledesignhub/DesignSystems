import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';

const Login = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Since we don't have authentication, we'll simulate login
      // In a real app, this would validate credentials
      
      // For demo purposes, try to find user by email (simulate login)
      // We'll create a mock user for demo
      const mockUser = {
        id: 'demo-user-' + Date.now(),
        email: formData.email,
        first_name: formData.email.split('@')[0],
        last_name: 'Demo',
        phone: '+1-555-DEMO',
        created_at: new Date().toISOString()
      };

      // In real app, you'd validate against a user service
      if (formData.email && formData.password) {
        onLogin(mockUser);
      } else {
        throw new Error('Please enter both email and password');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2 className="form-title">Login</h2>
      
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email" className="form-label">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className="form-input"
            placeholder="Enter your email"
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="password" className="form-label">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className="form-input"
            placeholder="Enter your password"
            required
          />
        </div>
        
        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
      
      <p style={{ marginTop: '20px', color: '#666' }}>
        Don't have an account?{' '}
        <Link to="/register" style={{ color: '#667eea', textDecoration: 'none' }}>
          Register here
        </Link>
      </p>
      
      <div className="alert alert-info" style={{ marginTop: '20px', fontSize: '14px' }}>
        <strong>Demo Mode:</strong> Enter any email and password to login. 
        The system will create a demo user for you.
      </div>
    </div>
  );
};

export default Login;