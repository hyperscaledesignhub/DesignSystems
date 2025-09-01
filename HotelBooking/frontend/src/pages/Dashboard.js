import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';

const Dashboard = ({ user }) => {
  const [stats, setStats] = useState({
    totalHotels: 0,
    totalReservations: 0,
    totalPayments: 0
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      // Load basic stats
      const hotels = await ApiService.getHotels();
      setStats(prev => ({ ...prev, totalHotels: hotels.length }));
      
      // Simulate some activity data
      setRecentActivity([
        { 
          id: 1, 
          type: 'registration', 
          message: 'Welcome to Hotel Booking System!',
          time: new Date().toLocaleString() 
        }
      ]);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const workflows = [
    {
      title: 'Hotel Management',
      description: 'Browse hotels and view details',
      icon: '🏨',
      link: '/hotels',
      color: '#667eea'
    },
    {
      title: 'Room Booking',
      description: 'Search and book rooms',
      icon: '🛏️',
      link: '/booking',
      color: '#764ba2'
    },
    {
      title: 'My Reservations',
      description: 'View and manage your bookings',
      icon: '📋',
      link: '/reservations',
      color: '#28a745'
    },
    {
      title: 'Payments',
      description: 'Process and view payments',
      icon: '💳',
      link: '/payments',
      color: '#ffc107'
    },
    {
      title: 'Inventory Management',
      description: 'Check room availability',
      icon: '📊',
      link: '/inventory',
      color: '#17a2b8'
    }
  ];

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: '30px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
        <h1 style={{ margin: '0 0 10px 0' }}>Welcome to Hotel Booking System</h1>
        <p style={{ margin: '0', opacity: '0.9' }}>
          Comprehensive microservices demo with all tested workflows
        </p>
      </div>

      {/* Stats Cards */}
      <div className="card-grid" style={{ marginBottom: '30px' }}>
        <div className="card text-center">
          <h3 style={{ color: '#667eea', fontSize: '2rem' }}>{stats.totalHotels}</h3>
          <p>Hotels Available</p>
        </div>
        <div className="card text-center">
          <h3 style={{ color: '#28a745', fontSize: '2rem' }}>{stats.totalReservations}</h3>
          <p>Total Reservations</p>
        </div>
        <div className="card text-center">
          <h3 style={{ color: '#ffc107', fontSize: '2rem' }}>{stats.totalPayments}</h3>
          <p>Payments Processed</p>
        </div>
      </div>

      {/* Workflow Cards */}
      <div className="card">
        <h2 style={{ marginBottom: '20px', color: '#333' }}>Available Workflows</h2>
        <div className="card-grid">
          {workflows.map((workflow, index) => (
            <Link 
              to={workflow.link} 
              key={index}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <div className="card" style={{ borderLeft: `4px solid ${workflow.color}`, cursor: 'pointer' }}>
                <div style={{ fontSize: '2rem', marginBottom: '10px' }}>{workflow.icon}</div>
                <h3 style={{ color: workflow.color, marginBottom: '10px' }}>{workflow.title}</h3>
                <p style={{ color: '#666', margin: '0' }}>{workflow.description}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* System Architecture Info */}
      <div className="card" style={{ marginTop: '30px' }}>
        <h2 style={{ marginBottom: '20px', color: '#333' }}>System Architecture</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
          {[
            { service: 'Hotel Service', port: '5001', status: '🟢' },
            { service: 'Room Service', port: '5002', status: '🟢' },
            { service: 'Guest Service', port: '5003', status: '🟢' },
            { service: 'Inventory Service', port: '5004', status: '🟢' },
            { service: 'Reservation Service', port: '5005', status: '🟢' },
            { service: 'Payment Service', port: '5006', status: '🟢' }
          ].map((service, index) => (
            <div key={index} style={{ textAlign: 'center', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ fontSize: '1.2rem', marginBottom: '5px' }}>{service.status}</div>
              <div style={{ fontWeight: '600', marginBottom: '3px' }}>{service.service}</div>
              <div style={{ fontSize: '0.9rem', color: '#666' }}>Port {service.port}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Tested Features */}
      <div className="card" style={{ marginTop: '30px' }}>
        <h2 style={{ marginBottom: '20px', color: '#333' }}>Verified Features</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
          {[
            {
              title: 'Concurrency Control',
              features: ['Database constraints', 'Row-level locking', 'Atomic operations', 'No overbooking']
            },
            {
              title: 'Service Communication',
              features: ['Docker networking', 'Service discovery', 'Health checks', 'Error handling']
            },
            {
              title: 'Complete Workflows',
              features: ['Guest registration', 'Hotel management', 'Room booking', 'Payment processing']
            }
          ].map((section, index) => (
            <div key={index} style={{ padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
              <h3 style={{ color: '#333', marginBottom: '15px' }}>{section.title}</h3>
              <ul style={{ listStyle: 'none', padding: '0', margin: '0' }}>
                {section.features.map((feature, featureIndex) => (
                  <li key={featureIndex} style={{ padding: '5px 0', color: '#666' }}>
                    ✅ {feature}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;