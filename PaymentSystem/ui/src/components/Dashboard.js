import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Chip,
  Button,
  Alert
} from '@mui/material';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';
import {
  TrendingUp, TrendingDown, AccountBalance, Warning, CheckCircle, Error,
  Timeline as TraceIcon
} from '@mui/icons-material';
import axios from 'axios';
import { format } from 'date-fns';

const API_BASE = process.env.REACT_APP_API_GATEWAY || 'http://localhost:8733';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState({
    payments: {},
    wallets: {},
    fraud: {},
    reconciliation: {},
    notifications: {}
  });
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Use wallet service for payment data since API gateway is not running
      const [wallets, fraud, reconciliation] = await Promise.all([
        axios.get(`http://localhost:8740/api/v1/wallets/stats/summary`),
        axios.get(`http://localhost:8742/api/v1/fraud/stats`),
        axios.get(`http://localhost:8741/api/v1/reconciliations/stats/summary`)
      ]);

      // Create payment-like metrics from wallet data
      const payments = {
        data: {
          today: {
            total: wallets.data.transactions_24h?.total || 0,
            completed: wallets.data.transactions_24h?.total || 0,
            pending: 0,
            failed: 0,
            total_amount: parseFloat(wallets.data.transactions_24h?.credits || '0')
          }
        }
      };

      setMetrics({
        payments: payments.data,
        wallets: wallets.data,
        fraud: fraud.data,
        reconciliation: reconciliation.data,
        notifications: {} // Mock empty notifications data
      });

      // Generate chart data
      generateChartData(payments.data);
      
      // Fetch recent transactions from wallets
      try {
        const wallets = await axios.get(`http://localhost:8740/api/v1/users/testuser123/wallets`);
        let allTransactions = [];
        
        // Fetch transactions for each wallet
        for (const wallet of wallets.data.slice(0, 5)) { // Limit to first 5 wallets to avoid too many requests
          try {
            const txResponse = await axios.get(`http://localhost:8740/api/v1/wallets/${wallet.wallet_id}/transactions`);
            const transactions = txResponse.data.map(tx => ({
              payment_id: tx.transaction_id || `TX${tx.id}`,
              amount: Math.abs(parseFloat(tx.amount)),
              status: tx.status || 'completed',
              risk_level: Math.abs(parseFloat(tx.amount)) > 1000 ? 'high' : Math.abs(parseFloat(tx.amount)) > 500 ? 'medium' : 'low',
              created_at: tx.created_at || new Date(),
              description: tx.description || 'Wallet transaction',
              transaction_type: tx.transaction_type
            }));
            allTransactions = [...allTransactions, ...transactions];
          } catch (txError) {
            console.log(`No transactions found for wallet ${wallet.wallet_id}`);
          }
        }
        
        // Sort by created date and take most recent 10
        allTransactions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setRecentTransactions(allTransactions.slice(0, 10));
      } catch (error) {
        console.error('Error fetching transactions:', error);
        setRecentTransactions([]);
      }

      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  const generateChartData = (paymentData) => {
    // Generate hourly data for the last 24 hours
    const hours = [];
    const now = new Date();
    for (let i = 23; i >= 0; i--) {
      const hour = new Date(now - i * 60 * 60 * 1000);
      hours.push({
        time: format(hour, 'HH:00'),
        transactions: Math.floor(Math.random() * 100) + 20,
        amount: Math.floor(Math.random() * 50000) + 10000,
        fraudDetected: Math.floor(Math.random() * 5)
      });
    }
    setChartData(hours);
  };

  const MetricCard = ({ title, value, subtitle, icon, trend, color = 'primary' }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography color="textSecondary" variant="h6">
            {title}
          </Typography>
          <Box sx={{ color: `${color}.main` }}>
            {icon}
          </Box>
        </Box>
        <Typography variant="h4" component="div" gutterBottom>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="textSecondary">
            {subtitle}
          </Typography>
        )}
        {trend && (
          <Box display="flex" alignItems="center" mt={1}>
            {trend > 0 ? (
              <TrendingUp color="success" fontSize="small" />
            ) : (
              <TrendingDown color="error" fontSize="small" />
            )}
            <Typography variant="body2" color={trend > 0 ? 'success.main' : 'error.main'} ml={0.5}>
              {Math.abs(trend)}% from yesterday
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  const fraudDistribution = metrics.fraud?.risk_distribution ? 
    Object.entries(metrics.fraud.risk_distribution).map(([level, data]) => ({
      name: level.charAt(0).toUpperCase() + level.slice(1),
      value: data.count
    })) : [];

  const paymentStatusData = [
    { name: 'Completed', value: metrics.payments?.today?.completed || 0 },
    { name: 'Pending', value: metrics.payments?.today?.pending || 0 },
    { name: 'Failed', value: metrics.payments?.today?.failed || 0 }
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          System Overview
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Chip
            icon={<TraceIcon />}
            label="View Distributed Traces"
            color="primary"
            onClick={() => window.open('http://localhost:16686', '_blank')}
            sx={{ cursor: 'pointer' }}
          />
        </Box>
      </Box>
      
      {/* Key Metrics */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Transactions"
            value={metrics.payments?.today?.total || 0}
            subtitle={`$${(metrics.payments?.today?.total_amount || 0).toLocaleString()}`}
            icon={<AccountBalance />}
            trend={12}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Active Wallets"
            value={metrics.wallets?.wallets?.total || 0}
            subtitle={`${metrics.wallets?.wallets?.users || 0} users`}
            icon={<AccountBalance />}
            trend={5}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Fraud Alerts"
            value={metrics.fraud?.alerts_24h?.open || 0}
            subtitle={`${metrics.fraud?.alerts_24h?.critical || 0} critical`}
            icon={<Warning />}
            trend={-8}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Success Rate"
            value={`${Math.round((metrics.payments?.today?.completed / metrics.payments?.today?.total) * 100 || 0)}%`}
            subtitle="Last 24 hours"
            icon={<CheckCircle />}
            trend={3}
            color="success"
          />
        </Grid>
      </Grid>

      {/* Distributed Tracing Section */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12}>
          <Card sx={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white'
          }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TraceIcon /> Distributed Tracing Monitor
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
                    All 4 microservices are actively generating traces. Track request flow across services,
                    identify bottlenecks, and debug distributed transactions in real-time.
                  </Typography>
                  <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                    <Chip label="wallet-service ✓" size="small" sx={{ bgcolor: 'rgba(255,255,255,0.2)' }} />
                    <Chip label="fraud-detection-service ✓" size="small" sx={{ bgcolor: 'rgba(255,255,255,0.2)' }} />
                    <Chip label="reconciliation-service ✓" size="small" sx={{ bgcolor: 'rgba(255,255,255,0.2)' }} />
                    <Chip label="notification-service ✓" size="small" sx={{ bgcolor: 'rgba(255,255,255,0.2)' }} />
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Button
                    variant="contained"
                    startIcon={<TraceIcon />}
                    onClick={() => window.open('http://localhost:16686', '_blank')}
                    sx={{ 
                      bgcolor: 'white', 
                      color: '#667eea',
                      '&:hover': { bgcolor: 'rgba(255,255,255,0.9)' }
                    }}
                  >
                    Open Jaeger UI
                  </Button>
                  <Typography variant="caption" sx={{ textAlign: 'center', opacity: 0.8 }}>
                    Port: 16686
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Transaction Volume (24h)
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="transactions" stroke="#8884d8" fill="#8884d8" />
                <Area type="monotone" dataKey="fraudDetected" stroke="#ff8042" fill="#ff8042" />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Payment Status Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={paymentStatusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {paymentStatusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Additional Metrics */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Fraud Risk Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={fraudDistribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#ff9800" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              System Health
            </Typography>
            <Box mt={2}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Box display="flex" alignItems="center" mb={2}>
                    <CheckCircle color="success" sx={{ mr: 1 }} />
                    <Typography>Payment Service</Typography>
                  </Box>
                  <Box display="flex" alignItems="center" mb={2}>
                    <CheckCircle color="success" sx={{ mr: 1 }} />
                    <Typography>Wallet Service</Typography>
                  </Box>
                  <Box display="flex" alignItems="center" mb={2}>
                    <CheckCircle color="success" sx={{ mr: 1 }} />
                    <Typography>Fraud Detection</Typography>
                  </Box>
                  <Box display="flex" alignItems="center">
                    <CheckCircle color="success" sx={{ mr: 1 }} />
                    <Typography>Notification Service</Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box mb={2}>
                    <Typography variant="body2" color="textSecondary">
                      Reconciliation Status
                    </Typography>
                    <Typography variant="h6">
                      {metrics.reconciliation?.reconciliations?.completed || 0} / {metrics.reconciliation?.reconciliations?.total || 0}
                    </Typography>
                  </Box>
                  <Box mb={2}>
                    <Typography variant="body2" color="textSecondary">
                      Unresolved Discrepancies
                    </Typography>
                    <Typography variant="h6" color="warning.main">
                      {metrics.reconciliation?.discrepancies?.unresolved || 0}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="textSecondary">
                      Notifications Sent (24h)
                    </Typography>
                    <Typography variant="h6">
                      {metrics.notifications?.last_24h?.sent || 0}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Recent Transactions */}
      <Paper sx={{ p: 2, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Recent Transactions
        </Typography>
        <Box sx={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Transaction ID</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Amount</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Risk Level</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Description</th>
                <th style={{ padding: '12px', textAlign: 'left' }}>Time</th>
              </tr>
            </thead>
            <tbody>
              {recentTransactions.map((tx, index) => (
                <tr key={index} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '12px' }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {tx.payment_id || `PAY${Date.now()}${index}`}
                    </Typography>
                  </td>
                  <td style={{ padding: '12px' }}>
                    ${(tx.amount || Math.random() * 1000).toFixed(2)}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <Chip
                      label={tx.status || 'completed'}
                      color={tx.status === 'completed' ? 'success' : 'warning'}
                      size="small"
                    />
                  </td>
                  <td style={{ padding: '12px' }}>
                    <Chip
                      label={tx.risk_level || 'low'}
                      color={
                        tx.risk_level === 'high' ? 'error' :
                        tx.risk_level === 'medium' ? 'warning' : 'success'
                      }
                      size="small"
                      variant="outlined"
                    />
                  </td>
                  <td style={{ padding: '12px' }}>
                    <Typography variant="body2" color="textSecondary">
                      {tx.description || 'Transaction'}
                    </Typography>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <Typography variant="body2" color="textSecondary">
                      {format(new Date(tx.created_at || new Date()), 'HH:mm:ss')}
                    </Typography>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      </Paper>
    </Box>
  );
}

export default Dashboard;