import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ApiService from '../services/api';

const Hotels = () => {
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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

  const viewRooms = (hotelId, hotelName) => {
    navigate(`/rooms/${hotelId}?hotel=${encodeURIComponent(hotelName)}`);
  };

  const bookRoom = (hotelId, hotelName) => {
    navigate(`/booking?hotel=${hotelId}&hotelName=${encodeURIComponent(hotelName)}`);
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading hotels...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: '30px' }}>
        <div style={{ marginBottom: '20px' }}>
          <h1 style={{ margin: '0', color: '#333' }}>Browse Hotels</h1>
          <p style={{ color: '#666', margin: '5px 0 0 0' }}>
            🏨 Discover and book amazing hotels for your next stay
          </p>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}


        <div className="alert alert-info">
          <strong>Hotel Booking:</strong> 
          Browse available hotels, view room details, and make reservations. 
          Click "View Rooms" to see available room types or "Book Now" to start your reservation.
        </div>
      </div>

      {hotels.length === 0 ? (
        <div className="card text-center">
          <h3>No Hotels Available</h3>
          <p>No hotels are currently available for booking. Please check back later!</p>
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
              
              <div style={{ marginBottom: '15px' }}>
                <p style={{ margin: '5px 0', color: '#666' }}>
                  📍 {hotel.address}
                </p>
                <p style={{ margin: '5px 0', color: '#666' }}>
                  🌍 {hotel.location}
                </p>
                <p style={{ margin: '5px 0', color: '#666', fontSize: '0.9rem' }}>
                  Created: {ApiService.formatDateTime(hotel.created_at)}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => viewRooms(hotel.hotel_id)}
                  style={{ flex: 1 }}
                >
                  View Rooms
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => navigate(`/booking?hotel=${hotel.hotel_id}`)}
                >
                  Book Now
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Workflow Information */}
      <div className="card" style={{ marginTop: '30px' }}>
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Booking Features</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#28a745' }}>🏨 Browse Hotels</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Explore all available hotels with detailed information
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#28a745' }}>🛏️ View Room Types</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Check room availability, pricing, and amenities
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#28a745' }}>📅 Make Reservations</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Book your perfect room for your desired dates
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Hotels;