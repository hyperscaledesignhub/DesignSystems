import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { Play, Square, Globe, Clock } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const HeaderContainer = styled.div`
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 16px 24px;
  display: flex;
  justify-content: between;
  align-items: center;
  gap: 16px;
`;

const StatusSection = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
`;

const StatusBadge = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  
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

const ScenarioSection = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

const ScenarioSelector = styled.select`
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  min-width: 200px;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const ControlsSection = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
`;

const ControlButton = styled.button`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  
  ${props => props.variant === 'start' ? `
    background-color: #16a34a;
    color: white;
    border-color: #16a34a;
    
    &:hover {
      background-color: #15803d;
    }
  ` : `
    background-color: #dc2626;
    color: white;
    border-color: #dc2626;
    
    &:hover {
      background-color: #b91c1c;
    }
  `}
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const TimeDisplay = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #64748b;
`;

const scenarios = {
  'ecommerce': 'E-commerce Holiday Sale',
  'gaming': 'Mobile Gaming Campaign',
  'finance': 'Financial Services',
  'social': 'Social Media Platform'
};

const Header = ({ 
  currentScenario, 
  simulationActive, 
  onStartSimulation, 
  onStopSimulation, 
  onChangeScenario 
}) => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const { get } = useApi();

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <HeaderContainer>
      <StatusSection>
        <StatusBadge active={simulationActive}>
          <StatusDot active={simulationActive} />
          {simulationActive ? 'Simulation Active' : 'Simulation Stopped'}
        </StatusBadge>
        
        <TimeDisplay>
          <Clock size={16} />
          {formatTime(currentTime)}
        </TimeDisplay>
      </StatusSection>
      
      <ScenarioSection>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Globe size={16} />
          <span style={{ fontSize: '14px', fontWeight: '500' }}>Scenario:</span>
        </div>
        <ScenarioSelector
          value={currentScenario}
          onChange={(e) => onChangeScenario(e.target.value)}
        >
          {Object.entries(scenarios).map(([key, name]) => (
            <option key={key} value={key}>
              {name}
            </option>
          ))}
        </ScenarioSelector>
      </ScenarioSection>
      
      <ControlsSection>
        {!simulationActive ? (
          <ControlButton
            variant="start"
            onClick={() => onStartSimulation(1.0)}
          >
            <Play size={16} />
            Start Simulation
          </ControlButton>
        ) : (
          <ControlButton
            variant="stop"
            onClick={onStopSimulation}
          >
            <Square size={16} />
            Stop Simulation
          </ControlButton>
        )}
      </ControlsSection>
    </HeaderContainer>
  );
};

export default Header;