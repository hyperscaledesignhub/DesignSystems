import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar
} from 'recharts';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Eye, 
  Ban,
  TrendingUp,
  MapPin,
  Monitor
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { format } from 'date-fns';

const FraudContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const Title = styled.h1`
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
`;

const StatCard = styled.div`
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: ${props => props.color || '#3b82f6'};
  }
`;

const StatHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
`;

const StatTitle = styled.h3`
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  margin: 0;
`;

const StatValue = styled.div`
  font-size: 32px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
`;

const StatChange = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  font-weight: 500;
  color: ${props => props.positive ? '#16a34a' : '#dc2626'};
`;

const AlertsSection = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
`;

const SectionTitle = styled.h3`
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const AlertsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

const AlertItem = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 8px;
  background: ${props => {
    switch(props.severity) {
      case 'high': return '#fef2f2';
      case 'medium': return '#fffbeb';
      case 'low': return '#f0f9ff';
      default: return '#f8fafc';
    }
  }};
  border: 1px solid ${props => {
    switch(props.severity) {
      case 'high': return '#fecaca';
      case 'medium': return '#fed7aa';
      case 'low': return '#bfdbfe';
      default: return '#e2e8f0';
    }
  }};
`;

const AlertIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: ${props => {
    switch(props.severity) {
      case 'high': return '#dc2626';
      case 'medium': return '#d97706';
      case 'low': return '#2563eb';
      default: return '#64748b';
    }
  }};
  color: white;
`;

const AlertContent = styled.div`
  flex: 1;
  
  .alert-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
  }
  
  .alert-title {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 4px 0;
  }
  
  .alert-meta {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 8px;
  }
  
  .alert-description {
    font-size: 14px;
    color: #374151;
    line-height: 1.5;
  }
`;

const SeverityBadge = styled.div`
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  
  ${props => {
    switch(props.severity) {
      case 'high':
        return `
          background-color: #fee2e2;
          color: #dc2626;
        `;
      case 'medium':
        return `
          background-color: #fef3c7;
          color: #d97706;
        `;
      case 'low':
        return `
          background-color: #dbeafe;
          color: #2563eb;
        `;
      default:
        return `
          background-color: #f1f5f9;
          color: #64748b;
        `;
    }
  }}
`;

const StatusBadge = styled.div`
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-transform: capitalize;
  
  ${props => {
    switch(props.status) {
      case 'new':
        return `
          background-color: #fef3c7;
          color: #d97706;
        `;
      case 'investigating':
        return `
          background-color: #dbeafe;
          color: #2563eb;
        `;
      case 'resolved':
        return `
          background-color: #dcfce7;
          color: #16a34a;
        `;
      default:
        return `
          background-color: #f1f5f9;
          color: #64748b;
        `;
    }
  }}
`;

const ChartSection = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  
  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
`;

const ChartCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
`;

const ChartTitle = styled.h3`
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 20px 0;
`;

const FraudDetection = () => {
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const { get } = useApi();

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await get('/api/fraud/alerts', { silent: true });
        setAlerts(data);
      } catch (error) {
        console.error('Failed to fetch fraud alerts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000); // Refresh every 15 seconds

    return () => clearInterval(interval);
  }, [get]);

  if (loading) {
    return <div>Loading fraud detection data...</div>;
  }

  if (!alerts) {
    return <div>Unable to load fraud detection data</div>;
  }

  // Generate mock data for charts
  const fraudTrendData = [];
  for (let i = 23; i >= 0; i--) {
    fraudTrendData.push({
      hour: `${(new Date().getHours() - i + 24) % 24}:00`,
      fraudulent: Math.floor(Math.random() * 50) + 10,
      legitimate: Math.floor(Math.random() * 1000) + 200,
      fraudRate: Math.random() * 8 + 2
    });
  }

  const fraudTypeData = [
    { name: 'IP Anomaly', count: 45, percentage: 35 },
    { name: 'Click Pattern', count: 32, percentage: 25 },
    { name: 'Geographic', count: 28, percentage: 22 },
    { name: 'Bot Detection', count: 23, percentage: 18 }
  ];

  const severityStats = {
    high: alerts.alerts?.filter(a => a.severity === 'high').length || 0,
    medium: alerts.alerts?.filter(a => a.severity === 'medium').length || 0,
    low: alerts.alerts?.filter(a => a.severity === 'low').length || 0,
    total: alerts.alerts?.length || 0
  };

  const getAlertIcon = (type) => {
    switch(type) {
      case 'ip_anomaly': return <MapPin size={20} />;
      case 'click_pattern': return <TrendingUp size={20} />;
      case 'geographic': return <MapPin size={20} />;
      case 'bot_detection': return <Monitor size={20} />;
      default: return <AlertTriangle size={20} />;
    }
  };

  return (
    <FraudContainer>
      <Header>
        <Title>Fraud Detection</Title>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            padding: '8px 16px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            background: 'white',
            cursor: 'pointer'
          }}>
            <Eye size={16} />
            View All
          </button>
          <button style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            border: '1px solid #dc2626',
            borderRadius: '6px',
            background: '#dc2626',
            color: 'white',
            cursor: 'pointer'
          }}>
            <Ban size={16} />
            Block IPs
          </button>
        </div>
      </Header>

      <StatsGrid>
        <StatCard color="#dc2626">
          <StatHeader>
            <StatTitle>High Risk Alerts</StatTitle>
            <Shield size={20} color="#dc2626" />
          </StatHeader>
          <StatValue>{severityStats.high}</StatValue>
          <StatChange positive={false}>
            <TrendingUp size={16} />
            +2 from yesterday
          </StatChange>
        </StatCard>

        <StatCard color="#d97706">
          <StatHeader>
            <StatTitle>Medium Risk Alerts</StatTitle>
            <AlertTriangle size={20} color="#d97706" />
          </StatHeader>
          <StatValue>{severityStats.medium}</StatValue>
          <StatChange positive>
            <TrendingUp size={16} />
            -1 from yesterday
          </StatChange>
        </StatCard>

        <StatCard color="#16a34a">
          <StatHeader>
            <StatTitle>Resolved Today</StatTitle>
            <CheckCircle size={20} color="#16a34a" />
          </StatHeader>
          <StatValue>{alerts.alerts?.filter(a => a.status === 'resolved').length || 0}</StatValue>
          <StatChange positive>
            <TrendingUp size={16} />
            +5 from yesterday
          </StatChange>
        </StatCard>

        <StatCard color="#3b82f6">
          <StatHeader>
            <StatTitle>Total Alerts</StatTitle>
            <Clock size={20} color="#3b82f6" />
          </StatHeader>
          <StatValue>{severityStats.total}</StatValue>
          <StatChange positive>
            <TrendingUp size={16} />
            Processing rate: 95%
          </StatChange>
        </StatCard>
      </StatsGrid>

      <ChartSection>
        <ChartCard>
          <ChartTitle>Fraud Detection Trends (24h)</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={fraudTrendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="fraudulent" 
                stackId="1"
                stroke="#dc2626" 
                fill="#dc2626" 
                fillOpacity={0.6}
                name="Fraudulent Clicks"
              />
              <Area 
                type="monotone" 
                dataKey="legitimate" 
                stackId="1"
                stroke="#16a34a" 
                fill="#16a34a" 
                fillOpacity={0.6}
                name="Legitimate Clicks"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard>
          <ChartTitle>Fraud Types Distribution</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={fraudTypeData} layout="horizontal">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={80} />
              <Tooltip />
              <Bar dataKey="count" fill="#dc2626" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </ChartSection>

      <AlertsSection>
        <SectionTitle>
          <AlertTriangle size={20} />
          Recent Fraud Alerts
        </SectionTitle>
        <AlertsList>
          {alerts.alerts && alerts.alerts.length > 0 ? (
            alerts.alerts.slice(0, 10).map((alert) => (
              <AlertItem key={alert.id} severity={alert.severity}>
                <AlertIcon severity={alert.severity}>
                  {getAlertIcon(alert.type)}
                </AlertIcon>
                <AlertContent>
                  <div className="alert-header">
                    <div>
                      <h4 className="alert-title">
                        {alert.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} Alert
                      </h4>
                      <div className="alert-meta">
                        Ad ID: {alert.ad_id} • 
                        {' ' + format(new Date(alert.timestamp * 1000), 'MMM dd, HH:mm')}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <SeverityBadge severity={alert.severity}>
                        {alert.severity}
                      </SeverityBadge>
                      <StatusBadge status={alert.status}>
                        {alert.status}
                      </StatusBadge>
                    </div>
                  </div>
                  <p className="alert-description">
                    {alert.description}
                  </p>
                </AlertContent>
              </AlertItem>
            ))
          ) : (
            <div style={{ 
              textAlign: 'center', 
              padding: '40px', 
              color: '#64748b',
              fontSize: '16px'
            }}>
              <CheckCircle size={48} style={{ margin: '0 auto 16px', display: 'block' }} />
              No fraud alerts detected. Your system is secure.
            </div>
          )}
        </AlertsList>
      </AlertsSection>
    </FraudContainer>
  );
};

export default FraudDetection;