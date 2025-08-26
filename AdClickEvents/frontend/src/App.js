import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import styled from 'styled-components';
import { Toaster } from 'react-hot-toast';
import io from 'socket.io-client';

// Components
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import CampaignComparison from './pages/CampaignComparison';
import FraudDetection from './pages/FraudDetection';
import SystemHealth from './pages/SystemHealth';
import DemoControls from './pages/DemoControls';

// Hooks
import { useApi } from './hooks/useApi';

const AppContainer = styled.div`
  display: flex;
  height: 100vh;
  background-color: #f8fafc;
`;

const MainContent = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const ContentArea = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px;
`;

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8900';

function App() {
  const [socket, setSocket] = useState(null);
  const [realtimeData, setRealtimeData] = useState(null);
  const [currentScenario, setCurrentScenario] = useState('ecommerce');
  const [simulationActive, setSimulationActive] = useState(false);
  const { get, post } = useApi();

  useEffect(() => {
    // Initialize WebSocket connection
    const newSocket = io(API_BASE_URL);
    
    newSocket.on('connect', () => {
      console.log('Connected to WebSocket server');
    });
    
    newSocket.on('realtime_update', (data) => {
      setRealtimeData(data);
    });
    
    newSocket.on('disconnect', () => {
      console.log('Disconnected from WebSocket server');
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket.close();
    };
  }, []);

  const startSimulation = async (speed = 1.0) => {
    try {
      await post('/api/simulation/start', { speed });
      setSimulationActive(true);
    } catch (error) {
      console.error('Failed to start simulation:', error);
    }
  };

  const stopSimulation = async () => {
    try {
      await post('/api/simulation/stop');
      setSimulationActive(false);
    } catch (error) {
      console.error('Failed to stop simulation:', error);
    }
  };

  const changeScenario = async (scenario) => {
    try {
      await post('/api/scenario', { scenario });
      setCurrentScenario(scenario);
    } catch (error) {
      console.error('Failed to change scenario:', error);
    }
  };

  return (
    <Router>
      <AppContainer>
        <Toaster position="top-right" />
        
        <Sidebar />
        
        <MainContent>
          <Header 
            currentScenario={currentScenario}
            simulationActive={simulationActive}
            onStartSimulation={startSimulation}
            onStopSimulation={stopSimulation}
            onChangeScenario={changeScenario}
          />
          
          <ContentArea>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" />} />
              <Route 
                path="/dashboard" 
                element={
                  <Dashboard 
                    realtimeData={realtimeData}
                    simulationActive={simulationActive}
                  />
                } 
              />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/campaigns" element={<CampaignComparison />} />
              <Route path="/fraud" element={<FraudDetection />} />
              <Route path="/health" element={<SystemHealth />} />
              <Route 
                path="/controls" 
                element={
                  <DemoControls 
                    currentScenario={currentScenario}
                    simulationActive={simulationActive}
                    onStartSimulation={startSimulation}
                    onStopSimulation={stopSimulation}
                    onChangeScenario={changeScenario}
                  />
                } 
              />
            </Routes>
          </ContentArea>
        </MainContent>
      </AppContainer>
    </Router>
  );
}

export default App;