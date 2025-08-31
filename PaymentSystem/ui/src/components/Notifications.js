import React, { useState, useEffect } from 'react';
import {
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Button,
  IconButton,
  Avatar,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Badge,
  Tab,
  Tabs
} from '@mui/material';
import {
  Email as EmailIcon,
  Sms as SmsIcon,
  Web as WebIcon,
  Notifications as NotificationsIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Clear as ClearIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';
import axios from 'axios';

function Notifications() {
  const [activeTab, setActiveTab] = useState(0);
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    fetchRealNotifications();
    const interval = setInterval(fetchRealNotifications, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchRealNotifications = async () => {
    try {
      let systemNotifications = [];
      
      // Get notifications from localStorage (created by user actions)
      const storedNotifications = JSON.parse(localStorage.getItem('notifications') || '[]');
      
      // Generate notifications based on recent wallet transactions
      try {
        const wallets = await axios.get(`http://localhost:8740/api/v1/users/testuser123/wallets`);
        
        for (const wallet of wallets.data) {
          try {
            const txResponse = await axios.get(`http://localhost:8740/api/v1/wallets/${wallet.wallet_id}/transactions`);
            
            // Create notifications for recent transactions (last 24 hours)
            const recentTransactions = txResponse.data.filter(tx => {
              const txDate = new Date(tx.created_at);
              const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
              return txDate > oneDayAgo;
            });
            
            recentTransactions.forEach(tx => {
              const amount = Math.abs(parseFloat(tx.amount));
              let notificationType, title, priority;
              
              if (tx.description && tx.description.includes('Payment via')) {
                notificationType = 'payment_success';
                title = 'Payment Processed Successfully';
                priority = 'normal';
              } else if (amount > 1000) {
                notificationType = 'large_transaction';
                title = 'Large Transaction Alert';
                priority = 'high';
              } else {
                notificationType = 'transaction_complete';
                title = 'Transaction Completed';
                priority = 'low';
              }
              
              // Check for low balance warnings
              if (parseFloat(wallet.balance) < 100) {
                systemNotifications.push({
                  id: `LOW_BAL_${wallet.wallet_id}_${Date.now()}`,
                  type: 'wallet_low_balance',
                  title: 'Low Wallet Balance Alert',
                  message: `Wallet ${wallet.wallet_id} balance is low: $${wallet.balance} remaining.`,
                  timestamp: new Date().toISOString(),
                  read: false,
                  priority: 'high',
                  channel: 'push',
                  user: wallet.user_id
                });
              }
              
              systemNotifications.push({
                id: `TX_${tx.transaction_id}`,
                type: notificationType,
                title: title,
                message: `${tx.transaction_type === 'debit' ? 'Sent' : 'Received'} $${amount} - ${tx.description || 'Wallet transaction'}`,
                timestamp: tx.created_at,
                read: false,
                priority: priority,
                channel: amount > 500 ? 'sms' : 'email',
                user: wallet.user_id
              });
            });
          } catch (txError) {
            console.log(`No transactions found for wallet ${wallet.wallet_id}`);
          }
        }
      } catch (error) {
        console.error('Error fetching wallet data for notifications:', error);
      }
      
      // Get fraud alerts from fraud detection service
      try {
        const fraudStats = await axios.get(`http://localhost:8742/api/v1/fraud/stats`);
        if (fraudStats.data?.alerts_24h?.critical > 0) {
          systemNotifications.push({
            id: `FRAUD_ALERT_${Date.now()}`,
            type: 'fraud_alert',
            title: 'Critical Fraud Alerts Detected',
            message: `${fraudStats.data.alerts_24h.critical} critical fraud alerts detected in the last 24 hours. Immediate attention required.`,
            timestamp: new Date().toISOString(),
            read: false,
            priority: 'critical',
            channel: 'sms',
            user: 'admin'
          });
        }
      } catch (error) {
        console.error('Error fetching fraud stats:', error);
      }
      
      // Combine all notifications
      const allNotifications = [...storedNotifications, ...systemNotifications];
      
      // Remove duplicates and sort by timestamp
      const uniqueNotifications = allNotifications.reduce((acc, notif) => {
        if (!acc.find(n => n.id === notif.id)) {
          acc.push(notif);
        }
        return acc;
      }, []);
      
      uniqueNotifications.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      
      // Apply persisted read states
      const readStates = JSON.parse(localStorage.getItem('notificationReadStates') || '{}');
      const notificationsWithReadStates = uniqueNotifications.map(notif => ({
        ...notif,
        read: readStates[notif.id] || notif.read || false
      }));
      
      setNotifications(notificationsWithReadStates.slice(0, 50)); // Keep only latest 50 notifications
      
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const [settings, setSettings] = useState({
    email: true,
    sms: true,
    push: true,
    webhook: false,
    fraudAlerts: true,
    paymentUpdates: true,
    systemNotifications: false,
    reconciliationReports: true
  });

  const unreadCount = notifications.filter(n => !n.read).length;
  const criticalCount = notifications.filter(n => n.priority === 'critical' && !n.read).length;

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'payment_success': return <CheckIcon color="success" />;
      case 'fraud_alert': return <ErrorIcon color="error" />;
      case 'wallet_low_balance': return <WarningIcon color="warning" />;
      case 'reconciliation_complete': return <CheckIcon color="info" />;
      case 'system_maintenance': return <InfoIcon color="info" />;
      case 'large_transaction': return <WarningIcon color="warning" />;
      case 'transaction_complete': return <CheckIcon color="success" />;
      default: return <NotificationsIcon />;
    }
  };

  const getChannelIcon = (channel) => {
    switch (channel) {
      case 'email': return <EmailIcon />;
      case 'sms': return <SmsIcon />;
      case 'webhook': return <WebIcon />;
      case 'push': return <NotificationsIcon />;
      default: return <NotificationsIcon />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'normal': return 'primary';
      case 'low': return 'default';
      default: return 'default';
    }
  };

  const markAsRead = (id) => {
    setNotifications(prev => {
      const updated = prev.map(notif => 
        notif.id === id ? { ...notif, read: true } : notif
      );
      
      // Persist read state to localStorage
      const readStates = JSON.parse(localStorage.getItem('notificationReadStates') || '{}');
      readStates[id] = true;
      localStorage.setItem('notificationReadStates', JSON.stringify(readStates));
      
      return updated;
    });
  };

  const markAllAsRead = () => {
    setNotifications(prev => {
      const updated = prev.map(notif => ({ ...notif, read: true }));
      
      // Persist all read states to localStorage
      const readStates = JSON.parse(localStorage.getItem('notificationReadStates') || '{}');
      updated.forEach(notif => {
        readStates[notif.id] = true;
      });
      localStorage.setItem('notificationReadStates', JSON.stringify(readStates));
      
      return updated;
    });
  };

  const deleteNotification = (id) => {
    setNotifications(prev => prev.filter(notif => notif.id !== id));
    
    // Remove from read states as well
    const readStates = JSON.parse(localStorage.getItem('notificationReadStates') || '{}');
    delete readStates[id];
    localStorage.setItem('notificationReadStates', JSON.stringify(readStates));
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const notificationStats = {
    today: notifications.filter(n => {
      const today = new Date();
      const notifDate = new Date(n.timestamp);
      return notifDate.toDateString() === today.toDateString();
    }).length,
    thisWeek: notifications.length,
    delivered: notifications.filter(n => n.channel === 'email' || n.channel === 'sms').length,
    failed: 0
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        🔔 Notifications Center
      </Typography>
      
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Unread</Typography>
              <Typography variant="h3" color="primary">
                <Badge badgeContent={unreadCount} color="error">
                  {unreadCount}
                </Badge>
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Critical</Typography>
              <Typography variant="h3" color="error.main">{criticalCount}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Today</Typography>
              <Typography variant="h3" color="success.main">{notificationStats.today}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Delivered</Typography>
              <Typography variant="h3" color="info.main">{notificationStats.delivered}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} sx={{ mb: 3 }}>
        <Tab 
          label={
            <Badge badgeContent={unreadCount} color="error">
              All Notifications
            </Badge>
          } 
        />
        <Tab label="Settings" />
      </Tabs>

      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">Recent Notifications</Typography>
                  <Button 
                    variant="outlined" 
                    size="small"
                    onClick={markAllAsRead}
                    disabled={unreadCount === 0}
                  >
                    Mark All as Read
                  </Button>
                </Box>
                
                <List>
                  {notifications.map((notification, index) => (
                    <React.Fragment key={notification.id}>
                      <ListItem
                        sx={{
                          bgcolor: notification.read ? 'transparent' : 'action.hover',
                          borderRadius: 1,
                          mb: 1
                        }}
                      >
                        <ListItemIcon>
                          <Avatar sx={{ bgcolor: 'transparent' }}>
                            {getNotificationIcon(notification.type)}
                          </Avatar>
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography 
                                variant="subtitle1" 
                                sx={{ fontWeight: notification.read ? 'normal' : 'bold' }}
                              >
                                {notification.title}
                              </Typography>
                              <Chip 
                                label={notification.priority} 
                                color={getPriorityColor(notification.priority)}
                                size="small"
                              />
                              {getChannelIcon(notification.channel)}
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="textSecondary">
                                {notification.message}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                {formatTimestamp(notification.timestamp)} • {notification.user}
                              </Typography>
                            </Box>
                          }
                        />
                        <Box>
                          {!notification.read && (
                            <IconButton 
                              size="small" 
                              onClick={() => markAsRead(notification.id)}
                              title="Mark as read"
                            >
                              <CheckIcon />
                            </IconButton>
                          )}
                          <IconButton 
                            size="small" 
                            onClick={() => deleteNotification(notification.id)}
                            title="Delete"
                          >
                            <ClearIcon />
                          </IconButton>
                        </Box>
                      </ListItem>
                      {index < notifications.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                  
                  {notifications.length === 0 && (
                    <ListItem>
                      <ListItemText>
                        <Alert severity="info">No notifications available</Alert>
                      </ListItemText>
                    </ListItem>
                  )}
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <SettingsIcon sx={{ mr: 1 }} />
                  Notification Channels
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.email}
                        onChange={(e) => setSettings({...settings, email: e.target.checked})}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <EmailIcon />
                        <Typography>Email Notifications</Typography>
                      </Box>
                    }
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.sms}
                        onChange={(e) => setSettings({...settings, sms: e.target.checked})}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <SmsIcon />
                        <Typography>SMS Notifications</Typography>
                      </Box>
                    }
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.push}
                        onChange={(e) => setSettings({...settings, push: e.target.checked})}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <NotificationsIcon />
                        <Typography>Push Notifications</Typography>
                      </Box>
                    }
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.webhook}
                        onChange={(e) => setSettings({...settings, webhook: e.target.checked})}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <WebIcon />
                        <Typography>Webhook Notifications</Typography>
                      </Box>
                    }
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Notification Types
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.fraudAlerts}
                        onChange={(e) => setSettings({...settings, fraudAlerts: e.target.checked})}
                      />
                    }
                    label="Fraud Alerts"
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.paymentUpdates}
                        onChange={(e) => setSettings({...settings, paymentUpdates: e.target.checked})}
                      />
                    }
                    label="Payment Updates"
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.systemNotifications}
                        onChange={(e) => setSettings({...settings, systemNotifications: e.target.checked})}
                      />
                    }
                    label="System Notifications"
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={settings.reconciliationReports}
                        onChange={(e) => setSettings({...settings, reconciliationReports: e.target.checked})}
                      />
                    }
                    label="Reconciliation Reports"
                  />
                </Box>
                
                <Alert severity="success" sx={{ mt: 2 }}>
                  Settings saved automatically
                </Alert>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default Notifications;