import React from 'react';
import { NavLink } from 'react-router-dom';
import styled from 'styled-components';
import { 
  BarChart3, 
  TrendingUp, 
  Target, 
  Shield, 
  Activity, 
  Settings 
} from 'lucide-react';

const SidebarContainer = styled.div`
  width: 260px;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  color: white;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #334155;
`;

const Logo = styled.div`
  padding: 24px;
  border-bottom: 1px solid #334155;
  
  h1 {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
    background: linear-gradient(135deg, #3b82f6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  
  p {
    margin: 4px 0 0 0;
    font-size: 12px;
    color: #64748b;
  }
`;

const Navigation = styled.nav`
  flex: 1;
  padding: 24px 0;
`;

const NavItem = styled(NavLink)`
  display: flex;
  align-items: center;
  padding: 12px 24px;
  color: #cbd5e1;
  text-decoration: none;
  transition: all 0.2s ease;
  border-right: 3px solid transparent;
  
  &:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: white;
  }
  
  &.active {
    background-color: rgba(59, 130, 246, 0.1);
    color: #60a5fa;
    border-right-color: #3b82f6;
  }
  
  svg {
    margin-right: 12px;
    width: 20px;
    height: 20px;
  }
  
  span {
    font-weight: 500;
  }
`;

const Footer = styled.div`
  padding: 24px;
  border-top: 1px solid #334155;
  font-size: 12px;
  color: #64748b;
  text-align: center;
`;

const menuItems = [
  {
    path: '/dashboard',
    icon: BarChart3,
    label: 'Real-time Dashboard',
    description: 'Live metrics & KPIs'
  },
  {
    path: '/analytics',
    icon: TrendingUp,
    label: 'Analytics & Trends',
    description: 'Performance insights'
  },
  {
    path: '/campaigns',
    icon: Target,
    label: 'Campaign Comparison',
    description: 'A/B testing results'
  },
  {
    path: '/fraud',
    icon: Shield,
    label: 'Fraud Detection',
    description: 'Security monitoring'
  },
  {
    path: '/health',
    icon: Activity,
    label: 'System Health',
    description: 'Infrastructure monitoring'
  },
  {
    path: '/controls',
    icon: Settings,
    label: 'Demo Controls',
    description: 'Simulation settings'
  }
];

const Sidebar = () => {
  return (
    <SidebarContainer>
      <Logo>
        <h1>AdClick Demo</h1>
        <p>Event Aggregation System</p>
      </Logo>
      
      <Navigation>
        {menuItems.map((item) => {
          const IconComponent = item.icon;
          return (
            <NavItem key={item.path} to={item.path}>
              <IconComponent />
              <div>
                <span>{item.label}</span>
              </div>
            </NavItem>
          );
        })}
      </Navigation>
      
      <Footer>
        AdClick Demo v1.0.0<br />
        Built for system demonstrations
      </Footer>
    </SidebarContainer>
  );
};

export default Sidebar;