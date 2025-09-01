import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ApiService from '../services/api';

const Rooms = () => {
  const { hotelId } = useParams();
  const navigate = useNavigate();
  const [hotel, setHotel] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newRoom, setNewRoom] = useState({
    name: '',
    max_occupancy: 2,
    base_price: 100
  });

  useEffect(() => {
    if (hotelId) {
      loadHotelAndRooms();
    }
  }, [hotelId]);

  const loadHotelAndRooms = async () => {
    try {
      setError('');
      // Load hotel details
      const hotelData = await ApiService.getHotel(hotelId);
      setHotel(hotelData);
      
      // Load room types
      const roomsData = await ApiService.getRoomTypes(hotelId);
      setRooms(roomsData);
    } catch (err) {
      setError('Failed to load hotel/rooms: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    try {
      const roomData = {
        ...newRoom,
        hotel_id: hotelId
      };
      const createdRoom = await ApiService.createRoomType(hotelId, roomData);
      setRooms([...rooms, createdRoom]);
      setNewRoom({ name: '', max_occupancy: 2, base_price: 100 });
      setShowCreateForm(false);
    } catch (err) {
      setError('Failed to create room type: ' + err.message);
    }
  };

  const bookRoom = (roomTypeId) => {
    navigate(`/booking?hotel=${hotelId}&room=${roomTypeId}`);
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading hotel and rooms...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: '30px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <button
              className="btn btn-secondary"
              onClick={() => navigate('/hotels')}
              style={{ marginBottom: '10px' }}
            >
              ← Back to Hotels
            </button>
            <h1 style={{ margin: '0', color: '#333' }}>
              {hotel ? `${hotel.name} - Room Types` : 'Room Types'}
            </h1>
            {hotel && (
              <p style={{ color: '#666', margin: '5px 0' }}>
                📍 {hotel.address} • 🌍 {hotel.location}
              </p>
            )}
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Cancel' : 'Add Room Type'}
          </button>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        {showCreateForm && (
          <form onSubmit={handleCreateRoom} style={{ marginBottom: '30px', padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h3>Create New Room Type</h3>
            <div className="form-group">
              <label className="form-label">Room Name</label>
              <input
                type="text"
                className="form-input"
                value={newRoom.name}
                onChange={(e) => setNewRoom({ ...newRoom, name: e.target.value })}
                placeholder="e.g., Standard Double Room"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Maximum Occupancy</label>
              <input
                type="number"
                className="form-input"
                value={newRoom.max_occupancy}
                onChange={(e) => setNewRoom({ ...newRoom, max_occupancy: parseInt(e.target.value) })}
                min="1"
                max="10"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Base Price (USD)</label>
              <input
                type="number"
                className="form-input"
                value={newRoom.base_price}
                onChange={(e) => setNewRoom({ ...newRoom, base_price: parseFloat(e.target.value) })}
                min="10"
                step="0.01"
                required
              />
            </div>
            <button type="submit" className="btn btn-success">
              Create Room Type
            </button>
          </form>
        )}

        <div className="alert alert-info">
          <strong>Room Management Workflow:</strong> 
          Browse room types for a hotel, view specifications (occupancy, price), and create new room types.
        </div>
      </div>

      {rooms.length === 0 ? (
        <div className="card text-center">
          <h3>No Room Types Available</h3>
          <p>Create room types for this hotel to allow bookings!</p>
        </div>
      ) : (
        <div className="card-grid">
          {rooms.map((room) => (
            <div key={room.room_type_id} className="card">
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                <span style={{ fontSize: '2rem', marginRight: '15px' }}>🛏️</span>
                <div>
                  <h3 style={{ margin: '0 0 5px 0', color: '#333' }}>
                    {room.name}
                  </h3>
                  <p style={{ margin: '0', fontSize: '0.9rem', color: '#666' }}>
                    ID: {room.room_type_id}
                  </p>
                </div>
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span style={{ color: '#666' }}>Max Occupancy:</span>
                  <span style={{ fontWeight: '600' }}>
                    👥 {room.max_occupancy} guests
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span style={{ color: '#666' }}>Base Price:</span>
                  <span style={{ fontWeight: '600', color: '#28a745' }}>
                    {ApiService.formatCurrency(room.base_price)} / night
                  </span>
                </div>
                <p style={{ margin: '10px 0 0 0', color: '#666', fontSize: '0.9rem' }}>
                  Created: {ApiService.formatDateTime(room.created_at)}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn btn-success"
                  onClick={() => bookRoom(room.room_type_id)}
                  style={{ flex: 1 }}
                >
                  Book This Room
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => navigate(`/inventory?room=${room.room_type_id}`)}
                >
                  Check Availability
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Room Management Features */}
      <div className="card" style={{ marginTop: '30px' }}>
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Room Management Features</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#764ba2' }}>✅ Browse Room Types</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              View all available room types for the selected hotel
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#764ba2' }}>✅ View Room Details</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Get room specifications (occupancy, price, amenities)
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#764ba2' }}>✅ Create Room Types</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Add new room types with custom pricing and occupancy
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Rooms;