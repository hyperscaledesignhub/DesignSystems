import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navigation = ({ user, onLogout }) => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;
  
  // Check if user is admin (demo logic - in real app this would come from backend)
  const isAdmin = user.email === 'admin@demo.com' || user.email === 'demo@example.com';

  return (
    <nav className="nav-container">
      <div className="nav-content">
        <div className="nav-brand">
          <span>🏨 Hotel Booking</span>
          {isAdmin && <span className="admin-badge">ADMIN</span>}
        </div>
        
        <ul className="nav-links">
          <li>
            <Link to="/dashboard" className={isActive('/dashboard') ? 'active' : ''}>
              Dashboard
            </Link>
          </li>
          
          {/* Guest/Customer Navigation */}
          <li>
            <Link to="/hotels" className={isActive('/hotels') ? 'active' : ''}>
              Hotels
            </Link>
          </li>
          <li>
            <Link to="/booking" className={isActive('/booking') ? 'active' : ''}>
              Book Room
            </Link>
          </li>
          <li>
            <Link to="/reservations" className={isActive('/reservations') ? 'active' : ''}>
              My Reservations
            </Link>
          </li>
          <li>
            <Link to="/payments" className={isActive('/payments') ? 'active' : ''}>
              Payments
            </Link>
          </li>
          
          {/* Admin-only Navigation */}
          {isAdmin && (
            <>
              <li className="nav-divider">
                <span>ADMIN</span>
              </li>
              <li>
                <Link to="/admin/hotels" className={isActive('/admin/hotels') ? 'active' : ''}>
                  Manage Hotels
                </Link>
              </li>
              <li>
                <Link to="/inventory" className={isActive('/inventory') ? 'active' : ''}>
                  Inventory
                </Link>
              </li>
            </>
          )}
        </ul>
        
        <div className="nav-user">
          <span className="user-info">
            Welcome, {user.first_name}!
            {isAdmin && <span className="role-badge">Admin</span>}
          </span>
          <button className="btn btn-secondary" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;