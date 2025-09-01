import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';

const Inventory = () => {
  const [searchParams] = useSearchParams();
  const [hotels, setHotels] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [inventoryData, setInventoryData] = useState({
    hotel_id: '',
    room_type_id: searchParams.get('room') || '',
    check_in: '',
    check_out: '',
    num_rooms: 1
  });
  
  const [availability, setAvailability] = useState(null);

  useEffect(() => {
    loadHotels();
  }, []);

  useEffect(() => {
    if (inventoryData.hotel_id) {
      loadRooms(inventoryData.hotel_id);
    }
  }, [inventoryData.hotel_id]);

  const loadHotels = async () => {
    try {
      const data = await ApiService.getHotels();
      setHotels(data);
      if (data.length > 0 && !inventoryData.hotel_id) {
        setInventoryData(prev => ({ ...prev, hotel_id: data[0].hotel_id }));
      }
    } catch (err) {
      setError('Failed to load hotels: ' + err.message);
    }
  };

  const loadRooms = async (hotelId) => {
    try {
      const data = await ApiService.getRoomTypes(hotelId);
      setRooms(data);
    } catch (err) {
      setError('Failed to load rooms: ' + err.message);
    }
  };

  const checkAvailability = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setAvailability(null);

    try {
      const result = await ApiService.checkAvailability(
        inventoryData.room_type_id,
        inventoryData.check_in,
        inventoryData.check_out,
        inventoryData.num_rooms
      );
      setAvailability(result);
    } catch (err) {
      setError('Failed to check availability: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const reserveRooms = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await ApiService.reserveRooms(
        inventoryData.hotel_id,
        inventoryData.room_type_id,
        inventoryData.check_in,
        inventoryData.check_out,
        inventoryData.num_rooms
      );
      setSuccess(`Successfully reserved ${inventoryData.num_rooms} rooms!`);
      
      // Refresh availability
      setTimeout(() => {
        checkAvailability({ preventDefault: () => {} });
      }, 1000);
    } catch (err) {
      setError('Failed to reserve rooms: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const releaseRooms = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await ApiService.releaseRooms(
        inventoryData.hotel_id,
        inventoryData.room_type_id,
        inventoryData.check_in,
        inventoryData.check_out,
        inventoryData.num_rooms
      );
      setSuccess(`Successfully released ${inventoryData.num_rooms} rooms!`);
      
      // Refresh availability
      setTimeout(() => {
        checkAvailability({ preventDefault: () => {} });
      }, 1000);
    } catch (err) {
      setError('Failed to release rooms: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectedHotel = hotels.find(h => h.hotel_id === inventoryData.hotel_id);
  const selectedRoom = rooms.find(r => r.room_type_id === inventoryData.room_type_id);

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: '30px' }}>
        <h1 style={{ color: '#333', marginBottom: '20px' }}>Inventory Management</h1>
        
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        <div className="alert alert-info">
          <strong>Inventory Management Workflow:</strong> 
          Check real-time room availability, reserve inventory during booking, and release inventory on cancellation.
        </div>
      </div>

      {/* Availability Check Form */}
      <div className="card" style={{ marginBottom: '30px' }}>
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Check Room Availability</h2>
        
        <form onSubmit={checkAvailability}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            <div className="form-group">
              <label className="form-label">Hotel</label>
              <select
                className="form-input"
                value={inventoryData.hotel_id}
                onChange={(e) => setInventoryData(prev => ({ ...prev, hotel_id: e.target.value }))}
                required
              >
                <option value="">Select a hotel</option>
                {hotels.map(hotel => (
                  <option key={hotel.hotel_id} value={hotel.hotel_id}>
                    {hotel.name} - {hotel.location}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Room Type</label>
              <select
                className="form-input"
                value={inventoryData.room_type_id}
                onChange={(e) => setInventoryData(prev => ({ ...prev, room_type_id: e.target.value }))}
                required
              >
                <option value="">Select a room type</option>
                {rooms.map(room => (
                  <option key={room.room_type_id} value={room.room_type_id}>
                    {room.name} - {ApiService.formatCurrency(room.base_price)}/night
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            <div className="form-group">
              <label className="form-label">Check-in Date</label>
              <input
                type="date"
                className="form-input"
                value={inventoryData.check_in}
                onChange={(e) => setInventoryData(prev => ({ ...prev, check_in: e.target.value }))}
                min={new Date().toISOString().split('T')[0]}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Check-out Date</label>
              <input
                type="date"
                className="form-input"
                value={inventoryData.check_out}
                onChange={(e) => setInventoryData(prev => ({ ...prev, check_out: e.target.value }))}
                min={inventoryData.check_in}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Number of Rooms</label>
              <input
                type="number"
                className="form-input"
                value={inventoryData.num_rooms}
                onChange={(e) => setInventoryData(prev => ({ ...prev, num_rooms: parseInt(e.target.value) }))}
                min="1"
                max="20"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%' }}
          >
            {loading ? 'Checking Availability...' : 'Check Availability'}
          </button>
        </form>
      </div>

      {/* Availability Results */}
      {availability && (
        <div className="card" style={{ marginBottom: '30px' }}>
          <h2 style={{ color: '#333', marginBottom: '20px' }}>Availability Results</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
            <div>
              <h3 style={{ color: '#667eea', marginBottom: '15px' }}>Selected Details</h3>
              <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px' }}>
                <p><strong>Hotel:</strong> {selectedHotel?.name}</p>
                <p><strong>Room Type:</strong> {selectedRoom?.name}</p>
                <p><strong>Check-in:</strong> {inventoryData.check_in}</p>
                <p><strong>Check-out:</strong> {inventoryData.check_out}</p>
                <p><strong>Requested Rooms:</strong> {inventoryData.num_rooms}</p>
              </div>
            </div>

            <div>
              <h3 style={{ color: '#667eea', marginBottom: '15px' }}>Availability Status</h3>
              <div style={{ 
                background: availability.available_rooms >= inventoryData.num_rooms ? '#d4edda' : '#f8d7da',
                border: `1px solid ${availability.available_rooms >= inventoryData.num_rooms ? '#c3e6cb' : '#f5c6cb'}`,
                padding: '20px', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', marginBottom: '10px' }}>
                  {availability.available_rooms >= inventoryData.num_rooms ? '✅' : '❌'}
                </div>
                <h3 style={{ 
                  color: availability.available_rooms >= inventoryData.num_rooms ? '#155724' : '#721c24',
                  marginBottom: '10px'
                }}>
                  {availability.available_rooms} Rooms Available
                </h3>
                <p style={{ 
                  color: availability.available_rooms >= inventoryData.num_rooms ? '#155724' : '#721c24',
                  margin: '0'
                }}>
                  {availability.available_rooms >= inventoryData.num_rooms 
                    ? 'Sufficient inventory for your request'
                    : `Only ${availability.available_rooms} rooms available`
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Inventory Management Actions */}
          <div style={{ marginTop: '30px' }}>
            <h3 style={{ color: '#667eea', marginBottom: '15px' }}>Inventory Actions</h3>
            <div style={{ display: 'flex', gap: '15px' }}>
              <button
                className="btn btn-warning"
                onClick={reserveRooms}
                disabled={loading}
                style={{ flex: 1 }}
              >
                {loading ? 'Reserving...' : `Reserve ${inventoryData.num_rooms} Room${inventoryData.num_rooms > 1 ? 's' : ''}`}
              </button>
              <button
                className="btn btn-success"
                onClick={releaseRooms}
                disabled={loading}
                style={{ flex: 1 }}
              >
                {loading ? 'Releasing...' : `Release ${inventoryData.num_rooms} Room${inventoryData.num_rooms > 1 ? 's' : ''}`}
              </button>
            </div>
            <p style={{ color: '#666', fontSize: '0.9rem', marginTop: '10px', textAlign: 'center' }}>
              These actions simulate the booking and cancellation process
            </p>
          </div>
        </div>
      )}

      {/* Concurrency Control Demo */}
      <div className="card">
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Concurrency Control Features</h2>
        
        <div style={{ marginBottom: '20px' }}>
          <p style={{ color: '#666', marginBottom: '15px' }}>
            The inventory system uses database-level concurrency control to prevent overbooking:
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#17a2b8', marginBottom: '10px' }}>✅ Database Constraints</h4>
            <code style={{ background: '#e9ecef', padding: '10px', borderRadius: '4px', display: 'block', fontSize: '0.9rem' }}>
              CHECK (total_reserved ≤ total_inventory)
            </code>
            <p style={{ margin: '10px 0 0 0', color: '#666', fontSize: '0.9rem' }}>
              Prevents overbooking at the database level
            </p>
          </div>

          <div style={{ padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#17a2b8', marginBottom: '10px' }}>✅ Atomic Updates</h4>
            <code style={{ background: '#e9ecef', padding: '10px', borderRadius: '4px', display: 'block', fontSize: '0.9rem' }}>
              WHERE (total_reserved + N) ≤ total_inventory
            </code>
            <p style={{ margin: '10px 0 0 0', color: '#666', fontSize: '0.9rem' }}>
              Only updates if sufficient inventory available
            </p>
          </div>

          <div style={{ padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#17a2b8', marginBottom: '10px' }}>✅ Row-Level Locking</h4>
            <code style={{ background: '#e9ecef', padding: '10px', borderRadius: '4px', display: 'block', fontSize: '0.9rem' }}>
              UPDATE ... RETURNING
            </code>
            <p style={{ margin: '10px 0 0 0', color: '#666', fontSize: '0.9rem' }}>
              PostgreSQL handles concurrent access safely
            </p>
          </div>
        </div>

        <div style={{ marginTop: '30px', padding: '20px', background: '#fff3cd', borderRadius: '8px', border: '1px solid #ffeaa7' }}>
          <h4 style={{ color: '#856404', marginBottom: '10px' }}>🧪 Test Concurrency</h4>
          <p style={{ color: '#856404', margin: '0', fontSize: '0.9rem' }}>
            Try making multiple simultaneous reservations for the same dates to see the concurrency control in action.
            The system will prevent overbooking even under high load.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Inventory;