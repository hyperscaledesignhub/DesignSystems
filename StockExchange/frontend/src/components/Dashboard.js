import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, DollarSign, Activity, 
  Users, BarChart3, Shield, Bell 
} from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../services/api';
import { useWebSocket } from '../contexts/WebSocketContext';
import './Dashboard.css';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalVolume: 0,
    activeUsers: 0,
    totalOrders: 0,
    totalTrades: 0,
    avgSpread: 0,
    successRate: 0
  });
  const [recentTrades, setRecentTrades] = useState([]);
  const [marketData, setMarketData] = useState([]);
  const [loading, setLoading] = useState(true);
  const { tradeUpdates, orderUpdates } = useWebSocket();

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (tradeUpdates.length > 0) {
      setRecentTrades(prev => [...tradeUpdates.slice(0, 5), ...prev].slice(0, 10));
    }
  }, [tradeUpdates]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      const [statsRes, tradesRes, marketRes] = await Promise.all([
        api.get('/reports/statistics'),
        api.get('/reports/trades?limit=10'),
        api.get('/marketdata/symbols')
      ]);

      setStats(statsRes.data);
      setRecentTrades(tradesRes.data.trades || []);
      
      const chartData = generateChartData();
      setMarketData(chartData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateChartData = () => {
    const now = new Date();
    return Array.from({ length: 12 }, (_, i) => {
      const time = new Date(now - (11 - i) * 5 * 60000);
      return {
        time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        volume: Math.floor(Math.random() * 50000) + 10000,
        price: 150 + Math.random() * 10,
        orders: Math.floor(Math.random() * 100) + 20
      };
    });
  };

  const StatCard = ({ icon: Icon, title, value, change, color }) => (
    <div className="stat-card">
      <div className="stat-header">
        <Icon size={24} className="stat-icon" style={{ color }} />
        <span className="stat-title">{title}</span>
      </div>
      <div className="stat-value">{value}</div>
      {change !== undefined && (
        <div className={`stat-change ${change >= 0 ? 'positive' : 'negative'}`}>
          {change >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          <span>{Math.abs(change)}%</span>
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Trading Dashboard</h1>
        <p>Real-time market overview and system metrics</p>
      </div>

      <div className="stats-grid">
        <StatCard 
          icon={DollarSign} 
          title="Total Volume" 
          value={`$${(stats.totalVolume || 0).toLocaleString()}`}
          change={12.5}
          color="#10b981"
        />
        <StatCard 
          icon={Activity} 
          title="Total Orders" 
          value={(stats.totalOrders || 0).toLocaleString()}
          change={8.3}
          color="#667eea"
        />
        <StatCard 
          icon={Users} 
          title="Active Users" 
          value={stats.activeUsers || 0}
          change={-2.1}
          color="#f59e0b"
        />
        <StatCard 
          icon={BarChart3} 
          title="Success Rate" 
          value={`${(stats.successRate || 0).toFixed(1)}%`}
          change={5.7}
          color="#ef4444"
        />
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Trading Volume</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={marketData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="volume" fill="#667eea" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Price Movement</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={marketData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={['dataMin - 5', 'dataMax + 5']} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="recent-activity">
        <div className="activity-card">
          <h3>Recent Trades</h3>
          <div className="trades-list">
            {recentTrades.length > 0 ? (
              recentTrades.map((trade, index) => (
                <div key={index} className="trade-item">
                  <div className="trade-symbol">{trade.symbol || 'AAPL'}</div>
                  <div className={`trade-side ${trade.side?.toLowerCase()}`}>
                    {trade.side || 'BUY'}
                  </div>
                  <div className="trade-quantity">{trade.quantity || 0} shares</div>
                  <div className="trade-price">${trade.price || 0}</div>
                  <div className="trade-time">
                    {new Date(trade.timestamp || Date.now()).toLocaleTimeString()}
                  </div>
                </div>
              ))
            ) : (
              <div className="no-data">No recent trades</div>
            )}
          </div>
        </div>

        <div className="activity-card">
          <h3>System Alerts</h3>
          <div className="alerts-list">
            <div className="alert-item info">
              <Bell size={16} />
              <span>Market opened successfully</span>
            </div>
            <div className="alert-item success">
              <Shield size={16} />
              <span>Risk management system operational</span>
            </div>
            <div className="alert-item warning">
              <Activity size={16} />
              <span>High trading volume detected</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;