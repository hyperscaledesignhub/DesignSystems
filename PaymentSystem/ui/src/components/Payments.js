import React, { useState, useEffect } from 'react';
import {
  Paper, Typography, Box, Button, Table, TableBody, TableCell, 
  TableContainer, TableHead, TableRow, Chip, TextField, Grid,
  Dialog, DialogTitle, DialogContent, DialogActions, FormControl,
  InputLabel, Select, MenuItem
} from '@mui/material';
import { Add, Search } from '@mui/icons-material';
import axios from 'axios';

// Use proxy endpoints instead of direct API calls to avoid CORS issues

function Payments() {
  // Demo system - default user
  const DEFAULT_USER = 'testuser123';
  
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const [wallets, setWallets] = useState([]);
  const [loadingWallets, setLoadingWallets] = useState(false);
  const [newPayment, setNewPayment] = useState({
    amount: '',
    currency: 'USD',
    payment_method: 'card',
    wallet_id: ''
  });

  useEffect(() => {
    fetchPayments();
    loadWalletsForUser(DEFAULT_USER);
  }, []);

  const loadWalletsForUser = async (userId) => {
    if (!userId.trim()) {
      setWallets([]);
      return;
    }

    setLoadingWallets(true);
    try {
      // Try to get wallets for specific user (if API supports it)
      let userWallets = [];
      
      try {
        const response = await axios.get(`http://localhost:8740/api/v1/users/${userId}/wallets`);
        userWallets = response.data;
      } catch (error) {
        // If user-specific endpoint doesn't work, return empty array
        console.log('User-specific wallet endpoint failed, no wallets found for user:', userId);
        userWallets = [];
      }
      
      // Convert balance to number and filter active wallets
      const validWallets = userWallets
        .filter(wallet => wallet.status === 'active' && wallet.user_id === userId)
        .map(wallet => ({
          ...wallet,
          balance: parseFloat(wallet.balance)
        }));
      
      setWallets(validWallets);
      
      if (validWallets.length === 0) {
        console.log(`No active wallets found for user: ${userId}`);
      }
      
    } catch (error) {
      console.error('Failed to load wallets for user:', error);
      setWallets([]);
    }
    setLoadingWallets(false);
  };


  const fetchPayments = async () => {
    try {
      // Get payments from localStorage and wallet transactions
      const storedPayments = JSON.parse(localStorage.getItem('payments') || '[]');
      // Ensure storedPayments is an array
      const paymentsArray = Array.isArray(storedPayments) ? storedPayments : [];
      
      // Also fetch wallet transactions that look like payments
      try {
        const wallets = await axios.get(`http://localhost:8740/api/v1/users/${DEFAULT_USER}/wallets`);
        let paymentTransactions = [];
        
        for (const wallet of wallets.data) {
          try {
            const txResponse = await axios.get(`http://localhost:8740/api/v1/wallets/${wallet.wallet_id}/transactions`);
            const payments = txResponse.data
              .filter(tx => tx.description && tx.description.includes('Payment via'))
              .map(tx => ({
                payment_id: tx.reference_id || tx.transaction_id,
                user_id: tx.description.match(/for user (\w+)/)?.[1] || 'unknown',
                amount: Math.abs(parseFloat(tx.amount)),
                currency: 'USD',
                status: tx.status || 'completed',
                payment_method: tx.description.includes('card') ? 'card' : 
                              tx.description.includes('bank') ? 'bank_transfer' : 'card',
                created_at: tx.created_at
              }));
            paymentTransactions = [...paymentTransactions, ...payments];
          } catch (txError) {
            console.log(`No transactions found for wallet ${wallet.wallet_id}`);
          }
        }
        
        // Combine stored payments with transaction-based payments
        const allPayments = [...paymentsArray, ...paymentTransactions];
        
        // Remove duplicates based on payment_id
        const uniquePayments = allPayments.reduce((acc, payment) => {
          if (!acc.find(p => p.payment_id === payment.payment_id)) {
            acc.push(payment);
          }
          return acc;
        }, []);
        
        // Sort by created date
        uniquePayments.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        setPayments(uniquePayments);
      } catch (apiError) {
        console.error('Error fetching wallet transactions:', apiError);
        setPayments(paymentsArray);
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching payments:', error);
      setPayments([]);
      setLoading(false);
    }
  };

  const createPayment = async () => {
    if (!newPayment.amount || !newPayment.wallet_id) {
      alert('Please fill in amount and select a wallet');
      return;
    }
    
    const amount = parseFloat(newPayment.amount);
    if (isNaN(amount) || amount <= 0) {
      alert('Please enter a valid amount greater than 0');
      return;
    }

    // Check if selected wallet has sufficient balance
    const selectedWallet = wallets.find(w => w.wallet_id === newPayment.wallet_id);
    if (!selectedWallet) {
      alert('Selected wallet not found');
      return;
    }

    if (selectedWallet.balance < amount) {
      alert(`Insufficient balance. Available: $${selectedWallet.balance.toFixed(2)}, Required: $${amount.toFixed(2)}`);
      return;
    }
    
    try {
      // For now, create a merchant wallet to simulate payment (in real scenario, this would be the merchant's wallet)
      let merchantWallet;
      try {
        // Try to get existing merchant wallet
        merchantWallet = await axios.get('http://localhost:8740/api/v1/wallets/WLT20250831000000merchant');
      } catch (error) {
        // Create merchant wallet if it doesn't exist
        const merchantResponse = await axios.post('http://localhost:8740/api/v1/wallets', {
          user_id: 'merchant_system',
          currency: 'USD', 
          initial_balance: 0.00,
          wallet_type: 'business'
        });
        merchantWallet = { data: merchantResponse.data };
      }

      // Create a payment by transferring from user wallet to merchant wallet
      const transactionResponse = await axios.post('http://localhost:8740/api/v1/wallets/transfer', {
        from_wallet_id: newPayment.wallet_id,
        to_wallet_id: merchantWallet.data.wallet_id,
        amount: amount,
        description: `Payment via ${newPayment.payment_method} for user ${DEFAULT_USER}`
      });
      
      // Store payment in localStorage for immediate display
      const paymentRecord = {
        payment_id: transactionResponse.data?.transfer_id || `PAY${Date.now()}`,
        user_id: DEFAULT_USER,
        amount: amount,
        currency: newPayment.currency,
        status: 'completed',
        payment_method: newPayment.payment_method,
        created_at: new Date().toISOString()
      };
      
      const existingPayments = JSON.parse(localStorage.getItem('payments') || '[]');
      // Ensure existingPayments is an array
      const paymentsArray = Array.isArray(existingPayments) ? existingPayments : [];
      paymentsArray.unshift(paymentRecord);
      localStorage.setItem('payments', JSON.stringify(paymentsArray));
      
      // Create notification for the payment
      const notification = {
        id: `PAYMENT_${paymentRecord.payment_id}`,
        type: 'payment_success',
        title: 'Payment Processed Successfully',
        message: `Payment of $${amount.toFixed(2)} processed successfully via ${newPayment.payment_method} for user ${DEFAULT_USER}`,
        timestamp: new Date().toISOString(),
        read: false,
        priority: amount > 1000 ? 'high' : 'normal',
        channel: amount > 500 ? 'sms' : 'email',
        user: DEFAULT_USER
      };
      
      const existingNotifications = JSON.parse(localStorage.getItem('notifications') || '[]');
      // Ensure existingNotifications is an array
      const notificationsArray = Array.isArray(existingNotifications) ? existingNotifications : [];
      notificationsArray.unshift(notification);
      localStorage.setItem('notifications', JSON.stringify(notificationsArray));
      
      alert(`Payment of $${amount.toFixed(2)} processed successfully via ${newPayment.payment_method}!`);
      
      setOpenDialog(false);
      setNewPayment({ amount: '', currency: 'USD', payment_method: 'card', wallet_id: '' });
      loadWalletsForUser(DEFAULT_USER); // Reload wallets after payment
      fetchPayments();
    } catch (error) {
      console.error('Error creating payment:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      alert(`Failed to process payment: ${errorMessage}`);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'failed': return 'error';
      case 'pending': return 'warning';
      default: return 'default';
    }
  };

  const filteredPayments = payments.filter(payment =>
    payment.payment_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    payment.user_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Payments Management
      </Typography>
      
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            placeholder="Search payments..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <Search />
            }}
          />
        </Grid>
        <Grid item xs={12} md={6} display="flex" justifyContent="flex-end">
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setOpenDialog(true)}
          >
            Create Payment
          </Button>
        </Grid>
      </Grid>

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Payment ID</TableCell>
                <TableCell>User ID</TableCell>
                <TableCell>Amount</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Method</TableCell>
                <TableCell>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredPayments.map((payment) => (
                <TableRow key={payment.payment_id}>
                  <TableCell sx={{ fontFamily: 'monospace' }}>
                    {payment.payment_id}
                  </TableCell>
                  <TableCell>{payment.user_id}</TableCell>
                  <TableCell>
                    ${payment.amount} {payment.currency}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={payment.status}
                      color={getStatusColor(payment.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{payment.payment_method}</TableCell>
                  <TableCell>
                    {new Date(payment.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Dialog 
        open={openDialog} 
        onClose={() => {
          setOpenDialog(false);
          setNewPayment({ amount: '', currency: 'USD', payment_method: 'card', wallet_id: '' });
        }} 
        maxWidth="sm" 
        fullWidth
      >
        <DialogTitle>Create New Payment</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Creating payment for user: <strong>{DEFAULT_USER}</strong>
          </Typography>
          <FormControl fullWidth margin="normal" disabled={loadingWallets}>
            <InputLabel>
              {loadingWallets ? 'Loading Wallets...' : 
               wallets.length === 0 ? 'No Wallets Available' : 'Select Wallet'}
            </InputLabel>
            <Select
              value={newPayment.wallet_id}
              label={loadingWallets ? 'Loading Wallets...' : 
                     wallets.length === 0 ? 'No Wallets Available' : 'Select Wallet'}
              onChange={(e) => setNewPayment({...newPayment, wallet_id: e.target.value})}
              disabled={loadingWallets || wallets.length === 0}
            >
              {wallets.map((wallet) => (
                <MenuItem key={wallet.wallet_id} value={wallet.wallet_id}>
                  {wallet.wallet_id.substring(0, 20)}... (Balance: ${wallet.balance.toFixed(2)})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {!loadingWallets && wallets.length === 0 && (
            <Typography variant="caption" color="error" sx={{ mt: 1, display: 'block' }}>
              No active wallets found for user "{DEFAULT_USER}". 
              Please create a wallet for this user first.
            </Typography>
          )}
          <TextField
            fullWidth
            label="Amount"
            type="number"
            value={newPayment.amount}
            onChange={(e) => setNewPayment({...newPayment, amount: e.target.value})}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Currency"
            value={newPayment.currency}
            onChange={(e) => setNewPayment({...newPayment, currency: e.target.value})}
            margin="normal"
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Payment Method</InputLabel>
            <Select
              value={newPayment.payment_method}
              label="Payment Method"
              onChange={(e) => setNewPayment({...newPayment, payment_method: e.target.value})}
            >
              <MenuItem value="card">Credit Card</MenuItem>
              <MenuItem value="bank_transfer">Bank Transfer</MenuItem>
              <MenuItem value="wallet">Wallet</MenuItem>
              <MenuItem value="cash">Cash</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setOpenDialog(false);
            setNewPayment({ amount: '', currency: 'USD', payment_method: 'card', wallet_id: '' });
          }}>Cancel</Button>
          <Button onClick={createPayment} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Payments;