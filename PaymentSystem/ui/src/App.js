import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CssBaseline,
  ThemeProvider,
  createTheme,
  Badge,
  IconButton
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Payment,
  AccountBalance,
  Security,
  CompareArrows,
  Notifications,
  Assessment,
  AccountBalanceWallet,
  NotificationsActive
} from '@mui/icons-material';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Import components
import DashboardView from './components/Dashboard';
import PaymentsView from './components/Payments';
import WalletsView from './components/Wallets';
import FraudDetection from './components/FraudDetection';
import Reconciliation from './components/Reconciliation';
import NotificationsView from './components/Notifications';
import Analytics from './components/Analytics';
import LiveTransactions from './components/LiveTransactions';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    success: {
      main: '#4caf50',
    },
    warning: {
      main: '#ff9800',
    },
    error: {
      main: '#f44336',
    }
  },
});

const drawerWidth = 240;

function App() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    // Connect to WebSocket for real-time notifications
    const websocket = new WebSocket(process.env.REACT_APP_WS_URL || 'ws://localhost:8743/ws/dashboard');
    
    websocket.onopen = () => {
      console.log('Connected to notification service');
      websocket.send('ping');
    };

    websocket.onmessage = (event) => {
      try {
        const notification = JSON.parse(event.data);
        if (notification !== 'pong') {
          setNotifications(prev => [notification, ...prev]);
          setUnreadCount(prev => prev + 1);
        }
      } catch (e) {
        console.log('Received:', event.data);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);

    return () => {
      if (websocket.readyState === 1) {
        websocket.close();
      }
    };
  }, []);

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    { text: 'Payments', icon: <Payment />, path: '/payments' },
    { text: 'Wallets', icon: <AccountBalanceWallet />, path: '/wallets' },
    { text: 'Fraud Detection', icon: <Security />, path: '/fraud' },
    { text: 'Reconciliation', icon: <CompareArrows />, path: '/reconciliation' },
    { text: 'Notifications', icon: <Notifications />, path: '/notifications' },
    { text: 'Analytics', icon: <Assessment />, path: '/analytics' },
    { text: 'Live Feed', icon: <AccountBalance />, path: '/live' },
  ];

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex' }}>
          <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
            <Toolbar>
              <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
                Payment System Dashboard
              </Typography>
              <IconButton color="inherit" onClick={() => setUnreadCount(0)}>
                <Badge badgeContent={unreadCount} color="error">
                  <NotificationsActive />
                </Badge>
              </IconButton>
            </Toolbar>
          </AppBar>
          
          <Drawer
            variant="permanent"
            sx={{
              width: drawerWidth,
              flexShrink: 0,
              [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
            }}
          >
            <Toolbar />
            <Box sx={{ overflow: 'auto' }}>
              <List>
                {menuItems.map((item) => (
                  <ListItem button key={item.text} component={Link} to={item.path}>
                    <ListItemIcon>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.text} />
                  </ListItem>
                ))}
              </List>
            </Box>
          </Drawer>
          
          <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
            <Toolbar />
            <Container maxWidth="xl">
              <Routes>
                <Route path="/" element={<DashboardView />} />
                <Route path="/payments" element={<PaymentsView />} />
                <Route path="/wallets" element={<WalletsView />} />
                <Route path="/fraud" element={<FraudDetection />} />
                <Route path="/reconciliation" element={<Reconciliation />} />
                <Route path="/notifications" element={<NotificationsView notifications={notifications} />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/live" element={<LiveTransactions ws={ws} />} />
              </Routes>
            </Container>
          </Box>
        </Box>
        <ToastContainer position="bottom-right" />
      </Router>
    </ThemeProvider>
  );
}

export default App;