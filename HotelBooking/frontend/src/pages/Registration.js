import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';

const Registration = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

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
    setSuccess('');

    try {
      // Validate passwords match
      if (formData.password !== formData.confirmPassword) {
        throw new Error('Passwords do not match');
      }

      // Register with guest service
      const guestData = {
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        phone: formData.phone || null
      };

      const newUser = await ApiService.registerGuest(guestData);
      
      setSuccess('Account created successfully! Logging you in...');
      
      // Auto-login after successful registration
      setTimeout(() => {
        onLogin(newUser);
      }, 1500);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2 className="form-title">Register</h2>
      
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}
      
      {success && (
        <div className="alert alert-success">
          {success}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="first_name" className="form-label">First Name</label>
          <input
            type="text"
            id="first_name"
            name="first_name"
            value={formData.first_name}
            onChange={handleChange}
            className="form-input"
            placeholder="Enter your first name"
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="last_name" className="form-label">Last Name</label>
          <input
            type="text"
            id="last_name"
            name="last_name"
            value={formData.last_name}
            onChange={handleChange}
            className="form-input"
            placeholder="Enter your last name"
            required
          />
        </div>
        
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
          <label htmlFor="phone" className="form-label">Phone (Optional)</label>
          <input
            type="tel"
            id="phone"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            className="form-input"
            placeholder="Enter your phone number"
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
            placeholder="Create a password"
            required
            minLength="6"
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="confirmPassword" className="form-label">Confirm Password</label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            className="form-input"
            placeholder="Confirm your password"
            required
            minLength="6"
          />
        </div>
        
        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Creating Account...' : 'Register'}
        </button>
      </form>
      
      <p style={{ marginTop: '20px', color: '#666' }}>
        Already have an account?{' '}
        <Link to="/login" style={{ color: '#667eea', textDecoration: 'none' }}>
          Login here
        </Link>
      </p>
    </div>
  );
};

export default Registration;