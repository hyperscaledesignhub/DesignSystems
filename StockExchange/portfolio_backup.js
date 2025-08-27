import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Briefcase, TrendingUp, TrendingDown, DollarSign, PieChart as PieIcon, Lock } from 'lucide-react';
import api from '../services/api';
import './Portfolio.css';

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState({
    totalValue: 0,
    totalPnL: 0,
    pnlPercentage: 0,
    positions: [],
    allocations: []
  });
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('positions');

  const COLORS = ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  useEffect(() => {
    fetchPortfolioData();
    const interval = setInterval(fetchPortfolioData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      const [positionsRes, tradesRes, balanceRes] = await Promise.all([
        api.get('/reports/positions'),
        api.get('/reports/trades?limit=50'),
        api.get('/wallet/balance')
      ]);

      const positions = positionsRes.data.positions || [];
      const trades = tradesRes.data.trades || [];
      const balance = balanceRes.data;

      const totalValue = positions.reduce((sum, p) => 
        sum + (p.quantity * p.current_price), 0
      ) + balance.available_balance;

      const totalCost = positions.reduce((sum, p) => 
        sum + (p.quantity * p.average_price), 0
      );

      const totalPnL = positions.reduce((sum, p) => 
        sum + p.unrealized_pnl, 0
      );

      const pnlPercentage = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0;

      const allocations = calculateAllocations(positions, balance.available_balance);

      setPortfolio({
        totalValue,
        totalPnL,
        pnlPercentage,
        positions,
        allocations,
        cashBalance: balance.available_balance,
        blockedBalance: balance.blocked_balance || 0
      });

      setTransactions(trades);
    } catch (error) {
      console.error('Failed to fetch portfolio data:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateAllocations = (positions, cash) => {
    const totalValue = positions.reduce((sum, p) => 
      sum + (p.quantity * p.current_price), 0
    ) + cash;

    if (totalValue === 0) return [];

    const allocations = positions.map(p => ({
      name: p.symbol,
      value: p.quantity * p.current_price,
      percentage: ((p.quantity * p.current_price) / totalValue * 100).toFixed(2)
    }));

    if (cash > 0) {
      allocations.push({
        name: 'Cash',
        value: cash,
        percentage: ((cash / totalValue) * 100).toFixed(2)
      });
    }

    return allocations;
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload[0]) {
      return (
        <div className="custom-tooltip">
          <p className="label">{payload[0].name}</p>
          <p className="value">${payload[0].value.toFixed(2)}</p>
          <p className="percentage">{payload[0].payload.percentage}%</p>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading portfolio...</p>
      </div>
    );
  }

  return (
    <div className="portfolio">
      <div className="portfolio-header">
        <h1>Portfolio Overview</h1>
        <p>Your investment performance and asset allocation</p>
      </div>

      <div className="portfolio-summary">
        <div className="summary-card">
          <div className="summary-icon">
            <Briefcase size={24} />
          </div>
          <div className="summary-content">
            <span className="summary-label">Total Value</span>
            <span className="summary-value">${portfolio.totalValue.toLocaleString()}</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">
            {portfolio.totalPnL >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
          </div>
          <div className="summary-content">
            <span className="summary-label">Total P&L</span>
            <span className={`summary-value ${portfolio.totalPnL >= 0 ? 'profit' : 'loss'}`}>
              {portfolio.totalPnL >= 0 ? '+' : ''} ${Math.abs(portfolio.totalPnL).toFixed(2)}
            </span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">
            <PieIcon size={24} />
          </div>
          <div className="summary-content">
            <span className="summary-label">P&L Percentage</span>
            <span className={`summary-value ${portfolio.pnlPercentage >= 0 ? 'profit' : 'loss'}`}>
              {portfolio.pnlPercentage >= 0 ? '+' : ''} {portfolio.pnlPercentage.toFixed(2)}%
            </span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">
            <DollarSign size={24} />
          </div>
          <div className="summary-content">
            <span className="summary-label">Available Balance</span>
            <span className="summary-value">${(portfolio.cashBalance || 0).toLocaleString()}</span>
          </div>
        </div>
        
        <div className="summary-card">
          <div className="summary-icon">
            <Lock size={24} />
          </div>
          <div className="summary-content">
            <span className="summary-label">Blocked Balance</span>
            <span className="summary-value">${(portfolio.blockedBalance || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>

      <div className="portfolio-content">
        <div className="allocation-chart">
          <h3>Asset Allocation</h3>
          {portfolio.allocations.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={portfolio.allocations}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percentage }) => `${name} ${percentage}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {portfolio.allocations.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-data">No allocations to display</div>
          )}
        </div>

        <div className="portfolio-details">
          <div className="details-tabs">
            <button
              className={`tab ${activeTab === 'positions' ? 'active' : ''}`}
              onClick={() => setActiveTab('positions')}
            >
              Positions ({portfolio.positions.length})
            </button>
            <button
              className={`tab ${activeTab === 'transactions' ? 'active' : ''}`}
              onClick={() => setActiveTab('transactions')}
            >
              Transactions ({transactions.length})
            </button>
          </div>

          <div className="details-content">
            {activeTab === 'positions' && (
              <div className="positions-list">
                {portfolio.positions.length > 0 ? (
                  <table className="positions-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Avg Price</th>
                        <th>Current Price</th>
                        <th>Value</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.positions.map(position => (
                        <tr key={position.symbol}>
                          <td className="symbol">{position.symbol}</td>
                          <td>{position.quantity}</td>
                          <td>${position.average_price.toFixed(2)}</td>
                          <td>${position.current_price.toFixed(2)}</td>
                          <td>${(position.quantity * position.current_price).toFixed(2)}</td>
                          <td className={position.unrealized_pnl >= 0 ? 'profit' : 'loss'}>
                            {position.unrealized_pnl >= 0 ? '+' : ''}
                            ${Math.abs(position.unrealized_pnl).toFixed(2)}
                          </td>
                          <td className={position.pnl_percentage >= 0 ? 'profit' : 'loss'}>
                            {position.pnl_percentage >= 0 ? '+' : ''}
                            {position.pnl_percentage.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="no-data">No positions yet</div>
                )}
              </div>
            )}

            {activeTab === 'transactions' && (
              <div className="transactions-list">
                {transactions.length > 0 ? (
                  <table className="transactions-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Symbol</th>
                        <th>Type</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx, index) => (
                        <tr key={index}>
                          <td>{new Date(tx.timestamp).toLocaleDateString()}</td>
                          <td className="symbol">{tx.symbol}</td>
                          <td>
                            <span className={`side ${tx.side?.toLowerCase()}`}>
                              {tx.side}
                            </span>
                          </td>
                          <td>{tx.quantity}</td>
                          <td>${tx.price}</td>
                          <td>${(tx.quantity * tx.price).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="no-data">No transactions yet</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Portfolio;