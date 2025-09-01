import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ApiService from '../services/api';

const Reservations = ({ user }) => {
  const navigate = useNavigate();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchId, setSearchId] = useState('');

  const loadReservations = async () => {
    setLoading(true);
    setError('');
    try {
      console.log('Loading reservations for user:', user.id);
      const data = await ApiService.getReservations(user.id);
      console.log('Received reservations:', data);
      setReservations(data || []);
    } catch (err) {
      console.error('Error loading reservations:', err);
      setError('Failed to load reservations: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReservations();
  }, [user]);

  // Also reload when the page becomes visible (user comes back from payment page)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log('Page became visible, reloading reservations...');
        loadReservations();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);


  const searchReservation = async (e) => {
    e.preventDefault();
    if (!searchId.trim()) return;

    setLoading(true);
    setError('');
    try {
      const reservation = await ApiService.getReservation(searchId);
      setReservations([reservation]);
    } catch (err) {
      setError('Reservation not found: ' + err.message);
      setReservations([]);
    } finally {
      setLoading(false);
    }
  };

  const cancelReservation = async (reservationId) => {
    if (!window.confirm('Are you sure you want to cancel this reservation?')) return;

    try {
      await ApiService.cancelReservation(reservationId);
      setSuccess('Reservation cancelled successfully!');
      
      // Update the reservation status in the list
      setReservations(prev => 
        prev.map(res => 
          res.id === reservationId 
            ? { ...res, status: 'cancelled' }
            : res
        )
      );

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to cancel reservation: ' + err.message);
    }
  };

  const processPayment = (reservationId, amount) => {
    navigate(`/payments?reservation=${reservationId}&amount=${amount}`);
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      confirmed: 'status-badge status-confirmed',
      cancelled: 'status-badge status-cancelled',
      pending: 'status-badge status-pending'
    };
    return <span className={statusClasses[status] || 'status-badge'}>{status}</span>;
  };

  // Demo reservations only for specific demo users (not for regular test users)
  const isDemoUser = user.email === 'demo@example.com' || user.id === 'demo-user-1756734532959';
  
  const demoReservations = isDemoUser ? [
    {
      id: 'demo-reservation-1',
      guest_id: user.id,
      hotel_id: 'demo-hotel',
      room_type_id: 'demo-room',
      check_in_date: '2026-01-15',
      check_out_date: '2026-01-17',
      num_rooms: 1,
      total_amount: 400.0,
      status: 'confirmed',
      created_at: new Date().toISOString(),
      hotel_name: 'Demo Grand Hotel',
      room_name: 'Deluxe Suite'
    },
    {
      id: 'demo-reservation-2',
      guest_id: user.id,
      hotel_id: 'demo-hotel-2',
      room_type_id: 'demo-room-2',
      check_in_date: '2026-02-01',
      check_out_date: '2026-02-03',
      num_rooms: 2,
      total_amount: 600.0,
      status: 'pending',
      created_at: new Date().toISOString(),
      hotel_name: 'Demo City Hotel',
      room_name: 'Standard Room'
    }
  ] : [];

  const displayReservations = reservations.length > 0 ? reservations : demoReservations;

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: '30px' }}>
        <h1 style={{ color: '#333', marginBottom: '20px' }}>My Reservations</h1>
        
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {/* Search Reservation */}
        <form onSubmit={searchReservation} style={{ marginBottom: '30px' }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'end' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label">Search by Reservation ID</label>
              <input
                type="text"
                className="form-input"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                placeholder="Enter reservation ID"
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ height: 'fit-content' }}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        <div className="alert alert-info">
          <strong>Reservation Management Workflow:</strong> 
          Create reservations with concurrency control, view booking details, and cancel existing bookings.
          {reservations.length === 0 && ' Below are demo reservations for testing.'}
        </div>
      </div>

      {/* Reservations List */}
      {displayReservations.length === 0 ? (
        <div className="card text-center">
          <h3>No Reservations Found</h3>
          <p>You don't have any reservations yet.</p>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/booking')}
          >
            Make a Reservation
          </button>
        </div>
      ) : (
        <div className="card-grid">
          {displayReservations.map((reservation) => (
            <div key={reservation.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '15px' }}>
                <div>
                  <h3 style={{ margin: '0 0 5px 0', color: '#333' }}>
                    {reservation.hotel_name || 'Hotel Booking'}
                  </h3>
                  <p style={{ margin: '0', fontSize: '0.9rem', color: '#666' }}>
                    ID: {reservation.id}
                  </p>
                </div>
                {getStatusBadge(reservation.status)}
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '15px' }}>
                  <div>
                    <strong>Room:</strong><br/>
                    <span style={{ color: '#666' }}>
                      {reservation.room_name || 'Room Type'}
                    </span>
                  </div>
                  <div>
                    <strong>Rooms:</strong><br/>
                    <span style={{ color: '#666' }}>
                      {reservation.num_rooms}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '15px' }}>
                  <div>
                    <strong>Check-in:</strong><br/>
                    <span style={{ color: '#666' }}>
                      {new Date(reservation.check_in_date).toLocaleDateString()}
                    </span>
                  </div>
                  <div>
                    <strong>Check-out:</strong><br/>
                    <span style={{ color: '#666' }}>
                      {new Date(reservation.check_out_date).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
                  <span><strong>Total Amount:</strong></span>
                  <span style={{ fontSize: '1.2rem', fontWeight: '600', color: '#28a745' }}>
                    {ApiService.formatCurrency(reservation.total_amount)}
                  </span>
                </div>

                <p style={{ margin: '10px 0 0 0', color: '#666', fontSize: '0.9rem' }}>
                  Booked: {ApiService.formatDateTime(reservation.created_at)}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                {reservation.status === 'confirmed' && (
                  <>
                    <button
                      className="btn btn-success"
                      onClick={() => processPayment(reservation.id, reservation.total_amount)}
                      style={{ flex: 1 }}
                    >
                      Pay Now
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => cancelReservation(reservation.id)}
                    >
                      Cancel
                    </button>
                  </>
                )}
                {reservation.status === 'paid' && (
                  <div style={{ color: '#28a745', fontWeight: 'bold', padding: '10px', textAlign: 'center', width: '100%', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                    ✅ Payment Completed
                  </div>
                )}
                
                {reservation.status === 'pending' && (
                  <button
                    className="btn btn-warning"
                    style={{ width: '100%' }}
                    disabled
                  >
                    Payment Pending
                  </button>
                )}
                
                {reservation.status === 'cancelled' && (
                  <button
                    className="btn btn-secondary"
                    style={{ width: '100%' }}
                    disabled
                  >
                    Cancelled
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Concurrency Control Demo */}
      <div className="card" style={{ marginTop: '30px' }}>
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Concurrency Control Features</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#28a745' }}>✅ Database Constraints</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Prevents overbooking with CHECK constraints
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#28a745' }}>✅ Atomic Operations</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Reservation + inventory update in single transaction
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#28a745' }}>✅ Row-Level Locking</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              PostgreSQL handles concurrent access safely
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reservations;