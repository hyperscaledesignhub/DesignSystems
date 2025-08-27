import React, { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react';
import api from '../services/api';
import { useWebSocket } from '../contexts/WebSocketContext';
import './MarketData.css';

const MarketData = () => {
  const [symbols, setSymbols] = useState([
    { symbol: 'AAPL', price: 150, change: 2.5, volume: 1000000 },
    { symbol: 'GOOGL', price: 2800, change: -1.2, volume: 500000 },
    { symbol: 'MSFT', price: 380, change: 1.8, volume: 750000 },
    { symbol: 'AMZN', price: 170, change: -0.5, volume: 600000 },
    { symbol: 'TSLA', price: 250, change: 3.2, volume: 1200000 }
  ]);
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [priceHistory, setPriceHistory] = useState([]);
  const [volumeData, setVolumeData] = useState([]);
  const { marketData, subscribeToSymbol } = useWebSocket();

  useEffect(() => {
    fetchMarketData();
    generateHistoricalData();
    subscribeToSymbol(selectedSymbol);
    const interval = setInterval(() => {
      updatePrices();
      generateHistoricalData();
    }, 5000);
    return () => clearInterval(interval);
  }, [selectedSymbol]);

  const fetchMarketData = async () => {
    try {
      const response = await api.get('/marketdata/symbols');
      if (response.data && response.data.length > 0) {
        setSymbols(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch market data:', error);
    }
  };

  const updatePrices = () => {
    setSymbols(prev => prev.map(s => ({
      ...s,
      price: s.price * (1 + (Math.random() - 0.5) * 0.02),
      change: (Math.random() - 0.5) * 5,
      volume: Math.floor(s.volume * (0.8 + Math.random() * 0.4))
    })));
  };

  const generateHistoricalData = () => {
    const now = new Date();
    const history = [];
    const volume = [];
    
    for (let i = 30; i >= 0; i--) {
      const time = new Date(now - i * 60000);
      const basePrice = selectedSymbol === 'AAPL' ? 150 : 
                       selectedSymbol === 'GOOGL' ? 2800 :
                       selectedSymbol === 'MSFT' ? 380 :
                       selectedSymbol === 'AMZN' ? 170 : 250;
      
      history.push({
        time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        price: basePrice + (Math.random() - 0.5) * 10,
        volume: Math.floor(Math.random() * 100000) + 50000
      });
      
      volume.push({
        time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        volume: Math.floor(Math.random() * 100000) + 50000,
        buy: Math.floor(Math.random() * 50000) + 25000,
        sell: Math.floor(Math.random() * 50000) + 25000
      });
    }
    
    setPriceHistory(history);
    setVolumeData(volume);
  };

  return (
    <div className="market-data">
      <div className="market-header">
        <h1>Market Data</h1>
        <p>Real-time market prices and analytics</p>
      </div>

      <div className="market-overview">
        {symbols.map(stock => (
          <div 
            key={stock.symbol} 
            className={`market-card ${selectedSymbol === stock.symbol ? 'active' : ''}`}
            onClick={() => setSelectedSymbol(stock.symbol)}
          >
            <div className="market-card-header">
              <span className="symbol">{stock.symbol}</span>
              {stock.change >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            </div>
            <div className="market-price">${stock.price.toFixed(2)}</div>
            <div className={`market-change ${stock.change >= 0 ? 'positive' : 'negative'}`}>
              {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
            </div>
            <div className="market-volume">
              Vol: {(stock.volume / 1000).toFixed(0)}K
            </div>
          </div>
        ))}
      </div>

      <div className="charts-section">
        <div className="chart-container">
          <h3>
            <Activity size={20} />
            Price Chart - {selectedSymbol}
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={priceHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={['dataMin - 5', 'dataMax + 5']} />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="price" 
                stroke="#667eea" 
                fill="url(#colorPrice)" 
                strokeWidth={2}
              />
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#667eea" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#667eea" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>
            <BarChart3 size={20} />
            Volume Analysis
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={volumeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="buy" stackId="a" fill="#10b981" />
              <Bar dataKey="sell" stackId="a" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="market-stats">
        <div className="stats-grid">
          <div className="stat-box">
            <span className="stat-label">Day High</span>
            <span className="stat-value">
              ${(symbols.find(s => s.symbol === selectedSymbol)?.price * 1.02).toFixed(2)}
            </span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Day Low</span>
            <span className="stat-value">
              ${(symbols.find(s => s.symbol === selectedSymbol)?.price * 0.98).toFixed(2)}
            </span>
          </div>
          <div className="stat-box">
            <span className="stat-label">52W High</span>
            <span className="stat-value">
              ${(symbols.find(s => s.symbol === selectedSymbol)?.price * 1.3).toFixed(2)}
            </span>
          </div>
          <div className="stat-box">
            <span className="stat-label">52W Low</span>
            <span className="stat-value">
              ${(symbols.find(s => s.symbol === selectedSymbol)?.price * 0.7).toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketData;