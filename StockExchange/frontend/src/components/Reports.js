import React, { useState, useEffect } from 'react';
import { FileText, Download, Calendar, Filter } from 'lucide-react';
import api from '../services/api';
import './Reports.css';

const Reports = () => {
  const [reportType, setReportType] = useState('trades');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const today = new Date();
    const lastWeek = new Date(today - 7 * 24 * 60 * 60 * 1000);
    setDateRange({
      start: lastWeek.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0]
    });
  }, []);

  const generateReport = async () => {
    setLoading(true);
    try {
      let data;
      switch(reportType) {
        case 'trades':
          const tradesRes = await api.get('/reports/trades?limit=100');
          data = tradesRes.data;
          break;
        case 'positions':
          const positionsRes = await api.get('/reports/positions');
          data = positionsRes.data;
          break;
        case 'pnl':
          const pnlRes = await api.get('/reports/pnl');
          data = pnlRes.data;
          break;
        case 'orders':
          const ordersRes = await api.get('/v1/orders');
          data = { orders: ordersRes.data };
          break;
        default:
          data = {};
      }
      setReportData(data);
    } catch (error) {
      console.error('Failed to generate report:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = () => {
    if (!reportData) return;
    
    const dataStr = JSON.stringify(reportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `report_${reportType}_${new Date().toISOString()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const renderReportContent = () => {
    if (!reportData) return null;

    switch(reportType) {
      case 'trades':
        return (
          <div className="report-content">
            <h3>Trade Report</h3>
            {reportData.trades && reportData.trades.length > 0 ? (
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.trades.map((trade, index) => (
                    <tr key={index}>
                      <td>{new Date(trade.timestamp).toLocaleString()}</td>
                      <td>{trade.symbol}</td>
                      <td className={trade.side?.toLowerCase()}>{trade.side}</td>
                      <td>{trade.quantity}</td>
                      <td>${trade.price}</td>
                      <td>${(trade.quantity * trade.price).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="no-data">No trades found</p>
            )}
          </div>
        );
      
      case 'positions':
        return (
          <div className="report-content">
            <h3>Position Report</h3>
            {reportData.positions && reportData.positions.length > 0 ? (
              <table className="report-table">
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
                  {reportData.positions.map((position, index) => (
                    <tr key={index}>
                      <td>{position.symbol}</td>
                      <td>{position.quantity}</td>
                      <td>${position.average_price.toFixed(2)}</td>
                      <td>${position.current_price.toFixed(2)}</td>
                      <td className={position.unrealized_pnl >= 0 ? 'profit' : 'loss'}>
                        ${position.unrealized_pnl.toFixed(2)}
                      </td>
                      <td className={position.pnl_percentage >= 0 ? 'profit' : 'loss'}>
                        {position.pnl_percentage.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="no-data">No positions found</p>
            )}
          </div>
        );
      
      case 'orders':
        return (
          <div className="report-content">
            <h3>Orders Report</h3>
            {reportData.orders && reportData.orders.length > 0 ? (
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.orders.map((order, index) => (
                    <tr key={index}>
                      <td>{new Date(order.created_at).toLocaleString()}</td>
                      <td>{order.symbol}</td>
                      <td className={order.side?.toLowerCase()}>{order.side}</td>
                      <td>{order.quantity}</td>
                      <td>${order.price}</td>
                      <td>
                        <span className={`status ${order.status?.toLowerCase()}`}>
                          {order.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="no-data">No orders found</p>
            )}
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="reports">
      <div className="reports-header">
        <h1>Reports & Analytics</h1>
        <p>Generate comprehensive trading reports and analytics</p>
      </div>

      <div className="report-controls">
        <div className="control-group">
          <label>Report Type</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
            <option value="trades">Trade Report</option>
            <option value="positions">Position Report</option>
            <option value="pnl">P&L Report</option>
            <option value="orders">Orders Report</option>
          </select>
        </div>

        <div className="control-group">
          <label>Start Date</label>
          <input 
            type="date" 
            value={dateRange.start}
            onChange={(e) => setDateRange({...dateRange, start: e.target.value})}
          />
        </div>

        <div className="control-group">
          <label>End Date</label>
          <input 
            type="date" 
            value={dateRange.end}
            onChange={(e) => setDateRange({...dateRange, end: e.target.value})}
          />
        </div>

        <button onClick={generateReport} className="btn-generate" disabled={loading}>
          <FileText size={18} />
          {loading ? 'Generating...' : 'Generate Report'}
        </button>

        {reportData && (
          <button onClick={downloadReport} className="btn-download">
            <Download size={18} />
            Download
          </button>
        )}
      </div>

      <div className="report-display">
        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Generating report...</p>
          </div>
        ) : reportData ? (
          renderReportContent()
        ) : (
          <div className="no-report">
            <FileText size={48} />
            <p>Select report parameters and click Generate Report</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Reports;