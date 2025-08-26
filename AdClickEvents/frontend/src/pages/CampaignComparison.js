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
  RadialBarChart,
  RadialBar,
  ScatterChart,
  Scatter
} from 'recharts';
import { Target, TrendingUp, DollarSign, Users, Play, Pause, Settings } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const CampaignContainer = styled.div`
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

const CampaignGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
`;

const CampaignCard = styled.div`
  background: white;
  border-radius: 12px;
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
    background: ${props => 
      props.status === 'active' ? '#10b981' : 
      props.status === 'paused' ? '#f59e0b' : '#64748b'
    };
  }
`;

const CampaignHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
`;

const CampaignInfo = styled.div`
  h3 {
    font-size: 18px;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 4px 0;
  }
  
  p {
    font-size: 14px;
    color: #64748b;
    margin: 0;
  }
`;

const StatusBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  text-transform: capitalize;
  
  ${props => {
    switch(props.status) {
      case 'active':
        return `
          background-color: #dcfce7;
          color: #16a34a;
        `;
      case 'paused':
        return `
          background-color: #fef3c7;
          color: #d97706;
        `;
      case 'completed':
        return `
          background-color: #e2e8f0;
          color: #64748b;
        `;
      default:
        return `
          background-color: #f1f5f9;
          color: #64748b;
        `;
    }
  }}
`;

const MetricsGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 20px 0;
`;

const Metric = styled.div`
  text-align: center;
  
  .value {
    font-size: 20px;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 4px;
  }
  
  .label {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
  }
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 8px;
  background-color: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
  margin: 16px 0;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #06b6d4);
  width: ${props => props.percentage}%;
  border-radius: 4px;
  transition: width 0.3s ease;
`;

const Actions = styled.div`
  display: flex;
  gap: 8px;
  margin-top: 20px;
`;

const ActionButton = styled.button`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #f9fafb;
    border-color: #3b82f6;
  }
`;

const ChartSection = styled.div`
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

const ComparisonTable = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  overflow-x: auto;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  
  th, td {
    text-align: left;
    padding: 12px;
    border-bottom: 1px solid #e2e8f0;
  }
  
  th {
    font-weight: 600;
    color: #1e293b;
    background-color: #f8fafc;
  }
  
  tr:hover {
    background-color: #f9fafb;
  }
`;

const CampaignComparison = () => {
  const [campaigns, setCampaigns] = useState(null);
  const [loading, setLoading] = useState(true);
  const { get } = useApi();

  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        const data = await get('/api/campaigns/comparison', { silent: true });
        setCampaigns(data);
      } catch (error) {
        console.error('Failed to fetch campaigns:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCampaigns();
    const interval = setInterval(fetchCampaigns, 30000);

    return () => clearInterval(interval);
  }, [get]);

  if (loading) {
    return <div>Loading campaign data...</div>;
  }

  if (!campaigns?.campaigns) {
    return <div>Unable to load campaign data</div>;
  }

  // Prepare data for charts
  const chartData = campaigns.campaigns.map(campaign => ({
    name: campaign.name.slice(0, 10) + '...',
    clicks: campaign.clicks,
    conversions: campaign.conversions,
    spent: campaign.spent,
    roi: campaign.conversion_rate
  }));

  const roiData = campaigns.campaigns.map((campaign, index) => ({
    name: campaign.name,
    roi: campaign.conversion_rate,
    spent: campaign.spent,
    fill: ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b'][index % 4]
  }));

  return (
    <CampaignContainer>
      <Header>
        <Title>Campaign Comparison</Title>
        <div style={{ display: 'flex', gap: '12px' }}>
          <ActionButton>
            <Target size={16} />
            Create Campaign
          </ActionButton>
          <ActionButton>
            <Settings size={16} />
            Bulk Actions
          </ActionButton>
        </div>
      </Header>

      <CampaignGrid>
        {campaigns.campaigns.map((campaign) => (
          <CampaignCard key={campaign.campaign_id} status={campaign.status}>
            <CampaignHeader>
              <CampaignInfo>
                <h3>{campaign.name}</h3>
                <p>ID: {campaign.campaign_id}</p>
              </CampaignInfo>
              <StatusBadge status={campaign.status}>
                {campaign.status === 'active' && <Play size={12} />}
                {campaign.status === 'paused' && <Pause size={12} />}
                {campaign.status}
              </StatusBadge>
            </CampaignHeader>

            <MetricsGrid>
              <Metric>
                <div className="value">{campaign.clicks.toLocaleString()}</div>
                <div className="label">Clicks</div>
              </Metric>
              <Metric>
                <div className="value">{campaign.conversions}</div>
                <div className="label">Conversions</div>
              </Metric>
              <Metric>
                <div className="value">${campaign.spent.toLocaleString()}</div>
                <div className="label">Spent</div>
              </Metric>
              <Metric>
                <div className="value">{campaign.conversion_rate}%</div>
                <div className="label">Conv. Rate</div>
              </Metric>
            </MetricsGrid>

            <div style={{ marginBottom: '8px', fontSize: '14px', color: '#64748b' }}>
              Budget Usage: {Math.round((campaign.spent / campaign.budget) * 100)}%
            </div>
            <ProgressBar>
              <ProgressFill percentage={(campaign.spent / campaign.budget) * 100} />
            </ProgressBar>

            <Actions>
              <ActionButton>
                <TrendingUp size={14} />
                Optimize
              </ActionButton>
              <ActionButton>
                <DollarSign size={14} />
                Adjust Bid
              </ActionButton>
              <ActionButton>
                <Users size={14} />
                Audience
              </ActionButton>
            </Actions>
          </CampaignCard>
        ))}
      </CampaignGrid>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <ChartSection>
          <ChartTitle>Performance Comparison</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="clicks" fill="#3b82f6" name="Clicks" />
              <Bar dataKey="conversions" fill="#10b981" name="Conversions" />
            </BarChart>
          </ResponsiveContainer>
        </ChartSection>

        <ChartSection>
          <ChartTitle>ROI vs Spend Analysis</ChartTitle>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart data={campaigns.campaigns}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="spent" name="Spent ($)" />
              <YAxis dataKey="conversion_rate" name="ROI (%)" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter dataKey="conversion_rate" fill="#3b82f6" />
            </ScatterChart>
          </ResponsiveContainer>
        </ChartSection>
      </div>

      <ComparisonTable>
        <ChartTitle>Detailed Campaign Metrics</ChartTitle>
        <Table>
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Status</th>
              <th>Budget</th>
              <th>Spent</th>
              <th>Clicks</th>
              <th>Conversions</th>
              <th>Conv. Rate</th>
              <th>CPC</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.campaigns.map((campaign) => (
              <tr key={campaign.campaign_id}>
                <td>
                  <strong>{campaign.name}</strong><br />
                  <small style={{ color: '#64748b' }}>{campaign.campaign_id}</small>
                </td>
                <td>
                  <StatusBadge status={campaign.status}>
                    {campaign.status}
                  </StatusBadge>
                </td>
                <td>${campaign.budget.toLocaleString()}</td>
                <td>${campaign.spent.toLocaleString()}</td>
                <td>{campaign.clicks.toLocaleString()}</td>
                <td>{campaign.conversions}</td>
                <td>{campaign.conversion_rate}%</td>
                <td>${campaign.cpc}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </ComparisonTable>
    </CampaignContainer>
  );
};

export default CampaignComparison;