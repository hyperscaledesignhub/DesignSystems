import React, { useState, useEffect } from 'react';
import {
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  Alert,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Button
} from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import axios from 'axios';

const COLORS = ['#4caf50', '#ff9800', '#f44336', '#9c27b0'];

function FraudDetection() {
  const [fraudStats, setFraudStats] = useState({
    totalChecks: 0,
    approvedCount: 0,
    rejectedCount: 0,
    averageRiskScore: 0
  });
  const [recentChecks, setRecentChecks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testForm, setTestForm] = useState({
    payment_id: '',
    amount: '',
    merchant_id: 'MERCH001',
    user_id: 'USER123'
  });
  const [realStats, setRealStats] = useState(null);

  useEffect(() => {
    fetchFraudStats();
  }, []);

  const fetchFraudStats = async () => {
    try {
      const response = await axios.get('http://localhost:8742/api/v1/fraud/stats');
      setRealStats(response.data);
    } catch (error) {
      console.error('Error fetching fraud stats:', error);
    }
  };

  const getRiskLevelData = () => {
    if (!realStats?.risk_distribution) {
      return [
        { name: 'Low', value: 65, color: '#4caf50' },
        { name: 'Medium', value: 20, color: '#ff9800' },
        { name: 'High', value: 10, color: '#f44336' },
        { name: 'Critical', value: 5, color: '#9c27b0' }
      ];
    }
    
    const colorMap = {
      'low': '#4caf50',
      'medium': '#ff9800', 
      'high': '#f44336',
      'critical': '#9c27b0'
    };
    
    return Object.entries(realStats.risk_distribution).map(([level, data]) => ({
      name: level.charAt(0).toUpperCase() + level.slice(1),
      value: data.count,
      color: colorMap[level] || '#9c27b0'
    }));
  };
  
  const riskLevelData = getRiskLevelData();

  const dailyFraudData = [
    { date: '08-25', checks: 120, blocked: 8 },
    { date: '08-26', checks: 145, blocked: 12 },
    { date: '08-27', checks: 98, blocked: 5 },
    { date: '08-28', checks: 167, blocked: 15 },
    { date: '08-29', checks: 134, blocked: 9 },
    { date: '08-30', checks: 89, blocked: 4 }
  ];

  const testFraudDetection = async () => {
    if (!testForm.payment_id || !testForm.amount) {
      alert('Please fill in Payment ID and Amount');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8742/api/v1/fraud/check', {
        payment_id: testForm.payment_id,
        transaction_id: `TXN${Date.now()}`,
        user_id: testForm.user_id,
        amount: parseFloat(testForm.amount),
        currency: 'USD',
        payment_method: 'credit_card',
        ip_address: '192.168.1.100',
        user_agent: 'Mozilla/5.0 Demo Browser',
        timestamp: new Date().toISOString()
      });
      
      setTestResult(response.data);
      
      // Add to recent checks
      setRecentChecks(prev => [{
        ...response.data,
        amount: testForm.amount,
        timestamp: new Date().toLocaleString()
      }, ...prev.slice(0, 4)]);
      
      // Refresh fraud stats
      fetchFraudStats();
      
    } catch (error) {
      console.error('Fraud check failed:', error);
      setTestResult({ error: 'Failed to check fraud detection service' });
    }
    setLoading(false);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        🛡️ Fraud Detection Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">Total Checks Today</Typography>
              <Typography variant="h3" color="primary">
                {realStats?.checks_24h?.total || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">Approved</Typography>
              <Typography variant="h3" color="success.main">
                {realStats?.checks_24h?.approved || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">Blocked</Typography>
              <Typography variant="h3" color="error.main">
                {realStats?.checks_24h?.declined || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">Avg Risk Score</Typography>
              <Typography variant="h3" color="warning.main">
                {Math.round(realStats?.checks_24h?.avg_risk_score || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Risk Level Distribution */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Risk Level Distribution</Typography>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={riskLevelData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({name, value}) => `${name}: ${value}%`}
                  >
                    {riskLevelData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Daily Fraud Checks */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Daily Fraud Checks</Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={dailyFraudData}>
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="checks" fill="#2196f3" name="Total Checks" />
                  <Bar dataKey="blocked" fill="#f44336" name="Blocked" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Test Fraud Detection */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Test Fraud Detection</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Payment ID"
                    value={testForm.payment_id}
                    onChange={(e) => setTestForm({...testForm, payment_id: e.target.value})}
                    placeholder="PAY123456"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Amount"
                    type="number"
                    value={testForm.amount}
                    onChange={(e) => setTestForm({...testForm, amount: e.target.value})}
                    placeholder="100.00"
                  />
                </Grid>
                <Grid item xs={12}>
                  <Button
                    variant="contained"
                    onClick={testFraudDetection}
                    disabled={loading}
                    fullWidth
                  >
                    {loading ? 'Checking...' : 'Run Fraud Check'}
                  </Button>
                </Grid>
              </Grid>

              {testResult && (
                <Box sx={{ mt: 2 }}>
                  {testResult.error ? (
                    <Alert severity="error">{testResult.error}</Alert>
                  ) : (
                    <Alert severity={testResult.decision === 'approve' ? 'success' : 'error'}>
                      <strong>Decision:</strong> {testResult.decision.toUpperCase()}<br/>
                      <strong>Risk Score:</strong> {testResult.risk_score}<br/>
                      <strong>Risk Level:</strong> {testResult.risk_level}<br/>
                      <strong>Reasons:</strong> {testResult.reasons?.join(', ')}
                    </Alert>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Fraud Checks */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recent Fraud Checks</Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Payment ID</TableCell>
                      <TableCell>Amount</TableCell>
                      <TableCell>Risk Score</TableCell>
                      <TableCell>Decision</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {recentChecks.length > 0 ? recentChecks.map((check, index) => (
                      <TableRow key={index}>
                        <TableCell>{check.payment_id}</TableCell>
                        <TableCell>${check.amount}</TableCell>
                        <TableCell>
                          <Chip 
                            label={check.risk_score} 
                            color={check.risk_score < 30 ? 'success' : check.risk_score < 70 ? 'warning' : 'error'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={check.decision} 
                            color={check.decision === 'approve' ? 'success' : 'error'}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    )) : (
                      <TableRow>
                        <TableCell colSpan={4}>
                          <Typography color="textSecondary" align="center">
                            No recent fraud checks. Use the test form above to run a check.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default FraudDetection;