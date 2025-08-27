import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  LayoutDashboard, 
  TrendingUp, 
  BookOpen, 
  Briefcase, 
  BarChart3, 
  Shield, 
  FileText,
  Rocket,
  LogOut,
  User
} from 'lucide-react';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();
  const { user, logout } = useAuth();

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/trading', label: 'Trading', icon: TrendingUp },
    { path: '/orderbook', label: 'Order Book', icon: BookOpen },
    { path: '/portfolio', label: 'Portfolio', icon: Briefcase },
    { path: '/market-data', label: 'Market Data', icon: BarChart3 },
    { path: '/risk', label: 'Risk Management', icon: Shield },
    { path: '/reports', label: 'Reports', icon: FileText },
    { path: '/use-cases', label: 'Use Cases', icon: Rocket },
  ];

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <TrendingUp size={24} />
          <span>Stock Exchange</span>
        </div>
        
        <div className="navbar-menu">
          {navItems.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={`navbar-item ${location.pathname === path ? 'active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          ))}
        </div>

        <div className="navbar-user">
          <div className="user-info">
            <User size={18} />
            <span>{user?.username || 'User'}</span>
          </div>
          <button onClick={logout} className="btn-logout">
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;