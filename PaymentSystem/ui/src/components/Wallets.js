import React, { useState, useEffect } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tabs,
  Tab,
  LinearProgress
} from '@mui/material';
import {
  AccountBalanceWallet as WalletIcon,
  Add as AddIcon,
  Send as SendIcon,
  Receipt as TransactionIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import axios from 'axios';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

function Wallets() {
  // Demo system - default user (same as in Payments.js)
  const DEFAULT_USER = 'testuser123';
  
  const [activeTab, setActiveTab] = useState(0);
  const [wallets, setWallets] = useState([
    {
      wallet_id: 'WLT20250830070333test',
      user_id: 'user123',
      balance: 1000.00,
      currency: 'USD',
      status: 'active',
      created_at: '2025-08-30T07:03:33Z',
      last_transaction: '2025-08-30T07:03:33Z'
    }
  ]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openCreateDialog, setOpenCreateDialog] = useState(false);
  const [openTransferDialog, setOpenTransferDialog] = useState(false);
  const [createForm, setCreateForm] = useState({
    initial_balance: '',
    wallet_type: 'personal'
  });
  const [transferForm, setTransferForm] = useState({
    from_wallet: '',
    to_wallet: '',
    amount: '',
    description: ''
  });
  const [alert, setAlert] = useState(null);

  const walletStats = {
    totalWallets: wallets.length,
    activeWallets: wallets.filter(w => w.status === 'active').length,
    totalBalance: wallets.reduce((sum, w) => sum + w.balance, 0),
    averageBalance: wallets.length ? wallets.reduce((sum, w) => sum + w.balance, 0) / wallets.length : 0
  };

  const balanceDistributionData = [
    { range: '$0-100', count: 15, color: '#FF8042' },
    { range: '$100-500', count: 25, color: '#FFBB28' },
    { range: '$500-1000', count: 18, color: '#00C49F' },
    { range: '$1000-5000', count: 12, color: '#0088FE' },
    { range: '$5000+', count: 5, color: '#8884D8' }
  ];

  const dailyTransactionData = [
    { date: '08-24', transactions: 45, volume: 12500 },
    { date: '08-25', transactions: 52, volume: 15800 },
    { date: '08-26', transactions: 38, volume: 9200 },
    { date: '08-27', transactions: 67, volume: 18900 },
    { date: '08-28', transactions: 41, volume: 11200 },
    { date: '08-29', transactions: 58, volume: 16400 },
    { date: '08-30', transactions: 23, volume: 8100 }
  ];

  const createWallet = async () => {
    if (!createForm.initial_balance) {
      setAlert({ type: 'error', message: 'Please enter an initial balance' });
      return;
    }

    // Validate initial balance
    const initialBalance = parseFloat(createForm.initial_balance);
    if (isNaN(initialBalance) || initialBalance < 0) {
      setAlert({ type: 'error', message: 'Please enter a valid initial balance (0 or greater)' });
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8740/api/v1/wallets', {
        user_id: DEFAULT_USER,
        currency: 'USD',
        initial_balance: initialBalance,
        wallet_type: createForm.wallet_type || 'personal'
      });

      // Add the new wallet to the existing list
      const newWallet = {
        ...response.data,
        balance: parseFloat(response.data.balance)
      };
      setWallets(prev => [newWallet, ...prev]);
      
      // Save the new wallet ID to localStorage for future loads
      const createdWallets = JSON.parse(localStorage.getItem('createdWallets') || '[]');
      createdWallets.push(response.data.wallet_id);
      localStorage.setItem('createdWallets', JSON.stringify(createdWallets));
      
      setCreateForm({ initial_balance: '', wallet_type: 'personal' });
      setOpenCreateDialog(false);
      setAlert({ type: 'success', message: `Wallet ${response.data.wallet_id} created successfully!` });
    } catch (error) {
      console.error('Wallet creation failed:', error);
      let errorMessage = 'Failed to create wallet. Please try again.';
      
      if (error.response) {
        // Server responded with error status
        if (error.response.data?.detail) {
          if (typeof error.response.data.detail === 'string') {
            errorMessage = error.response.data.detail;
          } else if (Array.isArray(error.response.data.detail)) {
            // Handle FastAPI validation errors
            const validationErrors = error.response.data.detail.map(err => 
              `${err.loc?.join('.')} - ${err.msg}`
            ).join(', ');
            errorMessage = `Validation error: ${validationErrors}`;
          }
        } else if (error.response.data?.message) {
          errorMessage = error.response.data.message;
        } else {
          errorMessage = `Server error (${error.response.status}): ${error.response.statusText}`;
        }
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = 'Cannot connect to wallet service. Please make sure the wallet service is running on port 8740.';
      } else {
        // Something else happened
        errorMessage = `Request error: ${error.message}`;
      }
      
      setAlert({ type: 'error', message: errorMessage });
    }
    setLoading(false);
  };

  const transferFunds = async () => {
    if (!transferForm.from_wallet || !transferForm.to_wallet || !transferForm.amount) {
      setAlert({ type: 'error', message: 'Please fill in all required fields' });
      return;
    }

    // Validate amount
    const amount = parseFloat(transferForm.amount);
    if (isNaN(amount) || amount <= 0) {
      setAlert({ type: 'error', message: 'Please enter a valid amount greater than 0' });
      return;
    }

    if (transferForm.from_wallet === transferForm.to_wallet) {
      setAlert({ type: 'error', message: 'Cannot transfer to the same wallet' });
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8740/api/v1/wallets/transfer', {
        from_wallet_id: transferForm.from_wallet,
        to_wallet_id: transferForm.to_wallet,
        amount: amount,
        description: transferForm.description || 'Wallet transfer'
      });

      // Refresh wallets after transfer
      await loadWallets();
      setTransferForm({ from_wallet: '', to_wallet: '', amount: '', description: '' });
      setOpenTransferDialog(false);
      setAlert({ type: 'success', message: `Transfer of $${amount.toFixed(2)} completed successfully!` });
    } catch (error) {
      console.error('Transfer failed:', error);
      let errorMessage = 'Transfer failed. Please check wallet balances and try again.';
      
      if (error.response) {
        if (error.response.data?.detail) {
          if (typeof error.response.data.detail === 'string') {
            errorMessage = error.response.data.detail;
          } else if (Array.isArray(error.response.data.detail)) {
            const validationErrors = error.response.data.detail.map(err => 
              `${err.loc?.join('.')} - ${err.msg}`
            ).join(', ');
            errorMessage = `Validation error: ${validationErrors}`;
          }
        } else if (error.response.data?.message) {
          errorMessage = error.response.data.message;
        } else {
          errorMessage = `Transfer failed (${error.response.status}): ${error.response.statusText}`;
        }
      } else if (error.request) {
        errorMessage = 'Cannot connect to wallet service. Please make sure the wallet service is running.';
      }
      
      setAlert({ type: 'error', message: errorMessage });
    }
    setLoading(false);
  };

  const loadWallets = async () => {
    setLoading(true);
    try {
      // Load demo wallets - in a real app, this would be a proper "list all wallets" API
      const knownWalletIds = [
        'WLT20250830084402test',
        'WLT20250830105220newu', 
        'WLT20250830111608test',
        'WLT20250830115319test'
      ];
      
      // Get created wallet IDs from localStorage for persistence
      const createdWallets = JSON.parse(localStorage.getItem('createdWallets') || '[]');
      const allWalletIds = [...new Set([...knownWalletIds, ...createdWallets])];
      
      const walletPromises = allWalletIds.map(async (walletId) => {
        try {
          const response = await axios.get(`http://localhost:8740/api/v1/wallets/${walletId}`);
          return {
            ...response.data,
            balance: parseFloat(response.data.balance)
          };
        } catch (error) {
          console.warn(`Failed to load wallet ${walletId}:`, error);
          return null;
        }
      });
      
      const walletResults = await Promise.all(walletPromises);
      const validWallets = walletResults.filter(wallet => wallet !== null);
      
      setWallets(validWallets);
      setAlert({ type: 'success', message: `Loaded ${validWallets.length} wallets successfully` });
    } catch (error) {
      console.error('Failed to load wallets:', error);
      setAlert({ type: 'error', message: 'Failed to load wallets from server' });
    }
    setLoading(false);
  };

  const loadTransactions = async (walletId) => {
    try {
      const response = await axios.get(`http://localhost:8740/api/v1/wallets/${walletId}/transactions`);
      if (response.data && Array.isArray(response.data)) {
        setTransactions(response.data);
      }
    } catch (error) {
      console.error('Failed to load transactions:', error);
      setAlert({ type: 'error', message: 'Failed to load transactions' });
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'success';
      case 'frozen': return 'warning';
      case 'closed': return 'error';
      default: return 'default';
    }
  };

  const formatCurrency = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  useEffect(() => {
    loadWallets();
  }, []);

  useEffect(() => {
    if (alert) {
      const timer = setTimeout(() => setAlert(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [alert]);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          💰 Wallet Management
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadWallets}
            sx={{ mr: 2 }}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenCreateDialog(true)}
          >
            Create Wallet
          </Button>
        </Box>
      </Box>

      {alert && (
        <Alert severity={alert.type} sx={{ mb: 3 }} onClose={() => setAlert(null)}>
          {alert.message}
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Total Wallets</Typography>
              <Typography variant="h3" color="primary">{walletStats.totalWallets}</Typography>
              <Typography variant="body2" color="textSecondary">
                {walletStats.activeWallets} active
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Total Balance</Typography>
              <Typography variant="h3" color="success.main">
                {formatCurrency(walletStats.totalBalance)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Across all wallets
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Average Balance</Typography>
              <Typography variant="h3" color="info.main">
                {formatCurrency(walletStats.averageBalance)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Per wallet
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary">Today's Transactions</Typography>
              <Typography variant="h3" color="warning.main">23</Typography>
              <Typography variant="body2" color="textSecondary">
                {formatCurrency(8100)} volume
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} sx={{ mb: 3 }}>
        <Tab label="All Wallets" />
        <Tab label="Transactions" />
        <Tab label="Analytics" />
      </Tabs>

      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">Active Wallets</Typography>
                  <Button
                    variant="contained"
                    startIcon={<SendIcon />}
                    onClick={() => setOpenTransferDialog(true)}
                    disabled={wallets.length < 2}
                  >
                    Transfer Funds
                  </Button>
                </Box>
                
                {loading && <LinearProgress sx={{ mb: 2 }} />}
                
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Wallet ID</TableCell>
                        <TableCell>User ID</TableCell>
                        <TableCell>Balance</TableCell>
                        <TableCell>Currency</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Created</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {wallets.map((wallet) => (
                        <TableRow key={wallet.wallet_id}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <WalletIcon sx={{ mr: 1 }} />
                              {wallet.wallet_id}
                            </Box>
                          </TableCell>
                          <TableCell>{wallet.user_id}</TableCell>
                          <TableCell>
                            <Typography variant="h6" color="success.main">
                              {formatCurrency(wallet.balance, wallet.currency)}
                            </Typography>
                          </TableCell>
                          <TableCell>{wallet.currency}</TableCell>
                          <TableCell>
                            <Chip
                              label={wallet.status}
                              color={getStatusColor(wallet.status)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>{formatDate(wallet.created_at)}</TableCell>
                          <TableCell>
                            <IconButton
                              size="small"
                              onClick={() => loadTransactions(wallet.wallet_id)}
                              title="View Transactions"
                            >
                              <TransactionIcon />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                      {wallets.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={7}>
                            <Box sx={{ textAlign: 'center', py: 4 }}>
                              <Typography color="textSecondary">
                                No wallets found. Create your first wallet to get started.
                              </Typography>
                            </Box>
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
      )}

      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Recent Transactions</Typography>
                {transactions.length > 0 ? (
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Transaction ID</TableCell>
                          <TableCell>Type</TableCell>
                          <TableCell>Amount</TableCell>
                          <TableCell>Description</TableCell>
                          <TableCell>Date</TableCell>
                          <TableCell>Status</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {transactions.map((tx) => (
                          <TableRow key={tx.transaction_id}>
                            <TableCell>{tx.transaction_id}</TableCell>
                            <TableCell>
                              <Chip
                                label={tx.type}
                                color={tx.type === 'credit' ? 'success' : 'warning'}
                                size="small"
                                icon={tx.type === 'credit' ? <TrendingUpIcon /> : <TrendingDownIcon />}
                              />
                            </TableCell>
                            <TableCell>
                              <Typography color={tx.type === 'credit' ? 'success.main' : 'error.main'}>
                                {tx.type === 'credit' ? '+' : '-'}{formatCurrency(Math.abs(tx.amount))}
                              </Typography>
                            </TableCell>
                            <TableCell>{tx.description}</TableCell>
                            <TableCell>{formatDate(tx.created_at)}</TableCell>
                            <TableCell>
                              <Chip label="completed" color="success" size="small" />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Alert severity="info">
                    Select a wallet from the "All Wallets" tab to view its transactions.
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Daily Transaction Trends</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dailyTransactionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis yAxisId="left" orientation="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="transactions" fill="#8884d8" name="Transactions" />
                    <Line yAxisId="right" type="monotone" dataKey="volume" stroke="#82ca9d" strokeWidth={2} name="Volume ($)" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Balance Distribution</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={balanceDistributionData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="count"
                      label={({range, count}) => `${range}: ${count}`}
                    >
                      {balanceDistributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Create Wallet Dialog */}
      <Dialog open={openCreateDialog} onClose={() => setOpenCreateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Wallet</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              Creating wallet for user: <strong>{DEFAULT_USER}</strong>
            </Typography>
            <TextField
              fullWidth
              label="Initial Balance"
              type="number"
              value={createForm.initial_balance}
              onChange={(e) => setCreateForm({...createForm, initial_balance: e.target.value})}
              margin="normal"
              required
            />
            <FormControl fullWidth margin="normal">
              <InputLabel>Wallet Type</InputLabel>
              <Select
                value={createForm.wallet_type}
                label="Wallet Type"
                onChange={(e) => setCreateForm({...createForm, wallet_type: e.target.value})}
              >
                <MenuItem value="personal">Personal</MenuItem>
                <MenuItem value="business">Business</MenuItem>
                <MenuItem value="merchant">Merchant</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreateDialog(false)}>Cancel</Button>
          <Button onClick={createWallet} variant="contained" disabled={loading}>
            {loading ? 'Creating...' : 'Create Wallet'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Transfer Dialog */}
      <Dialog open={openTransferDialog} onClose={() => setOpenTransferDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Transfer Funds</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth margin="normal">
              <InputLabel>From Wallet</InputLabel>
              <Select
                value={transferForm.from_wallet}
                label="From Wallet"
                onChange={(e) => setTransferForm({...transferForm, from_wallet: e.target.value})}
              >
                {wallets.map((wallet) => (
                  <MenuItem key={wallet.wallet_id} value={wallet.wallet_id}>
                    {wallet.wallet_id} ({formatCurrency(wallet.balance)})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth margin="normal">
              <InputLabel>To Wallet</InputLabel>
              <Select
                value={transferForm.to_wallet}
                label="To Wallet"
                onChange={(e) => setTransferForm({...transferForm, to_wallet: e.target.value})}
              >
                {wallets.filter(w => w.wallet_id !== transferForm.from_wallet).map((wallet) => (
                  <MenuItem key={wallet.wallet_id} value={wallet.wallet_id}>
                    {wallet.wallet_id} ({formatCurrency(wallet.balance)})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Amount"
              type="number"
              value={transferForm.amount}
              onChange={(e) => setTransferForm({...transferForm, amount: e.target.value})}
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Description (Optional)"
              value={transferForm.description}
              onChange={(e) => setTransferForm({...transferForm, description: e.target.value})}
              margin="normal"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenTransferDialog(false)}>Cancel</Button>
          <Button onClick={transferFunds} variant="contained" disabled={loading}>
            {loading ? 'Processing...' : 'Transfer'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Wallets;