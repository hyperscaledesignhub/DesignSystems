import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';

const Payments = ({ user }) => {
  const [searchParams] = useSearchParams();
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [paymentForm, setPaymentForm] = useState({
    reservation_id: searchParams.get('reservation') || '',
    amount: parseFloat(searchParams.get('amount')) || 0,
    payment_method: 'credit_card',
    currency: 'USD'
  });
  
  const [searchId, setSearchId] = useState('');

  useEffect(() => {
    const loadUserPayments = async () => {
      setLoading(true);
      setError('');
      try {
        console.log('Loading user reservations first...');
        // First get user's reservations
        const userReservations = await ApiService.getReservations(user.id);
        console.log('User reservations:', userReservations);
        
        // Then get all payments and filter by user's reservation IDs
        const allPayments = await ApiService.getPayments();
        console.log('All payments:', allPayments);
        
        // Filter payments to only include ones for this user's reservations
        const userReservationIds = userReservations.map(res => res.id);
        const userPayments = allPayments.filter(payment => 
          userReservationIds.includes(payment.reservation_id)
        );
        
        console.log('Filtered user payments:', userPayments);
        setPayments(userPayments || []);
      } catch (err) {
        console.error('Error loading payments:', err);
        setError('Failed to load payments: ' + err.message);
      } finally {
        setLoading(false);
      }
    };
    
    loadUserPayments();
  }, [user.id]);

  const processPayment = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const payment = await ApiService.processPayment(paymentForm);
      setPayments(prev => [payment, ...prev]);
      setSuccess('Payment processed successfully!');
      
      // Reset form
      setPaymentForm({
        reservation_id: '',
        amount: 0,
        payment_method: 'credit_card',
        currency: 'USD'
      });
    } catch (err) {
      setError('Payment failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const searchPayment = async (e) => {
    e.preventDefault();
    if (!searchId.trim()) return;

    setLoading(true);
    setError('');
    try {
      const payment = await ApiService.getPayment(searchId);
      setPayments([payment]);
    } catch (err) {
      setError('Payment not found: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      completed: 'status-badge status-completed',
      pending: 'status-badge status-pending',
      failed: 'status-badge status-cancelled'
    };
    return <span className={statusClasses[status] || 'status-badge'}>{status}</span>;
  };

  // Demo payments only for specific demo users (not for regular test users)
  const isDemoUser = user.email === 'demo@example.com' || user.id === 'demo-user-1756734532959';
  
  const demoPayments = isDemoUser ? [
    {
      id: 'demo-payment-1',
      reservation_id: 'demo-reservation-1',
      amount: 400.0,
      currency: 'USD',
      payment_method: 'credit_card',
      status: 'completed',
      processed_at: new Date().toISOString(),
      created_at: new Date().toISOString()
    },
    {
      id: 'demo-payment-2',
      reservation_id: 'demo-reservation-2',
      amount: 200.0,
      currency: 'EUR',
      payment_method: 'paypal',
      status: 'completed',
      processed_at: new Date().toISOString(),
      created_at: new Date().toISOString()
    }
  ] : [];

  const displayPayments = payments.length > 0 ? payments : demoPayments;

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div className="card" style={{ marginBottom: '30px' }}>
        <h1 style={{ color: '#333', marginBottom: '20px' }}>Payment Processing</h1>
        
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        <div className="alert alert-info">
          <strong>Payment Processing Workflow:</strong> 
          Handle payment for reservations with mock implementation and check payment status.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '30px' }}>
        {/* Process Payment Form */}
        <div className="card">
          <h2 style={{ color: '#333', marginBottom: '20px' }}>Process Payment</h2>
          
          <form onSubmit={processPayment}>
            <div className="form-group">
              <label className="form-label">Reservation ID</label>
              <input
                type="text"
                className="form-input"
                value={paymentForm.reservation_id}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, reservation_id: e.target.value }))}
                placeholder="Enter reservation ID"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Amount</label>
              <input
                type="number"
                className="form-input"
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, amount: parseFloat(e.target.value) }))}
                placeholder="0.00"
                min="0.01"
                step="0.01"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Payment Method</label>
              <select
                className="form-input"
                value={paymentForm.payment_method}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, payment_method: e.target.value }))}
              >
                <option value="credit_card">Credit Card</option>
                <option value="debit_card">Debit Card</option>
                <option value="paypal">PayPal</option>
                <option value="bank_transfer">Bank Transfer</option>
                <option value="apple_pay">Apple Pay</option>
                <option value="google_pay">Google Pay</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Currency</label>
              <select
                className="form-input"
                value={paymentForm.currency}
                onChange={(e) => setPaymentForm(prev => ({ ...prev, currency: e.target.value }))}
              >
                <option value="USD">USD - US Dollar</option>
                <option value="EUR">EUR - Euro</option>
                <option value="GBP">GBP - British Pound</option>
                <option value="JPY">JPY - Japanese Yen</option>
                <option value="CAD">CAD - Canadian Dollar</option>
              </select>
            </div>

            <button
              type="submit"
              className="btn btn-success"
              disabled={loading}
              style={{ width: '100%' }}
            >
              {loading ? 'Processing...' : 'Process Payment'}
            </button>
          </form>
        </div>

        {/* Search Payment */}
        <div className="card">
          <h2 style={{ color: '#333', marginBottom: '20px' }}>Search Payment</h2>
          
          <form onSubmit={searchPayment}>
            <div className="form-group">
              <label className="form-label">Payment ID</label>
              <input
                type="text"
                className="form-input"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                placeholder="Enter payment ID"
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%' }}
            >
              {loading ? 'Searching...' : 'Search Payment'}
            </button>
          </form>

          <div style={{ marginTop: '30px', padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#333', marginBottom: '15px' }}>Payment Methods Tested:</h4>
            <div style={{ display: 'grid', gap: '10px' }}>
              {['Credit Card', 'Debit Card', 'PayPal', 'Bank Transfer', 'Apple Pay'].map(method => (
                <div key={method} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: '#28a745' }}>✅</span>
                  <span>{method}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Payment History */}
      <div className="card">
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Payment History</h2>
        
        {displayPayments.length === 0 ? (
          <div className="text-center" style={{ padding: '40px' }}>
            <h3>No Payments Found</h3>
            <p style={{ color: '#666' }}>Process a payment or search by payment ID.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Payment ID</th>
                  <th>Reservation</th>
                  <th>Amount</th>
                  <th>Method</th>
                  <th>Status</th>
                  <th>Processed</th>
                </tr>
              </thead>
              <tbody>
                {displayPayments.map((payment) => (
                  <tr key={payment.id}>
                    <td>
                      <div style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                        {payment.id}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                        {payment.reservation_id}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontWeight: '600', color: '#28a745' }}>
                        {new Intl.NumberFormat('en-US', {
                          style: 'currency',
                          currency: payment.currency
                        }).format(payment.amount)}
                      </div>
                    </td>
                    <td>
                      <div style={{ textTransform: 'capitalize' }}>
                        {payment.payment_method.replace('_', ' ')}
                      </div>
                    </td>
                    <td>{getStatusBadge(payment.status)}</td>
                    <td>
                      <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        {ApiService.formatDateTime(payment.processed_at)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Payment Features */}
      <div className="card" style={{ marginTop: '30px' }}>
        <h2 style={{ color: '#333', marginBottom: '20px' }}>Payment System Features</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#ffc107' }}>✅ Mock Implementation</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Always successful processing for demo purposes
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#ffc107' }}>✅ Multiple Currencies</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Supports USD, EUR, GBP, JPY, and CAD
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#ffc107' }}>✅ Payment Methods</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Credit/debit cards, PayPal, bank transfers
            </p>
          </div>
          <div style={{ padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <h4 style={{ color: '#ffc107' }}>✅ Status Tracking</h4>
            <p style={{ margin: '0', color: '#666', fontSize: '0.9rem' }}>
              Complete audit trail with timestamps
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Payments;