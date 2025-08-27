import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import api from '../services/api';
import './RiskManagement.css';

const RiskManagement = () => {
  const [riskMetrics, setRiskMetrics] = useState({
    exposureLimit: 100000,
    currentExposure: 0,
    dailyLossLimit: 5000,
    currentDailyLoss: 0,
    positionLimits: [],
    violations: []
  });

  useEffect(() => {
    fetchRiskData();
    const interval = setInterval(fetchRiskData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchRiskData = async () => {
    try {
      const [positionsRes, ordersRes] = await Promise.all([
        api.get('/reports/positions'),
        api.get('/v1/orders')
      ]);

      const positions = positionsRes.data.positions || [];
      const orders = ordersRes.data || [];

      const exposure = positions.reduce((sum, p) => 
        sum + (p.quantity * p.current_price), 0
      );

      const dailyLoss = positions.reduce((sum, p) => 
        sum + Math.min(0, p.unrealized_pnl), 0
      );

      const violations = checkViolations(exposure, dailyLoss, positions);

      setRiskMetrics({
        exposureLimit: 100000,
        currentExposure: exposure,
        dailyLossLimit: 5000,
        currentDailyLoss: Math.abs(dailyLoss),
        positionLimits: calculatePositionLimits(positions),
        violations
      });
    } catch (error) {
      console.error('Failed to fetch risk data:', error);
    }
  };

  const checkViolations = (exposure, dailyLoss, positions) => {
    const violations = [];
    
    if (exposure > 100000) {
      violations.push({
        type: 'EXPOSURE',
        severity: 'HIGH',
        message: 'Total exposure exceeds limit'
      });
    }
    
    if (Math.abs(dailyLoss) > 5000) {
      violations.push({
        type: 'DAILY_LOSS',
        severity: 'HIGH',
        message: 'Daily loss limit exceeded'
      });
    }
    
    positions.forEach(p => {
      if (p.quantity * p.current_price > 20000) {
        violations.push({
          type: 'POSITION_SIZE',
          severity: 'MEDIUM',
          message: `Position size too large for ${p.symbol}`
        });
      }
    });
    
    return violations;
  };

  const calculatePositionLimits = (positions) => {
    return positions.map(p => ({
      symbol: p.symbol,
      currentSize: p.quantity * p.current_price,
      limit: 20000,
      usage: ((p.quantity * p.current_price) / 20000) * 100
    }));
  };

  const getSeverityIcon = (severity) => {
    switch(severity) {
      case 'HIGH': return <XCircle size={16} />;
      case 'MEDIUM': return <AlertTriangle size={16} />;
      default: return <CheckCircle size={16} />;
    }
  };

  return (
    <div className="risk-management">
      <div className="risk-header">
        <h1>Risk Management</h1>
        <p>Monitor and control trading risks in real-time</p>
      </div>

      <div className="risk-overview">
        <div className="risk-card">
          <div className="risk-card-header">
            <Shield size={20} />
            <span>Exposure Management</span>
          </div>
          <div className="risk-metric">
            <div className="metric-label">Current Exposure</div>
            <div className="metric-value">${riskMetrics.currentExposure.toLocaleString()}</div>
            <div className="metric-progress">
              <div 
                className="progress-bar"
                style={{ 
                  width: `${(riskMetrics.currentExposure / riskMetrics.exposureLimit) * 100}%`,
                  background: riskMetrics.currentExposure > riskMetrics.exposureLimit ? '#ef4444' : '#10b981'
                }}
              />
            </div>
            <div className="metric-limit">Limit: ${riskMetrics.exposureLimit.toLocaleString()}</div>
          </div>
        </div>

        <div className="risk-card">
          <div className="risk-card-header">
            <AlertTriangle size={20} />
            <span>Daily Loss Limit</span>
          </div>
          <div className="risk-metric">
            <div className="metric-label">Current Daily Loss</div>
            <div className="metric-value">${riskMetrics.currentDailyLoss.toLocaleString()}</div>
            <div className="metric-progress">
              <div 
                className="progress-bar"
                style={{ 
                  width: `${(riskMetrics.currentDailyLoss / riskMetrics.dailyLossLimit) * 100}%`,
                  background: riskMetrics.currentDailyLoss > riskMetrics.dailyLossLimit ? '#ef4444' : '#f59e0b'
                }}
              />
            </div>
            <div className="metric-limit">Limit: ${riskMetrics.dailyLossLimit.toLocaleString()}</div>
          </div>
        </div>
      </div>

      <div className="risk-details">
        <div className="violations-section">
          <h3>Risk Violations</h3>
          {riskMetrics.violations.length > 0 ? (
            <div className="violations-list">
              {riskMetrics.violations.map((violation, index) => (
                <div key={index} className={`violation-item ${violation.severity.toLowerCase()}`}>
                  {getSeverityIcon(violation.severity)}
                  <div className="violation-content">
                    <span className="violation-type">{violation.type}</span>
                    <span className="violation-message">{violation.message}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-violations">
              <CheckCircle size={24} />
              <span>No risk violations detected</span>
            </div>
          )}
        </div>

        <div className="position-limits-section">
          <h3>Position Limits</h3>
          {riskMetrics.positionLimits.length > 0 ? (
            <div className="limits-list">
              {riskMetrics.positionLimits.map((limit, index) => (
                <div key={index} className="limit-item">
                  <div className="limit-header">
                    <span className="limit-symbol">{limit.symbol}</span>
                    <span className="limit-usage">{limit.usage.toFixed(1)}%</span>
                  </div>
                  <div className="limit-progress">
                    <div 
                      className="progress-bar"
                      style={{ 
                        width: `${limit.usage}%`,
                        background: limit.usage > 100 ? '#ef4444' : 
                                   limit.usage > 75 ? '#f59e0b' : '#10b981'
                      }}
                    />
                  </div>
                  <div className="limit-values">
                    <span>${limit.currentSize.toFixed(0)} / ${limit.limit.toFixed(0)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-data">No positions to monitor</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RiskManagement;