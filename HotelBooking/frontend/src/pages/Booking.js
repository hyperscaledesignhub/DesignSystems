import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';

const Booking = ({ user }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [step, setStep] = useState(1);
  const [hotels, setHotels] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [availability, setAvailability] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [bookingData, setBookingData] = useState({
    hotel_id: searchParams.get('hotel') || '',
    room_type_id: searchParams.get('room') || '',
    check_in: '',
    check_out: '',
    num_rooms: 1,
    total_amount: 0
  });

  useEffect(() => {
    loadHotels();
    if (bookingData.hotel_id) {
      loadRooms(bookingData.hotel_id);
    }
  }, [bookingData.hotel_id]);

  useEffect(() => {
    if (bookingData.room_type_id && bookingData.check_in && bookingData.check_out) {
      checkAvailability();
    }
  }, [bookingData.room_type_id, bookingData.check_in, bookingData.check_out, bookingData.num_rooms]);

  const loadHotels = async () => {
    try {
      const data = await ApiService.getHotels();
      setHotels(data);
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

  const checkAvailability = async () => {
    try {
      const availability = await ApiService.checkAvailability(
        bookingData.room_type_id,
        bookingData.check_in,
        bookingData.check_out,
        bookingData.num_rooms
      );
      setAvailability(availability);
      
      // Calculate total amount
      const selectedRoom = rooms.find(r => r.room_type_id === bookingData.room_type_id);
      if (selectedRoom) {
        const nights = calculateNights(bookingData.check_in, bookingData.check_out);
        const total = selectedRoom.base_price * bookingData.num_rooms * nights;
        setBookingData(prev => ({ ...prev, total_amount: total }));
      }
    } catch (err) {
      setError('Failed to check availability: ' + err.message);
      setAvailability(null);
    }
  };

  const calculateNights = (checkIn, checkOut) => {
    const start = new Date(checkIn);
    const end = new Date(checkOut);
    const diffTime = Math.abs(end - start);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const handleInputChange = (field, value) => {
    setBookingData(prev => ({
      ...prev,
      [field]: value
    }));
    
    if (field === 'hotel_id') {
      loadRooms(value);
      setBookingData(prev => ({ ...prev, room_type_id: '' }));
    }
  };

  const createReservation = async () => {
    setLoading(true);
    setError('');
    try {
      const reservationData = {
        guest_id: user.id,
        room_type_id: bookingData.room_type_id,
        check_in: bookingData.check_in,
        check_out: bookingData.check_out,
        num_rooms: bookingData.num_rooms,
        total_amount: bookingData.total_amount
      };
      
      const reservation = await ApiService.createReservation(reservationData);
      setSuccess('Reservation created successfully!');
      
      setTimeout(() => {
        navigate(`/reservations`);
      }, 2000);
      
    } catch (err) {
      setError('Failed to create reservation: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectedHotel = hotels.find(h => h.hotel_id === bookingData.hotel_id);
  const selectedRoom = rooms.find(r => r.room_type_id === bookingData.room_type_id);
  const nights = bookingData.check_in && bookingData.check_out ? calculateNights(bookingData.check_in, bookingData.check_out) : 0;

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <div className="card">
        <h1 style={{ color: '#333', marginBottom: '30px' }}>Book a Room</h1>
        
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {/* Step 1: Select Hotel and Room */}
        <div style={{ marginBottom: '30px' }}>
          <h3 style={{ color: '#667eea', marginBottom: '20px' }}>1. Select Hotel and Room</h3>
          
          <div className="form-group">
            <label className="form-label">Hotel</label>
            <select
              className="form-input"
              value={bookingData.hotel_id}
              onChange={(e) => handleInputChange('hotel_id', e.target.value)}
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

          {rooms.length > 0 && (
            <div className="form-group">
              <label className="form-label">Room Type</label>
              <select
                className="form-input"
                value={bookingData.room_type_id}
                onChange={(e) => handleInputChange('room_type_id', e.target.value)}
                required
              >
                <option value="">Select a room type</option>
                {rooms.map(room => (
                  <option key={room.room_type_id} value={room.room_type_id}>
                    {room.name} - {ApiService.formatCurrency(room.base_price)}/night (Max {room.max_occupancy} guests)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Step 2: Select Dates */}
        <div style={{ marginBottom: '30px' }}>
          <h3 style={{ color: '#667eea', marginBottom: '20px' }}>2. Select Dates</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
            <div className="form-group">
              <label className="form-label">Check-in</label>
              <input
                type="date"
                className="form-input"
                value={bookingData.check_in}
                onChange={(e) => handleInputChange('check_in', e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                required
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Check-out</label>
              <input
                type="date"
                className="form-input"
                value={bookingData.check_out}
                onChange={(e) => handleInputChange('check_out', e.target.value)}
                min={bookingData.check_in}
                required
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Number of Rooms</label>
              <input
                type="number"
                className="form-input"
                value={bookingData.num_rooms}
                onChange={(e) => handleInputChange('num_rooms', parseInt(e.target.value))}
                min="1"
                max="10"
                required
              />
            </div>
          </div>
        </div>

        {/* Step 3: Check Availability */}
        {availability && (
          <div style={{ marginBottom: '30px' }}>
            <h3 style={{ color: '#667eea', marginBottom: '20px' }}>3. Availability Check</h3>
            
            <div style={{ 
              padding: '20px', 
              background: availability.available_rooms >= bookingData.num_rooms ? '#d4edda' : '#f8d7da', 
              borderRadius: '8px',
              border: `1px solid ${availability.available_rooms >= bookingData.num_rooms ? '#c3e6cb' : '#f5c6cb'}`
            }}>
              {availability.available_rooms >= bookingData.num_rooms ? (
                <div>
                  <h4 style={{ color: '#155724', margin: '0 0 10px 0' }}>✅ Rooms Available!</h4>
                  <p style={{ color: '#155724', margin: '0' }}>
                    {availability.available_rooms} rooms available for your dates
                  </p>
                </div>
              ) : (
                <div>
                  <h4 style={{ color: '#721c24', margin: '0 0 10px 0' }}>❌ Not Available</h4>
                  <p style={{ color: '#721c24', margin: '0' }}>
                    Only {availability.available_rooms} rooms available, but you need {bookingData.num_rooms}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Booking Summary */}
        {selectedHotel && selectedRoom && bookingData.check_in && bookingData.check_out && (
          <div style={{ marginBottom: '30px' }}>
            <h3 style={{ color: '#667eea', marginBottom: '20px' }}>4. Booking Summary</h3>
            
            <div style={{ padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div>
                  <strong>Hotel:</strong> {selectedHotel.name}<br/>
                  <strong>Room Type:</strong> {selectedRoom.name}<br/>
                  <strong>Guests per room:</strong> Max {selectedRoom.max_occupancy}
                </div>
                <div>
                  <strong>Check-in:</strong> {bookingData.check_in}<br/>
                  <strong>Check-out:</strong> {bookingData.check_out}<br/>
                  <strong>Nights:</strong> {nights}
                </div>
              </div>
              
              <hr style={{ margin: '15px 0' }}/>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong>Rooms:</strong> {bookingData.num_rooms} × {ApiService.formatCurrency(selectedRoom.base_price)} × {nights} nights
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#28a745' }}>
                  Total: {ApiService.formatCurrency(bookingData.total_amount)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Book Button */}
        {availability && availability.available_rooms >= bookingData.num_rooms && bookingData.total_amount > 0 && (
          <button
            className="btn btn-success"
            onClick={createReservation}
            disabled={loading}
            style={{ width: '100%', padding: '15px' }}
          >
            {loading ? 'Creating Reservation...' : `Book Now - ${ApiService.formatCurrency(bookingData.total_amount)}`}
          </button>
        )}

        {/* Workflow Information */}
        <div className="alert alert-info" style={{ marginTop: '30px' }}>
          <strong>Complete Booking Workflow:</strong><br/>
          1. Guest Registration → 2. Browse Hotels → 3. Select Room Type → 
          4. Check Availability → 5. Create Reservation → 6. Process Payment
        </div>
      </div>
    </div>
  );
};

export default Booking;