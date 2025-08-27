import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, RefreshCw } from 'lucide-react';
import api from '../services/api';
import { useWebSocket } from '../contexts/WebSocketContext';
import './OrderBook.css';

const OrderBook = () => {
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [orderBook, setOrderBook] = useState({ asks: [], bids: [], spread: 0 });
  const [depth, setDepth] = useState(10);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const { marketData, subscribeToSymbol, unsubscribeFromSymbol } = useWebSocket();

  const symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'];

  useEffect(() => {
    fetchOrderBook();
    subscribeToSymbol(selectedSymbol);
    const interval = setInterval(fetchOrderBook, 2000);
    
    return () => {
      clearInterval(interval);
      unsubscribeFromSymbol(selectedSymbol);
    };
  }, [selectedSymbol, depth]);

  useEffect(() => {
    if (marketData[selectedSymbol]) {
      updateOrderBookFromWebSocket(marketData[selectedSymbol]);
    }
  }, [marketData, selectedSymbol]);

  const fetchOrderBook = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/marketdata/orderBook/L2?symbol=${selectedSymbol}&depth=${depth}`);
      processOrderBook(response.data);
    } catch (error) {
      console.error('Failed to fetch order book:', error);
    } finally {
      setLoading(false);
    }
  };

  const processOrderBook = (data) => {
    const asks = data.asks || [];
    const bids = data.bids || [];
    
    const spread = asks.length > 0 && bids.length > 0 
      ? (parseFloat(asks[0][0]) - parseFloat(bids[0][0])).toFixed(2)
      : 0;
    
    setOrderBook({ asks, bids, spread });
    setLastUpdate(new Date());
  };

  const updateOrderBookFromWebSocket = (data) => {
    if (data.orderBook) {
      processOrderBook(data.orderBook);
    }
  };

  const calculateTotal = (price, quantity) => {
    return (parseFloat(price) * parseFloat(quantity)).toFixed(2);
  };

  const getMaxQuantity = () => {
    const allQuantities = [
      ...orderBook.asks.map(a => parseFloat(a[1])),
      ...orderBook.bids.map(b => parseFloat(b[1]))
    ];
    return Math.max(...allQuantities, 1);
  };

  const renderOrderRow = (price, quantity, side, index) => {
    const total = calculateTotal(price, quantity);
    const maxQty = getMaxQuantity();
    const percentage = (parseFloat(quantity) / maxQty) * 100;
    
    return (
      <div key={index} className={`order-row ${side}`}>
        <div className="order-depth-bar" style={{ width: `${percentage}%` }}></div>
        <div className="order-data">
          <span className="order-price">${parseFloat(price).toFixed(2)}</span>
          <span className="order-quantity">{quantity}</span>
          <span className="order-total">${total}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="orderbook">
      <div className="orderbook-header">
        <h1>Order Book</h1>
        <div className="header-controls">
          <select 
            value={selectedSymbol} 
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="symbol-select"
          >
            {symbols.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>
          
          <select 
            value={depth} 
            onChange={(e) => setDepth(parseInt(e.target.value))}
            className="depth-select"
          >
            <option value="5">5 Levels</option>
            <option value="10">10 Levels</option>
            <option value="20">20 Levels</option>
            <option value="50">50 Levels</option>
          </select>
          
          <button onClick={fetchOrderBook} className="btn-refresh">
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      <div className="orderbook-stats">
        <div className="stat-item">
          <Activity size={18} />
          <span>Spread: ${orderBook.spread}</span>
        </div>
        <div className="stat-item">
          <TrendingUp size={18} />
          <span>Best Ask: ${orderBook.asks[0]?.[0] || '-'}</span>
        </div>
        <div className="stat-item">
          <TrendingDown size={18} />
          <span>Best Bid: ${orderBook.bids[0]?.[0] || '-'}</span>
        </div>
        <div className="stat-item">
          <span>Last Update: {lastUpdate.toLocaleTimeString()}</span>
        </div>
      </div>

      <div className="orderbook-content">
        <div className="asks-section">
          <div className="section-header">
            <h3>Asks (Sell Orders)</h3>
            <span className="order-count">{orderBook.asks.length} orders</span>
          </div>
          <div className="order-header">
            <span>Price</span>
            <span>Quantity</span>
            <span>Total</span>
          </div>
          <div className="orders-list asks">
            {orderBook.asks.length > 0 ? (
              [...orderBook.asks].reverse().map((ask, index) => 
                renderOrderRow(ask[0], ask[1], 'ask', index)
              )
            ) : (
              <div className="no-orders">No sell orders</div>
            )}
          </div>
        </div>

        <div className="spread-indicator">
          <div className="spread-value">
            <span>SPREAD</span>
            <strong>${orderBook.spread}</strong>
          </div>
        </div>

        <div className="bids-section">
          <div className="section-header">
            <h3>Bids (Buy Orders)</h3>
            <span className="order-count">{orderBook.bids.length} orders</span>
          </div>
          <div className="order-header">
            <span>Price</span>
            <span>Quantity</span>
            <span>Total</span>
          </div>
          <div className="orders-list bids">
            {orderBook.bids.length > 0 ? (
              orderBook.bids.map((bid, index) => 
                renderOrderRow(bid[0], bid[1], 'bid', index)
              )
            ) : (
              <div className="no-orders">No buy orders</div>
            )}
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
        </div>
      )}
    </div>
  );
};

export default OrderBook;