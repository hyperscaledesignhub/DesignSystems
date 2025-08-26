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
  Bar,
  ComposedChart,
  Area,
  AreaChart
} from 'recharts';
import { TrendingUp, Calendar, Filter, Download } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const AnalyticsContainer = styled.div`
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

const Controls = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
`;

const FilterButton = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #f9fafb;
    border-color: #3b82f6;
  }
`;

const ChartGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
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

const FullWidthChart = styled(ChartCard)`
  grid-column: 1 / -1;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
`;

const StatCard = styled.div`
  background: #f8fafc;
  border-radius: 6px;
  padding: 16px;
  
  .label {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
    margin-bottom: 4px;
  }
  
  .value {
    font-size: 20px;
    font-weight: 700;
    color: #1e293b;
  }
`;

const Analytics = () => {
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');
  const { get } = useApi();

  useEffect(() => {
    const fetchTrends = async () => {
      try {
        const data = await get('/api/analytics/trends', { silent: true });
        setTrends(data);
      } catch (error) {
        console.error('Failed to fetch trends:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTrends();
    const interval = setInterval(fetchTrends, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [get, timeRange]);

  if (loading) {
    return <div>Loading analytics...</div>;
  }

  if (!trends) {
    return <div>Unable to load analytics data</div>;
  }

  // Prepare data for charts
  const combinedData = trends.hours?.map((hour, index) => ({
    time: hour,
    clicks: trends.clicks?.[index] || 0,
    revenue: trends.revenue?.[index] || 0,
    ctr: Math.random() * 5 + 2, // Mock CTR data
    cpc: Math.random() * 2 + 0.5 // Mock CPC data
  })) || [];

  // Performance metrics
  const performanceData = [
    { name: 'Morning (6-12)', clicks: 15420, revenue: 3200, ctr: 3.2, cpc: 1.24 },
    { name: 'Afternoon (12-18)', clicks: 18750, revenue: 4100, ctr: 3.8, cpc: 1.31 },
    { name: 'Evening (18-24)', clicks: 22340, revenue: 5200, ctr: 4.1, cpc: 1.28 },
    { name: 'Night (0-6)', clicks: 8920, revenue: 1800, ctr: 2.9, cpc: 1.15 }
  ];

  // Device breakdown
  const deviceData = [
    { name: 'Mobile', clicks: 32450, revenue: 7200, share: 68 },
    { name: 'Desktop', clicks: 12340, revenue: 4100, share: 26 },
    { name: 'Tablet', clicks: 2890, revenue: 890, share: 6 }
  ];

  const totalClicks = combinedData.reduce((sum, item) => sum + item.clicks, 0);
  const totalRevenue = combinedData.reduce((sum, item) => sum + item.revenue, 0);
  const avgCTR = (combinedData.reduce((sum, item) => sum + item.ctr, 0) / combinedData.length).toFixed(2);
  const avgCPC = (combinedData.reduce((sum, item) => sum + item.cpc, 0) / combinedData.length).toFixed(2);

  return (
    <AnalyticsContainer>
      <Header>
        <Title>Analytics & Trends</Title>
        <Controls>
          <FilterButton>
            <Calendar size={16} />
            {timeRange.toUpperCase()}
          </FilterButton>
          <FilterButton>
            <Filter size={16} />
            Filters
          </FilterButton>
          <FilterButton>
            <Download size={16} />
            Export
          </FilterButton>
        </Controls>
      </Header>

      <StatsGrid>
        <StatCard>
          <div className="label">Total Clicks</div>
          <div className="value">{totalClicks.toLocaleString()}</div>
        </StatCard>
        <StatCard>
          <div className="label">Total Revenue</div>
          <div className="value">${totalRevenue.toLocaleString()}</div>
        </StatCard>
        <StatCard>
          <div className="label">Average CTR</div>
          <div className="value">{avgCTR}%</div>
        </StatCard>
        <StatCard>
          <div className="label">Average CPC</div>
          <div className="value">${avgCPC}</div>
        </StatCard>
      </StatsGrid>

      <FullWidthChart>
        <ChartTitle>Clicks vs Revenue Trend</ChartTitle>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={combinedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Bar yAxisId="left" dataKey="clicks" fill="#3b82f6" name="Clicks" />
            <Line 
              yAxisId="right" 
              type="monotone" 
              dataKey="revenue" 
              stroke="#10b981" 
              strokeWidth={3}
              name="Revenue ($)"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </FullWidthChart>

      <ChartGrid>
        <ChartCard>
          <ChartTitle>Performance by Time of Day</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="clicks" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard>
          <ChartTitle>Click-Through Rate Trends</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={combinedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="ctr" 
                stroke="#06b6d4" 
                fill="#06b6d4" 
                fillOpacity={0.3}
                name="CTR (%)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard>
          <ChartTitle>Device Performance</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={deviceData} layout="horizontal">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" />
              <Tooltip />
              <Bar dataKey="revenue" fill="#10b981" name="Revenue ($)" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard>
          <ChartTitle>Cost Per Click Analysis</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={combinedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="cpc" 
                stroke="#f59e0b" 
                strokeWidth={2}
                dot={{ fill: '#f59e0b', strokeWidth: 2, r: 4 }}
                name="CPC ($)"
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </ChartGrid>
    </AnalyticsContainer>
  );
};

export default Analytics;