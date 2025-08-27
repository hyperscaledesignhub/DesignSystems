import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import Trading from './components/Trading';
import OrderBook from './components/OrderBook';
import Portfolio from './components/Portfolio';
import MarketData from './components/MarketData';
import RiskManagement from './components/RiskManagement';
import Reports from './components/Reports';
import UseCases from './components/UseCases';
import Login from './components/Login';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import './App.css';

function AppContent() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="App">
        <div className="loading-container">
          <div className="loading-spinner">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <WebSocketProvider>
      <div className="App">
        <Toaster position="top-right" />
        {isAuthenticated && <Navbar />}
        <div className="main-content">
          <Routes>
            <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
            <Route path="/trading" element={isAuthenticated ? <Trading /> : <Navigate to="/login" />} />
            <Route path="/orderbook" element={isAuthenticated ? <OrderBook /> : <Navigate to="/login" />} />
            <Route path="/portfolio" element={isAuthenticated ? <Portfolio /> : <Navigate to="/login" />} />
            <Route path="/market-data" element={isAuthenticated ? <MarketData /> : <Navigate to="/login" />} />
            <Route path="/risk" element={isAuthenticated ? <RiskManagement /> : <Navigate to="/login" />} />
            <Route path="/reports" element={isAuthenticated ? <Reports /> : <Navigate to="/login" />} />
            <Route path="/use-cases" element={isAuthenticated ? <UseCases /> : <Navigate to="/login" />} />
            <Route path="/" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} />
          </Routes>
        </div>
      </div>
    </WebSocketProvider>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;