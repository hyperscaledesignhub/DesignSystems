import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';
import { TrendingUp, MousePointer, DollarSign, Users, Globe, Shield } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const DashboardContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const MetricsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
`;

const MetricCard = styled.div`
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
`;

const MetricHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
`;

const MetricTitle = styled.h3`
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  margin: 0;
`;

const MetricValue = styled.div`
  font-size: 32px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
`;

const MetricChange = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  font-weight: 500;
  
  ${props => props.positive ? `
    color: #16a34a;
  ` : `
    color: #dc2626;
  `}
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
  border-radius: 8px;
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

const TopAdsSection = styled.div`
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
`;

const AdItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
  
  &:last-child {
    border-bottom: none;
  }
`;

const AdInfo = styled.div`
  h4 {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 4px 0;
  }
  
  p {
    font-size: 12px;
    color: #64748b;
    margin: 0;
  }
`;

const AdMetric = styled.div`
  text-align: right;
  
  .value {
    font-size: 16px;
    font-weight: 700;
    color: #1e293b;
  }
  
  .label {
    font-size: 12px;
    color: #64748b;
  }
`;

const COLORS = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];

const Dashboard = ({ realtimeData, simulationActive }) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const { get } = useApi();

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await get('/api/metrics/realtime', { silent: true });
        setMetrics(data);
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, [get]);

  if (loading) {
    return <div>Loading dashboard...</div>;
  }

  if (!metrics) {
    return <div>Unable to load dashboard data</div>;
  }

  // Prepare chart data
  const countryData = Object.entries(metrics.country_distribution || {}).map(([country, data]) => ({
    name: country,
    clicks: data.clicks,
    percentage: data.percentage
  }));

  // Mock hourly data for trend chart
  const hourlyData = [];
  for (let i = 23; i >= 0; i--) {
    hourlyData.push({
      hour: `${(new Date().getHours() - i + 24) % 24}:00`,
      clicks: Math.floor(Math.random() * 1000) + 200
    });
  }

  return (
    <DashboardContainer>
      <MetricsGrid>
        <MetricCard>
          <MetricHeader>
            <MetricTitle>Total Clicks</MetricTitle>
            <MousePointer size={20} color="#3b82f6" />
          </MetricHeader>
          <MetricValue>
            {metrics.total_clicks?.toLocaleString() || '0'}
          </MetricValue>
          <MetricChange positive>
            <TrendingUp size={16} />
            +{metrics.clicks_per_second || 0}/sec
          </MetricChange>
        </MetricCard>

        <MetricCard>
          <MetricHeader>
            <MetricTitle>Revenue/Hour</MetricTitle>
            <DollarSign size={20} color="#10b981" />
          </MetricHeader>
          <MetricValue>
            ${metrics.revenue_per_hour?.toLocaleString() || '0'}
          </MetricValue>
          <MetricChange positive>
            <TrendingUp size={16} />
            +12.5%
          </MetricChange>
        </MetricCard>

        <MetricCard>
          <MetricHeader>
            <MetricTitle>Active Campaigns</MetricTitle>
            <Users size={20} color="#f59e0b" />
          </MetricHeader>
          <MetricValue>
            {metrics.active_campaigns || 0}
          </MetricValue>
          <MetricChange positive>
            <TrendingUp size={16} />
            +2 today
          </MetricChange>
        </MetricCard>

        <MetricCard>
          <MetricHeader>
            <MetricTitle>Fraud Rate</MetricTitle>
            <Shield size={20} color="#ef4444" />
          </MetricHeader>
          <MetricValue>
            {metrics.fraud_rate?.toFixed(1) || '0.0'}%
          </MetricValue>
          <MetricChange positive={metrics.fraud_rate < 5}>
            <TrendingUp size={16} />
            {metrics.fraud_rate < 5 ? 'Normal' : 'Alert'}
          </MetricChange>
        </MetricCard>
      </MetricsGrid>

      <ChartSection>
        <ChartCard>
          <ChartTitle>Clicks Over Time (24h)</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="clicks" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard>
          <ChartTitle>Geographic Distribution</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={countryData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percentage }) => `${name} ${percentage}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="clicks"
              >
                {countryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </ChartSection>

      <TopAdsSection>
        <ChartTitle>Top Performing Ads</ChartTitle>
        {metrics.top_ads?.map((ad, index) => (
          <AdItem key={ad.ad_id}>
            <AdInfo>
              <h4>#{index + 1} {ad.name}</h4>
              <p>ID: {ad.ad_id}</p>
            </AdInfo>
            <AdMetric>
              <div className="value">{ad.clicks.toLocaleString()}</div>
              <div className="label">clicks</div>
            </AdMetric>
          </AdItem>
        )) || (
          <div>No ad data available</div>
        )}
      </TopAdsSection>
    </DashboardContainer>
  );
};

export default Dashboard;