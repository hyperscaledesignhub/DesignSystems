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
  BarChart,
  Bar
} from 'recharts';
import { 
  Activity, 
  Server, 
  Database, 
  Cpu, 
  MemoryStick, 
  HardDrive, 
  Wifi,
  CheckCircle,
  AlertTriangle,
  XCircle
} from 'lucide-react';
import { useApi } from '../hooks/useApi';

const HealthContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const Title = styled.h1`
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
`;

const ServiceGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
`;

const ServiceCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: ${props => 
      props.status === 'healthy' ? '#10b981' : 
      props.status === 'warning' ? '#f59e0b' : '#ef4444'
    };
  }
`;

const ServiceHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
`;

const ServiceInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
    margin: 0;
  }
  
  p {
    font-size: 12px;
    color: #64748b;
    margin: 0;
  }
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  
  ${props => {
    switch(props.status) {
      case 'healthy':
        return `
          background-color: #dcfce7;
          color: #16a34a;
        `;
      case 'warning':
        return `
          background-color: #fef3c7;
          color: #d97706;
        `;
      case 'error':
        return `
          background-color: #fee2e2;
          color: #dc2626;
        `;
      default:
        return `
          background-color: #f1f5f9;
          color: #64748b;
        `;
    }
  }}
`;

const MetricRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0;
  
  .label {
    font-size: 14px;
    color: #64748b;
  }
  
  .value {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
  }
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 6px;
  background-color: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
  margin: 8px 0;
`;

const ProgressFill = styled.div`
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
  width: ${props => props.percentage}%;
  background: ${props => {
    if (props.percentage > 80) return '#ef4444';
    if (props.percentage > 60) return '#f59e0b';
    return '#10b981';
  }};
`;

const ChartSection = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
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

const AlertsCard = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  grid-column: 1 / -1;
`;

const AlertItem = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  margin-bottom: 12px;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const getStatusIcon = (status) => {
  switch(status) {
    case 'healthy':
      return <CheckCircle size={16} />;
    case 'warning':
      return <AlertTriangle size={16} />;
    case 'error':
      return <XCircle size={16} />;
    default:
      return <AlertTriangle size={16} />;
  }
};

const SystemHealth = () => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { get } = useApi();

  useEffect(() => {
    const fetchHealthData = async () => {
      try {
        // Simulate getting system health data
        const mockData = {
          services: [
            {
              name: 'Query Service',
              type: 'api',
              status: 'healthy',
              uptime: '99.8%',
              responseTime: '45ms',
              cpu: 34,
              memory: 62,
              requests: 1250
            },
            {
              name: 'Aggregation Service',
              type: 'worker',
              status: 'healthy',
              uptime: '99.9%',
              responseTime: '12ms',
              cpu: 45,
              memory: 58,
              processed: 15420
            },
            {
              name: 'Database Writer',
              type: 'worker',
              status: 'warning',
              uptime: '98.5%',
              responseTime: '89ms',
              cpu: 78,
              memory: 85,
              writes: 890
            },
            {
              name: 'Kafka Cluster',
              type: 'message_queue',
              status: 'healthy',
              uptime: '99.9%',
              responseTime: '8ms',
              cpu: 23,
              memory: 41,
              throughput: 5420
            },
            {
              name: 'InfluxDB',
              type: 'database',
              status: 'healthy',
              uptime: '99.7%',
              responseTime: '23ms',
              cpu: 29,
              memory: 67,
              storage: 73
            },
            {
              name: 'Log Watcher',
              type: 'monitor',
              status: 'healthy',
              uptime: '99.6%',
              responseTime: '15ms',
              cpu: 12,
              memory: 28,
              files: 15
            }
          ],
          alerts: [
            {
              service: 'Database Writer',
              message: 'High memory usage detected (85%)',
              severity: 'warning',
              time: '2 minutes ago'
            },
            {
              service: 'InfluxDB',
              message: 'Storage usage approaching limit (73%)',
              severity: 'info',
              time: '15 minutes ago'
            }
          ]
        };
        
        setHealthData(mockData);
      } catch (error) {
        console.error('Failed to fetch health data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHealthData();
    const interval = setInterval(fetchHealthData, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [get]);

  if (loading) {
    return <div>Loading system health data...</div>;
  }

  if (!healthData) {
    return <div>Unable to load system health data</div>;
  }

  // Generate mock performance data
  const performanceData = [];
  for (let i = 29; i >= 0; i--) {
    performanceData.push({
      time: `${i}m ago`,
      cpu: Math.random() * 40 + 20,
      memory: Math.random() * 30 + 40,
      network: Math.random() * 100 + 50
    });
  }

  const throughputData = [];
  for (let i = 23; i >= 0; i--) {
    throughputData.push({
      hour: `${(new Date().getHours() - i + 24) % 24}:00`,
      requests: Math.floor(Math.random() * 2000) + 500,
      errors: Math.floor(Math.random() * 50) + 5
    });
  }

  const getServiceIcon = (type) => {
    switch(type) {
      case 'api': return <Server size={20} />;
      case 'worker': return <Cpu size={20} />;
      case 'database': return <Database size={20} />;
      case 'message_queue': return <Wifi size={20} />;
      case 'monitor': return <Activity size={20} />;
      default: return <Server size={20} />;
    }
  };

  return (
    <HealthContainer>
      <Title>System Health Monitor</Title>

      <ServiceGrid>
        {healthData.services.map((service, index) => (
          <ServiceCard key={index} status={service.status}>
            <ServiceHeader>
              <ServiceInfo>
                {getServiceIcon(service.type)}
                <div>
                  <h3>{service.name}</h3>
                  <p>Uptime: {service.uptime}</p>
                </div>
              </ServiceInfo>
              <StatusIndicator status={service.status}>
                {getStatusIcon(service.status)}
                {service.status}
              </StatusIndicator>
            </ServiceHeader>

            <MetricRow>
              <span className="label">Response Time</span>
              <span className="value">{service.responseTime}</span>
            </MetricRow>

            <MetricRow>
              <span className="label">CPU Usage</span>
              <span className="value">{service.cpu}%</span>
            </MetricRow>
            <ProgressBar>
              <ProgressFill percentage={service.cpu} />
            </ProgressBar>

            <MetricRow>
              <span className="label">Memory Usage</span>
              <span className="value">{service.memory}%</span>
            </MetricRow>
            <ProgressBar>
              <ProgressFill percentage={service.memory} />
            </ProgressBar>

            <MetricRow>
              <span className="label">
                {service.requests ? 'Requests/min' : 
                 service.processed ? 'Processed/min' : 
                 service.writes ? 'Writes/min' : 
                 service.throughput ? 'Throughput/min' : 
                 service.files ? 'Files Watched' : 'Activity'}
              </span>
              <span className="value">
                {service.requests || service.processed || service.writes || 
                 service.throughput || service.files || 'N/A'}
              </span>
            </MetricRow>
          </ServiceCard>
        ))}
      </ServiceGrid>

      <ChartSection>
        <ChartCard>
          <ChartTitle>System Performance (30min)</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="cpu" 
                stroke="#3b82f6" 
                strokeWidth={2}
                name="CPU %"
              />
              <Line 
                type="monotone" 
                dataKey="memory" 
                stroke="#10b981" 
                strokeWidth={2}
                name="Memory %"
              />
              <Line 
                type="monotone" 
                dataKey="network" 
                stroke="#f59e0b" 
                strokeWidth={2}
                name="Network MB/s"
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard>
          <ChartTitle>API Throughput & Errors (24h)</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={throughputData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="requests" fill="#3b82f6" name="Requests" />
              <Bar dataKey="errors" fill="#ef4444" name="Errors" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </ChartSection>

      {healthData.alerts && healthData.alerts.length > 0 && (
        <AlertsCard>
          <ChartTitle>System Alerts</ChartTitle>
          {healthData.alerts.map((alert, index) => (
            <AlertItem key={index}>
              <AlertTriangle size={20} color="#dc2626" />
              <div style={{ flex: 1 }}>
                <strong>{alert.service}:</strong> {alert.message}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>
                {alert.time}
              </div>
            </AlertItem>
          ))}
        </AlertsCard>
      )}
    </HealthContainer>
  );
};

export default SystemHealth;