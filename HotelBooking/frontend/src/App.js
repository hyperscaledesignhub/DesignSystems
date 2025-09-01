import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

import Login from './pages/Login';
import Registration from './pages/Registration';
import Dashboard from './pages/Dashboard';
import Hotels from './pages/Hotels';
import AdminHotels from './pages/AdminHotels';
import Rooms from './pages/Rooms';
import Booking from './pages/Booking';
import Reservations from './pages/Reservations';
import Payments from './pages/Payments';
import Inventory from './pages/Inventory';
import Navigation from './components/Navigation';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in from localStorage
    const savedUser = localStorage.getItem('hotel_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('hotel_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('hotel_user');
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading Hotel Booking System...</p>
      </div>
    );
  }

  return (
    <div className="App">
      {user && <Navigation user={user} onLogout={handleLogout} />}
      
      <main className={user ? 'main-content' : 'full-page'}>
        <Routes>
          <Route 
            path="/login" 
            element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/dashboard" />} 
          />
          <Route 
            path="/register" 
            element={!user ? <Registration onLogin={handleLogin} /> : <Navigate to="/dashboard" />} 
          />
          <Route 
            path="/dashboard" 
            element={user ? <Dashboard user={user} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/hotels" 
            element={user ? <Hotels /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/admin/hotels" 
            element={user ? <AdminHotels /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/rooms/:hotelId" 
            element={user ? <Rooms /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/booking" 
            element={user ? <Booking user={user} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/reservations" 
            element={user ? <Reservations user={user} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/payments" 
            element={user ? <Payments user={user} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/inventory" 
            element={user ? <Inventory /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/" 
            element={<Navigate to={user ? "/dashboard" : "/login"} />} 
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;