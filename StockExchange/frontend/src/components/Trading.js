import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, AlertCircle, CheckCircle, XCircle, Plus } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';
import './Trading.css';

const Trading = () => {
  const [orderForm, setOrderForm] = useState({
    symbol: 'AAPL',
    side: 'BUY',
    orderType: 'LIMIT',
    quantity: '',
    price: '',
    stopPrice: '',
    timeInForce: 'DAY'
  });
  const [orders, setOrders] = useState([]);
  const [positions, setPositions] = useState([]);
  const [balance, setBalance] = useState({ available: 0, blocked: 0 });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('orders');
  const [showAddFunds, setShowAddFunds] = useState(false);
  const [fundsAmount, setFundsAmount] = useState('');

  useEffect(() => {
    fetchOrders();
    fetchPositions();
    fetchBalance();
    const interval = setInterval(() => {
      fetchOrders();
      fetchPositions();
      fetchBalance();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await api.get('/v1/orders');
      setOrders(response.data || []);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    }
  };

  const fetchPositions = async () => {
    try {
      const response = await api.get('/reports/positions');
      setPositions(response.data.positions || []);
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    }
  };

  const fetchBalance = async () => {
    try {
      const response = await api.get('/wallet/balance');
      setBalance(response.data);
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    }
  };

  const addFunds = async () => {
    if (!fundsAmount || isNaN(fundsAmount) || parseFloat(fundsAmount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    try {
      await api.post('/wallet/add-funds', {
        amount: parseFloat(fundsAmount)
      });
      
      // Refresh balance to show updated funds
      fetchBalance();
      setShowAddFunds(false);
      setFundsAmount('');
      toast.success('Funds added successfully!');
    } catch (error) {
      console.error('Failed to add funds:', error);
      toast.error('Failed to add funds. Please try again.');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setOrderForm(prev => ({ ...prev, [name]: value }));
  };

  const calculateOrderValue = () => {
    const quantity = parseFloat(orderForm.quantity) || 0;
    const price = parseFloat(orderForm.price) || 0;
    return (quantity * price).toFixed(2);
  };

  const submitOrder = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const orderData = {
        symbol: orderForm.symbol,
        side: orderForm.side,
        quantity: orderForm.quantity,
        price: orderForm.price,
        order_type: orderForm.orderType,
        time_in_force: orderForm.timeInForce
      };
      
      if (orderForm.orderType === 'STOP_LIMIT') {
        orderData.stop_price = orderForm.stopPrice;
      }
      
      const response = await api.post('/v1/order', orderData);
      toast.success(`Order placed successfully! ID: ${response.data.id}`);
      
      setOrderForm(prev => ({ ...prev, quantity: '', price: '', stopPrice: '' }));
      fetchOrders();
      fetchBalance();
    } catch (error) {
      toast.error(`Order failed: ${error.response?.data?.detail || 'Please try again'}`);
    } finally {
      setLoading(false);
    }
  };

  const cancelOrder = async (orderId) => {
    try {
      await api.delete(`/v1/order/${orderId}`);
      toast.success('Order cancelled successfully');
      fetchOrders();
      fetchBalance();
    } catch (error) {
      toast.error('Failed to cancel order');
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      'PENDING': { color: 'warning', icon: AlertCircle },
      'PARTIALLY_FILLED': { color: 'info', icon: TrendingUp },
      'FILLED': { color: 'success', icon: CheckCircle },
      'CANCELLED': { color: 'danger', icon: XCircle },
      'REJECTED': { color: 'danger', icon: XCircle }
    };
    
    const badge = badges[status] || { color: 'secondary', icon: AlertCircle };
    const Icon = badge.icon;
    
    return (
      <span className={`status-badge ${badge.color}`}>
        <Icon size={14} />
        {status}
      </span>
    );
  };

  return (
    <div className="trading">
      <div className="trading-header">
        <h1>Trading Terminal</h1>
        <div className="balance-info">
          <div className="balance-item">
            <span>Available:</span>
            <strong>${balance.available?.toLocaleString() || 0}</strong>
          </div>
          <div className="balance-item">
            <span>Blocked:</span>
            <strong>${balance.blocked?.toLocaleString() || 0}</strong>
          </div>
          <button 
            className="add-funds-btn-small" 
            onClick={() => setShowAddFunds(true)}
            title="Add demo funds to wallet"
          >
            <Plus size={14} />
            Add Funds
          </button>
        </div>
      </div>

      <div className="trading-layout">
        <div className="order-panel">
          <form onSubmit={submitOrder} className="order-form">
            <h2>Place Order</h2>
            
            <div className="form-row">
              <div className="form-group">
                <label>Symbol</label>
                <select name="symbol" value={orderForm.symbol} onChange={handleInputChange}>
                  <option value="AAPL">AAPL - Apple Inc.</option>
                  <option value="GOOGL">GOOGL - Alphabet Inc.</option>
                  <option value="MSFT">MSFT - Microsoft Corp.</option>
                  <option value="AMZN">AMZN - Amazon.com Inc.</option>
                  <option value="TSLA">TSLA - Tesla Inc.</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Side</label>
                <div className="side-buttons">
                  <button
                    type="button"
                    className={`side-btn buy ${orderForm.side === 'BUY' ? 'active' : ''}`}
                    onClick={() => setOrderForm(prev => ({ ...prev, side: 'BUY' }))}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    className={`side-btn sell ${orderForm.side === 'SELL' ? 'active' : ''}`}
                    onClick={() => setOrderForm(prev => ({ ...prev, side: 'SELL' }))}
                  >
                    SELL
                  </button>
                </div>
              </div>
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label>Order Type</label>
                <select name="orderType" value={orderForm.orderType} onChange={handleInputChange}>
                  <option value="MARKET">Market</option>
                  <option value="LIMIT">Limit</option>
                  <option value="STOP_LIMIT">Stop Limit</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Time in Force</label>
                <select name="timeInForce" value={orderForm.timeInForce} onChange={handleInputChange}>
                  <option value="DAY">Day</option>
                  <option value="GTC">Good Till Cancel</option>
                  <option value="IOC">Immediate or Cancel</option>
                  <option value="FOK">Fill or Kill</option>
                </select>
              </div>
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label>Quantity</label>
                <input
                  type="number"
                  name="quantity"
                  value={orderForm.quantity}
                  onChange={handleInputChange}
                  placeholder="Enter quantity"
                  min="1"
                  required
                />
              </div>
              
              {orderForm.orderType !== 'MARKET' && (
                <div className="form-group">
                  <label>Price</label>
                  <input
                    type="number"
                    name="price"
                    value={orderForm.price}
                    onChange={handleInputChange}
                    placeholder="Enter price"
                    min="0.01"
                    step="0.01"
                    required
                  />
                </div>
              )}
            </div>
            
            {orderForm.orderType === 'STOP_LIMIT' && (
              <div className="form-row">
                <div className="form-group">
                  <label>Stop Price</label>
                  <input
                    type="number"
                    name="stopPrice"
                    value={orderForm.stopPrice}
                    onChange={handleInputChange}
                    placeholder="Enter stop price"
                    min="0.01"
                    step="0.01"
                    required
                  />
                </div>
              </div>
            )}
            
            <div className="order-summary">
              <div className="summary-item">
                <span>Order Value:</span>
                <strong>${calculateOrderValue()}</strong>
              </div>
              <div className="summary-item">
                <span>Commission:</span>
                <strong>$0.99</strong>
              </div>
              <div className="summary-item total">
                <span>Total:</span>
                <strong>${(parseFloat(calculateOrderValue()) + 0.99).toFixed(2)}</strong>
              </div>
            </div>
            
            <button type="submit" className="btn-submit-order" disabled={loading}>
              {loading ? 'Placing Order...' : `Place ${orderForm.side} Order`}
            </button>
          </form>
        </div>

        <div className="orders-panel">
          <div className="panel-tabs">
            <button
              className={`tab ${activeTab === 'orders' ? 'active' : ''}`}
              onClick={() => setActiveTab('orders')}
            >
              Open Orders ({orders.filter(o => o.status === 'PENDING').length})
            </button>
            <button
              className={`tab ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              Order History
            </button>
            <button
              className={`tab ${activeTab === 'positions' ? 'active' : ''}`}
              onClick={() => setActiveTab('positions')}
            >
              Positions ({positions.length})
            </button>
          </div>

          <div className="panel-content">
            {activeTab === 'orders' && (
              <div className="orders-list">
                {orders.filter(o => o.status === 'PENDING' || o.status === 'PARTIALLY_FILLED').length > 0 ? (
                  <table className="orders-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Filled</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.filter(o => o.status === 'PENDING' || o.status === 'PARTIALLY_FILLED').map(order => (
                        <tr key={order.id}>
                          <td className="symbol">{order.symbol}</td>
                          <td>
                            <span className={`side ${order.side.toLowerCase()}`}>
                              {order.side}
                            </span>
                          </td>
                          <td>{order.quantity}</td>
                          <td>${order.price}</td>
                          <td>{order.filled_quantity}/{order.quantity}</td>
                          <td>{getStatusBadge(order.status)}</td>
                          <td>
                            <button
                              className="btn-cancel"
                              onClick={() => cancelOrder(order.id)}
                            >
                              Cancel
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="no-data">No open orders</div>
                )}
              </div>
            )}

            {activeTab === 'history' && (
              <div className="orders-list">
                {orders.filter(o => o.status === 'FILLED' || o.status === 'CANCELLED' || o.status === 'REJECTED').length > 0 ? (
                  <table className="orders-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.filter(o => o.status === 'FILLED' || o.status === 'CANCELLED' || o.status === 'REJECTED').map(order => (
                        <tr key={order.id}>
                          <td>{new Date(order.created_at).toLocaleString()}</td>
                          <td className="symbol">{order.symbol}</td>
                          <td>
                            <span className={`side ${order.side.toLowerCase()}`}>
                              {order.side}
                            </span>
                          </td>
                          <td>{order.quantity}</td>
                          <td>${order.price}</td>
                          <td>{getStatusBadge(order.status)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="no-data">No order history</div>
                )}
              </div>
            )}

            {activeTab === 'positions' && (
              <div className="positions-list">
                {positions.length > 0 ? (
                  <table className="positions-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Avg Price</th>
                        <th>Current Price</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map(position => (
                        <tr key={position.symbol}>
                          <td className="symbol">{position.symbol}</td>
                          <td>{position.quantity}</td>
                          <td>${position.average_price}</td>
                          <td>${position.current_price}</td>
                          <td className={position.unrealized_pnl >= 0 ? 'profit' : 'loss'}>
                            ${position.unrealized_pnl?.toFixed(2)}
                          </td>
                          <td className={position.pnl_percentage >= 0 ? 'profit' : 'loss'}>
                            {position.pnl_percentage?.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="no-data">No positions</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {showAddFunds && (
        <div className="modal-overlay" onClick={() => setShowAddFunds(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Add Demo Funds</h3>
            <div className="form-group">
              <label>Amount (USD):</label>
              <input
                type="number"
                value={fundsAmount}
                onChange={(e) => setFundsAmount(e.target.value)}
                placeholder="Enter amount..."
                min="1"
                step="1000"
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowAddFunds(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={addFunds}>
                Add Funds
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Trading;