import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ApiService from '../services/api';

const AdminHotels = () => {
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newHotel, setNewHotel] = useState({
    name: '',
    address: '',
    location: ''
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadHotels();
  }, []);

  const loadHotels = async () => {
    try {
      setError('');
      const data = await ApiService.getHotels();
      setHotels(data);
    } catch (err) {
      setError('Failed to load hotels: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateHotel = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const createdHotel = await ApiService.createHotel(newHotel);
      setHotels([...hotels, createdHotel]);
      setNewHotel({ name: '', address: '', location: '' });
      setShowCreateForm(false);
      setSuccess('Hotel created successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to create hotel: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const manageRooms = (hotelId, hotelName) => {
    navigate(`/rooms/${hotelId}?admin=true&hotel=${encodeURIComponent(hotelName)}`);
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading hotel management...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: '30px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h1 style={{ margin: '0', color: '#333' }}>Hotel Management</h1>
            <p style={{ color: '#666', margin: '5px 0 0 0' }}>
              🔧 Admin Panel - Create and manage hotels in the system
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Cancel' : '+ Add New Hotel'}
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {showCreateForm && (
          <form onSubmit={handleCreateHotel} style={{ marginBottom: '30px', padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h3>Create New Hotel</h3>
            <div className="form-group">
              <label className="form-label">Hotel Name</label>
              <input
                type="text"
                className="form-input"
                value={newHotel.name}
                onChange={(e) => setNewHotel({ ...newHotel, name: e.target.value })}
                placeholder="e.g., Grand Plaza Hotel"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Address</label>
              <input
                type="text"
                className="form-input"
                value={newHotel.address}
                onChange={(e) => setNewHotel({ ...newHotel, address: e.target.value })}
                placeholder="e.g., 123 Main Street"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Location</label>
              <input
                type="text"
                className="form-input"
                value={newHotel.location}
                onChange={(e) => setNewHotel({ ...newHotel, location: e.target.value })}
                placeholder="e.g., New York, NY"
                required
              />
            </div>
            <button type="submit" className="btn btn-success" disabled={loading}>
              {loading ? 'Creating...' : 'Create Hotel'}
            </button>
          </form>
        )}

        <div className="alert alert-info">
          <strong>Admin Hotel Management:</strong> 
          Create new hotels, manage room types, and configure inventory settings. Regular users will see these hotels in the booking system.
        </div>
      </div>

      {hotels.length === 0 ? (
        <div className="card text-center">
          <h3>No Hotels in System</h3>
          <p>Create your first hotel to start accepting bookings!</p>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateForm(true)}
          >
            Create First Hotel
          </button>
        </div>
      ) : (
        <div className="card-grid">
          {hotels.map((hotel) => (
            <div key={hotel.hotel_id} className="card">
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                <span style={{ fontSize: '2rem', marginRight: '15px' }}>🏨</span>
                <div>
                  <h3 style={{ margin: '0 0 5px 0', color: '#333' }}>
                    {hotel.name}
                  </h3>
                  <p style={{ margin: '0', fontSize: '0.9rem', color: '#666' }}>
                    ID: {hotel.hotel_id}
                  </p>
                </div>
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <div style={{ marginBottom: '10px' }}>
                  <strong>📍 Address:</strong><br/>
                  <span style={{ color: '#666' }}>{hotel.address}</span>
                </div>
                <div style={{ marginBottom: '10px' }}>
                  <strong>🌍 Location:</strong><br/>
                  <span style={{ color: '#666' }}>{hotel.location}</span>
                </div>
                <div style={{ fontSize: '0.9rem', color: '#666' }}>
                  Created: {ApiService.formatDateTime(hotel.created_at)}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => manageRooms(hotel.hotel_id, hotel.name)}
                  style={{ flex: 1 }}
                >
                  Manage Rooms
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => navigate(`/inventory?hotel=${hotel.hotel_id}`)}
                >
                  Inventory
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Management Features */}
      <div className="card" style={{ marginTop: '30px' }}>
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Hotel Management Features</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#dc3545' }}>🏨 Create Hotels</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Add new hotels to the booking system with location details
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#dc3545' }}>🛏️ Room Management</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Configure room types, pricing, and occupancy limits
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#dc3545' }}>📦 Inventory Control</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Set availability, manage reservations, and handle overbooking
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminHotels;