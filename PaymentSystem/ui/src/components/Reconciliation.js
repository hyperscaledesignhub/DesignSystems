import React, { useState } from 'react';
import {
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  TextField,
  Alert,
  LinearProgress,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import axios from 'axios';

function Reconciliation() {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [reconciliationResult, setReconciliationResult] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [reconciliations, setReconciliations] = useState([
    {
      id: 'REC20250830072737',
      date: '2025-08-30',
      status: 'completed',
      totalTransactions: 245,
      matchedTransactions: 241,
      unmatchedTransactions: 4,
      totalAmount: 62450.00,
      discrepancyAmount: 850.00
    },
    {
      id: 'REC20250829145623', 
      date: '2025-08-29',
      status: 'completed',
      totalTransactions: 189,
      matchedTransactions: 186,
      unmatchedTransactions: 3,
      totalAmount: 45200.00,
      discrepancyAmount: 320.00
    }
  ]);

  const discrepancies = [
    {
      id: 'DISC001',
      transactionId: 'TXN123456',
      type: 'amount_mismatch',
      internalAmount: 100.00,
      pspAmount: 95.00,
      difference: 5.00,
      status: 'pending',
      psp: 'Stripe'
    },
    {
      id: 'DISC002', 
      transactionId: 'TXN789012',
      type: 'missing_in_psp',
      internalAmount: 250.00,
      pspAmount: null,
      difference: 250.00,
      status: 'investigating',
      psp: 'PayPal'
    },
    {
      id: 'DISC003',
      transactionId: 'TXN345678',
      type: 'status_mismatch',
      internalAmount: 75.00,
      pspAmount: 75.00,
      difference: 0.00,
      status: 'resolved',
      psp: 'Square'
    }
  ];

  const reconciliationTrendData = [
    { date: '08-24', total: 156, matched: 152, unmatched: 4, matchRate: 97.4 },
    { date: '08-25', total: 189, matched: 186, unmatched: 3, matchRate: 98.4 },
    { date: '08-26', total: 134, matched: 131, unmatched: 3, matchRate: 97.8 },
    { date: '08-27', total: 245, matched: 241, unmatched: 4, matchRate: 98.4 },
    { date: '08-28', total: 178, matched: 175, unmatched: 3, matchRate: 98.3 },
    { date: '08-29', total: 189, matched: 186, unmatched: 3, matchRate: 98.4 },
    { date: '08-30', total: 245, matched: 241, unmatched: 4, matchRate: 98.4 }
  ];

  const pspPerformanceData = [
    { psp: 'Stripe', matched: 98.7, unmatched: 1.3, volume: 1250000 },
    { psp: 'PayPal', matched: 97.2, unmatched: 2.8, volume: 890000 },
    { psp: 'Square', matched: 99.1, unmatched: 0.9, volume: 650000 },
    { psp: 'Braintree', matched: 98.4, unmatched: 1.6, volume: 420000 }
  ];

  const runDailyReconciliation = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/reconciliation/', {
        start_date: new Date().toISOString().split('T')[0] + 'T00:00:00',
        end_date: new Date().toISOString().split('T')[0] + 'T23:59:59',
        reconciliation_type: 'daily'
      });
      
      setReconciliationResult(response.data);
      setOpenDialog(true);
      
      // Update reconciliations list
      setReconciliations(prev => [response.data, ...prev]);
      
    } catch (error) {
      console.error('Reconciliation failed:', error);
      setReconciliationResult({ error: 'Failed to run reconciliation' });
      setOpenDialog(true);
    }
    setLoading(false);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'warning'; 
      case 'failed': return 'error';
      case 'pending': return 'default';
      default: return 'default';
    }
  };

  const getDiscrepancyTypeColor = (type) => {
    switch (type) {
      case 'amount_mismatch': return 'warning';
      case 'missing_in_psp': return 'error';
      case 'missing_internal': return 'error';
      case 'status_mismatch': return 'info';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        🔄 Reconciliation Dashboard
      </Typography>
      
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Key Metrics */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Today's Match Rate</Typography>
              <Typography variant="h3" color="success.main">98.4%</Typography>
              <Typography variant="body2" color="textSecondary">241 of 245 matched</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Pending Discrepancies</Typography>
              <Typography variant="h3" color="warning.main">7</Typography>
              <Typography variant="body2" color="textSecondary">$1,245 in dispute</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Resolved Today</Typography>
              <Typography variant="h3" color="success.main">12</Typography>
              <Typography variant="body2" color="textSecondary">$845 recovered</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Settlement Amount</Typography>
              <Typography variant="h3" color="primary">$61.6K</Typography>
              <Typography variant="body2" color="textSecondary">Ready for payout</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} sx={{ mb: 3 }}>
        <Tab label="Overview" />
        <Tab label="Reconciliations" />
        <Tab label="Discrepancies" />
        <Tab label="Analytics" />
      </Tabs>

      {activeTab === 0 && (
        <Grid container spacing={3}>
          {/* Run Reconciliation */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Run Daily Reconciliation</Typography>
                <Typography variant="body2" color="textSecondary" paragraph>
                  Process today's transactions and identify discrepancies across all PSPs.
                </Typography>
                <Button
                  variant="contained"
                  onClick={runDailyReconciliation}
                  disabled={loading}
                  fullWidth
                  size="large"
                >
                  {loading ? 'Processing...' : 'Start Reconciliation'}
                </Button>
                {loading && <LinearProgress sx={{ mt: 2 }} />}
              </CardContent>
            </Card>
          </Grid>

          {/* Reconciliation Trends */}
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Weekly Reconciliation Trends</Typography>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={reconciliationTrendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis yAxisId="left" orientation="left" />
                    <YAxis yAxisId="right" orientation="right" domain={[95, 100]} />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="matched" fill="#4caf50" name="Matched" />
                    <Bar yAxisId="left" dataKey="unmatched" fill="#f44336" name="Unmatched" />
                    <Line yAxisId="right" type="monotone" dataKey="matchRate" stroke="#2196f3" strokeWidth={2} name="Match Rate %" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* PSP Performance */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>PSP Reconciliation Performance</Typography>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={pspPerformanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="psp" />
                    <YAxis />
                    <Tooltip formatter={(value, name) => 
                      name.includes('matched') ? [`${value}%`, name] : [`$${value.toLocaleString()}`, 'Volume']
                    } />
                    <Legend />
                    <Bar dataKey="matched" fill="#4caf50" name="Match Rate %" />
                    <Bar dataKey="unmatched" fill="#f44336" name="Error Rate %" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Recent Reconciliations</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Reconciliation ID</TableCell>
                    <TableCell>Date</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Transactions</TableCell>
                    <TableCell>Matched</TableCell>
                    <TableCell>Discrepancies</TableCell>
                    <TableCell>Amount</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reconciliations.map((recon) => (
                    <TableRow key={recon.id}>
                      <TableCell>{recon.id}</TableCell>
                      <TableCell>{recon.date}</TableCell>
                      <TableCell>
                        <Chip 
                          label={recon.status} 
                          color={getStatusColor(recon.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{recon.totalTransactions}</TableCell>
                      <TableCell>{recon.matchedTransactions}</TableCell>
                      <TableCell>{recon.unmatchedTransactions}</TableCell>
                      <TableCell>${recon.totalAmount.toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Outstanding Discrepancies</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Transaction ID</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Internal Amount</TableCell>
                    <TableCell>PSP Amount</TableCell>
                    <TableCell>Difference</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>PSP</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {discrepancies.map((disc) => (
                    <TableRow key={disc.id}>
                      <TableCell>{disc.id}</TableCell>
                      <TableCell>{disc.transactionId}</TableCell>
                      <TableCell>
                        <Chip 
                          label={disc.type.replace('_', ' ')} 
                          color={getDiscrepancyTypeColor(disc.type)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>${disc.internalAmount.toFixed(2)}</TableCell>
                      <TableCell>{disc.pspAmount ? `$${disc.pspAmount.toFixed(2)}` : 'N/A'}</TableCell>
                      <TableCell>
                        <Typography color={disc.difference > 0 ? 'error.main' : 'textPrimary'}>
                          ${Math.abs(disc.difference).toFixed(2)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={disc.status} 
                          color={disc.status === 'resolved' ? 'success' : disc.status === 'investigating' ? 'warning' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{disc.psp}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {activeTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Match Rate Trend</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={reconciliationTrendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis domain={[95, 100]} />
                    <Tooltip formatter={(value) => [`${value}%`, 'Match Rate']} />
                    <Line type="monotone" dataKey="matchRate" stroke="#2196f3" strokeWidth={3} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>PSP Volume Distribution</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={pspPerformanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="psp" />
                    <YAxis />
                    <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, 'Volume']} />
                    <Bar dataKey="volume" fill="#2196f3" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Reconciliation Result Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Reconciliation Results</DialogTitle>
        <DialogContent>
          {reconciliationResult?.error ? (
            <Alert severity="error">{reconciliationResult.error}</Alert>
          ) : reconciliationResult && (
            <Box>
              <Typography variant="body1" gutterBottom>
                <strong>Reconciliation ID:</strong> {reconciliationResult.reconciliation_id}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Status:</strong> {reconciliationResult.status}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Total Transactions:</strong> {reconciliationResult.total_transactions}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Matched:</strong> {reconciliationResult.matched_transactions}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Unmatched:</strong> {reconciliationResult.unmatched_transactions}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Total Amount:</strong> ${reconciliationResult.total_amount}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Reconciliation;