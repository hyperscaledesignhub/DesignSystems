import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { 
  Play, 
  Pause, 
  Square, 
  Settings, 
  Zap, 
  BarChart3, 
  Shield,
  Database,
  RefreshCw
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import toast from 'react-hot-toast';

const ControlsContainer = styled.div`
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

const Section = styled.div`
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

const ControlGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
`;

const ControlCard = styled.div`
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
  
  h4 {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 8px 0;
  }
  
  p {
    font-size: 12px;
    color: #64748b;
    margin: 0 0 12px 0;
  }
`;

const Button = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  border: 1px solid;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  
  ${props => {
    switch(props.variant) {
      case 'primary':
        return `
          background-color: #3b82f6;
          color: white;
          border-color: #3b82f6;
          
          &:hover:not(:disabled) {
            background-color: #2563eb;
          }
        `;
      case 'success':
        return `
          background-color: #16a34a;
          color: white;
          border-color: #16a34a;
          
          &:hover:not(:disabled) {
            background-color: #15803d;
          }
        `;
      case 'warning':
        return `
          background-color: #d97706;
          color: white;
          border-color: #d97706;
          
          &:hover:not(:disabled) {
            background-color: #b45309;
          }
        `;
      case 'danger':
        return `
          background-color: #dc2626;
          color: white;
          border-color: #dc2626;
          
          &:hover:not(:disabled) {
            background-color: #b91c1c;
          }
        `;
      default:
        return `
          background-color: white;
          color: #374151;
          border-color: #d1d5db;
          
          &:hover:not(:disabled) {
            background-color: #f9fafb;
            border-color: #3b82f6;
          }
        `;
    }
  }}
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const ScenarioSelector = styled.select`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const SpeedSlider = styled.div`
  margin: 16px 0;
  
  label {
    display: block;
    font-size: 14px;
    font-weight: 500;
    color: #374151;
    margin-bottom: 8px;
  }
  
  input[type="range"] {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #e2e8f0;
    outline: none;
    
    &::-webkit-slider-thumb {
      appearance: none;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #3b82f6;
      cursor: pointer;
    }
    
    &::-moz-range-thumb {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #3b82f6;
      cursor: pointer;
      border: none;
    }
  }
  
  .speed-labels {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #64748b;
    margin-top: 4px;
  }
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 16px;
  
  ${props => props.active ? `
    background-color: #dcfce7;
    color: #16a34a;
    border: 1px solid #bbf7d0;
  ` : `
    background-color: #fee2e2;
    color: #dc2626;
    border: 1px solid #fecaca;
  `}
`;

const StatusDot = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
  animation: ${props => props.active ? 'pulse 2s infinite' : 'none'};
  
  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
  }
`;

const scenarios = {
  'ecommerce': {
    name: 'E-commerce Holiday Sale',
    description: 'High-volume retail campaign with geographic targeting',
    icon: BarChart3
  },
  'gaming': {
    name: 'Mobile Gaming Campaign', 
    description: 'Gaming app promotion with evening peak traffic',
    icon: Zap
  },
  'finance': {
    name: 'Financial Services',
    description: 'Conservative patterns with fraud monitoring',
    icon: Shield
  },
  'social': {
    name: 'Social Media Platform',
    description: 'Viral campaign with influencer marketing',
    icon: Database
  }
};

const DemoControls = ({ 
  currentScenario, 
  simulationActive, 
  onStartSimulation, 
  onStopSimulation, 
  onChangeScenario 
}) => {
  const [speed, setSpeed] = useState(1.0);
  const [scenarios_list, setScenarios] = useState(null);
  const [loading, setLoading] = useState(false);
  const { get, post } = useApi();

  useEffect(() => {
    const fetchScenarios = async () => {
      try {
        const data = await get('/api/scenarios', { silent: true });
        setScenarios(data);
      } catch (error) {
        console.error('Failed to fetch scenarios:', error);
      }
    };

    fetchScenarios();
  }, [get]);

  const handleSpeedChange = (e) => {
    setSpeed(parseFloat(e.target.value));
  };

  const handleStartSimulation = async () => {
    setLoading(true);
    try {
      await onStartSimulation(speed);
      toast.success('Simulation started successfully');
    } catch (error) {
      toast.error('Failed to start simulation');
    } finally {
      setLoading(false);
    }
  };

  const handleStopSimulation = async () => {
    setLoading(true);
    try {
      await onStopSimulation();
      toast.success('Simulation stopped');
    } catch (error) {
      toast.error('Failed to stop simulation');
    } finally {
      setLoading(false);
    }
  };

  const triggerBurstTraffic = async () => {
    toast.success('Burst traffic simulation initiated (demo only)');
  };

  const triggerFraudAttack = async () => {
    toast.success('Fraud attack simulation initiated (demo only)');
  };

  const resetData = async () => {
    toast.success('Data reset completed (demo only)');
  };

  return (
    <ControlsContainer>
      <Title>Demo Controls</Title>
      
      <Section>
        <SectionTitle>
          <Settings size={20} />
          Simulation Status
        </SectionTitle>
        
        <StatusIndicator active={simulationActive}>
          <StatusDot active={simulationActive} />
          {simulationActive ? 'Simulation Active' : 'Simulation Stopped'}
          {simulationActive && ` (${speed}x speed)`}
        </StatusIndicator>

        <ControlGrid>
          <ControlCard>
            <h4>Start Simulation</h4>
            <p>Begin generating realistic ad click events</p>
            <Button 
              variant="success" 
              onClick={handleStartSimulation}
              disabled={simulationActive || loading}
            >
              <Play size={16} />
              Start
            </Button>
          </ControlCard>

          <ControlCard>
            <h4>Stop Simulation</h4>
            <p>Halt event generation and processing</p>
            <Button 
              variant="danger" 
              onClick={handleStopSimulation}
              disabled={!simulationActive || loading}
            >
              <Square size={16} />
              Stop
            </Button>
          </ControlCard>

          <ControlCard>
            <h4>Pause/Resume</h4>
            <p>Temporarily pause the simulation</p>
            <Button 
              variant="warning"
              disabled={!simulationActive || loading}
            >
              <Pause size={16} />
              Pause
            </Button>
          </ControlCard>

          <ControlCard>
            <h4>Reset Data</h4>
            <p>Clear all generated data and metrics</p>
            <Button 
              variant="danger"
              onClick={resetData}
              disabled={loading}
            >
              <RefreshCw size={16} />
              Reset
            </Button>
          </ControlCard>
        </ControlGrid>
      </Section>

      <Section>
        <SectionTitle>
          <BarChart3 size={20} />
          Scenario Configuration
        </SectionTitle>

        <ControlCard>
          <h4>Demo Scenario</h4>
          <p>Select the business use case to demonstrate</p>
          <ScenarioSelector
            value={currentScenario}
            onChange={(e) => onChangeScenario(e.target.value)}
          >
            {Object.entries(scenarios).map(([key, scenario]) => (
              <option key={key} value={key}>
                {scenario.name}
              </option>
            ))}
          </ScenarioSelector>
          
          {scenarios[currentScenario] && (
            <div style={{ 
              marginTop: '12px', 
              fontSize: '12px', 
              color: '#64748b',
              fontStyle: 'italic' 
            }}>
              {scenarios[currentScenario].description}
            </div>
          )}
        </ControlCard>

        <ControlCard>
          <h4>Simulation Speed</h4>
          <p>Control the rate of event generation</p>
          <SpeedSlider>
            <label>Speed Multiplier: {speed}x</label>
            <input
              type="range"
              min="0.1"
              max="5.0"
              step="0.1"
              value={speed}
              onChange={handleSpeedChange}
            />
            <div className="speed-labels">
              <span>0.1x</span>
              <span>1x</span>
              <span>2x</span>
              <span>5x</span>
            </div>
          </SpeedSlider>
        </ControlCard>
      </Section>

      <Section>
        <SectionTitle>
          <Zap size={20} />
          Demo Scenarios
        </SectionTitle>

        <ControlGrid>
          <ControlCard>
            <h4>Burst Traffic</h4>
            <p>Simulate sudden traffic spike for 60 seconds</p>
            <Button 
              variant="primary"
              onClick={triggerBurstTraffic}
              disabled={loading}
            >
              <Zap size={16} />
              Trigger Burst
            </Button>
          </ControlCard>

          <ControlCard>
            <h4>Fraud Attack</h4>
            <p>Simulate fraudulent click patterns</p>
            <Button 
              variant="warning"
              onClick={triggerFraudAttack}
              disabled={loading}
            >
              <Shield size={16} />
              Simulate Fraud
            </Button>
          </ControlCard>

          <ControlCard>
            <h4>System Stress Test</h4>
            <p>Test system under high load conditions</p>
            <Button 
              variant="primary"
              disabled={loading}
            >
              <BarChart3 size={16} />
              Stress Test
            </Button>
          </ControlCard>

          <ControlCard>
            <h4>Geographic Surge</h4>
            <p>Simulate traffic from specific regions</p>
            <Button 
              variant="primary"
              disabled={loading}
            >
              <Database size={16} />
              Geo Surge
            </Button>
          </ControlCard>
        </ControlGrid>
      </Section>

      <Section>
        <SectionTitle>
          <Settings size={20} />
          Advanced Settings
        </SectionTitle>

        <ControlGrid>
          <ControlCard>
            <h4>Fraud Rate</h4>
            <p>Percentage of fraudulent events (0-50%)</p>
            <input 
              type="range" 
              min="0" 
              max="50" 
              defaultValue="5"
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
              Current: 5%
            </div>
          </ControlCard>

          <ControlCard>
            <h4>Peak Hours</h4>
            <p>Define high-activity time periods</p>
            <ScenarioSelector defaultValue="default">
              <option value="default">Default Pattern</option>
              <option value="morning">Morning Peak (9-12)</option>
              <option value="evening">Evening Peak (18-22)</option>
              <option value="24h">24/7 Uniform</option>
            </ScenarioSelector>
          </ControlCard>

          <ControlCard>
            <h4>Device Mix</h4>
            <p>Distribution of device types</p>
            <div style={{ fontSize: '12px', color: '#64748b' }}>
              Mobile: 70% | Desktop: 25% | Tablet: 5%
            </div>
            <Button variant="outline" style={{ marginTop: '8px' }}>
              Configure
            </Button>
          </ControlCard>

          <ControlCard>
            <h4>Geographic Distribution</h4>
            <p>Regional traffic patterns</p>
            <div style={{ fontSize: '12px', color: '#64748b' }}>
              Based on selected scenario
            </div>
            <Button variant="outline" style={{ marginTop: '8px' }}>
              Customize
            </Button>
          </ControlCard>
        </ControlGrid>
      </Section>
    </ControlsContainer>
  );
};

export default DemoControls;