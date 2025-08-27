import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { TrendingUp, Mail, Lock, User } from 'lucide-react';
import './Login.css';

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    if (isLogin) {
      await login(formData.username, formData.password);
    } else {
      const success = await register(formData.email, formData.username, formData.password);
      if (success) {
        setIsLogin(true);
        setFormData({ ...formData, password: '' });
      }
    }
    
    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const loadDemoCredentials = (role) => {
    if (role === 'buyer') {
      setFormData({
        email: 'demo_buyer@test.com',
        username: 'demo_buyer',
        password: 'demopass123'
      });
    } else {
      setFormData({
        email: 'demo_seller@test.com',
        username: 'demo_seller',
        password: 'demopass123'
      });
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <TrendingUp size={40} className="login-logo" />
          <h1>Stock Exchange Platform</h1>
          <p>Advanced Trading System Demonstration</p>
        </div>

        <div className="login-tabs">
          <button
            className={`login-tab ${isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(true)}
          >
            Login
          </button>
          <button
            className={`login-tab ${!isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(false)}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {!isLogin && (
            <div className="form-field">
              <Mail size={18} className="field-icon" />
              <input
                type="email"
                name="email"
                placeholder="Email Address"
                value={formData.email}
                onChange={handleChange}
                required={!isLogin}
              />
            </div>
          )}

          <div className="form-field">
            <User size={18} className="field-icon" />
            <input
              type="text"
              name="username"
              placeholder="Username"
              value={formData.username}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-field">
            <Lock size={18} className="field-icon" />
            <input
              type="password"
              name="password"
              placeholder="Password"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>

          <button type="submit" className="btn-submit" disabled={loading}>
            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
          </button>
        </form>

        {isLogin && (
          <div className="demo-credentials">
            <p>Quick Demo Access:</p>
            <div className="demo-buttons">
              <button onClick={() => loadDemoCredentials('buyer')} className="demo-btn">
                Load Buyer Demo
              </button>
              <button onClick={() => loadDemoCredentials('seller')} className="demo-btn">
                Load Seller Demo
              </button>
            </div>
          </div>
        )}

        <div className="login-features">
          <h3>Platform Features:</h3>
          <ul>
            <li>Real-time Order Matching Engine</li>
            <li>Advanced Risk Management</li>
            <li>Live Market Data & Analytics</li>
            <li>Portfolio Management</li>
            <li>WebSocket Real-time Updates</li>
            <li>Comprehensive Reporting</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Login;