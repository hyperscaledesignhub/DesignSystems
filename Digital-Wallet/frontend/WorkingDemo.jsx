import React, { useState, useEffect } from 'react';

// Simple API calls
const API_BASE = 'http://localhost:9080/api/v1';

const WorkingDemo = () => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [wallets, setWallets] = useState([]);
  const [email, setEmail] = useState('deposit_test@example.com');
  const [password, setPassword] = useState('test123');
  const [selectedWallet, setSelectedWallet] = useState(null);
  const [depositAmount, setDepositAmount] = useState('10.00');
  const [withdrawAmount, setWithdrawAmount] = useState('5.00');
  const [status, setStatus] = useState('');
  const [transactions, setTransactions] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  // Simple fetch wrapper
  const apiFetch = async (url, options = {}) => {
    const response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
    });
    
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.message || 'API Error');
    }
    return data;
  };

  // Login
  const handleLogin = async () => {
    try {
      setStatus('Logging in...');
      const data = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      
      setToken(data.access_token);
      setUser({ user_id: data.user_id, email });
      setStatus('Login successful!');
    } catch (error) {
      setStatus(`Login failed: ${error.message}`);
    }
  };

  // Register
  const handleRegister = async () => {
    try {
      setStatus('Registering...');
      await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          full_name: email.split('@')[0],
        }),
      });
      setStatus('Registration successful! Now login.');
    } catch (error) {
      setStatus(`Registration failed: ${error.message}`);
    }
  };

  // Get wallets
  const fetchWallets = async () => {
    if (!user) return;
    
    try {
      setStatus('Fetching wallets...');
      const data = await apiFetch(`/wallets/user/${user.user_id}`);
      setWallets(data.wallets || []);
      if (data.wallets && data.wallets.length > 0) {
        setSelectedWallet(data.wallets[0]);
      }
      setStatus(`Found ${data.wallets?.length || 0} wallets`);
    } catch (error) {
      setStatus(`Fetch wallets failed: ${error.message}`);
    }
  };

  // Create wallet
  const handleCreateWallet = async () => {
    if (!user) return;
    
    try {
      setStatus('Creating wallet...');
      await apiFetch('/wallets', {
        method: 'POST',
        body: JSON.stringify({
          user_id: user.user_id,
          currency: 'USD',
        }),
      });
      setStatus('Wallet created successfully!');
      await fetchWallets();
    } catch (error) {
      setStatus(`Create wallet failed: ${error.message}`);
    }
  };

  // Deposit
  const handleDeposit = async () => {
    if (!selectedWallet || !depositAmount) {
      setStatus('Please select wallet and enter amount');
      return;
    }

    try {
      setStatus('Processing deposit...');
      
      // Generate UUID
      const idempotencyKey = crypto.randomUUID();
      
      const response = await apiFetch('/deposits', {
        method: 'POST',
        body: JSON.stringify({
          wallet_id: selectedWallet.wallet_id,
          amount: parseFloat(depositAmount),
          currency: 'USD',
          idempotency_key: idempotencyKey,
        }),
      });

      setStatus(`Deposit successful! Transaction: ${response.transaction_id}`);
      
      // Refresh wallets and transaction history
      setTimeout(() => {
        fetchWallets();
        if (showHistory) fetchTransactionHistory();
      }, 1000);
    } catch (error) {
      setStatus(`Deposit failed: ${error.message}`);
      console.error('Deposit error:', error);
    }
  };

  // Withdraw
  const handleWithdraw = async () => {
    if (!selectedWallet || !withdrawAmount) {
      setStatus('Please select wallet and enter amount');
      return;
    }

    const amount = parseFloat(withdrawAmount);
    const currentBalance = parseFloat(selectedWallet.balance);
    
    if (amount > currentBalance) {
      setStatus('Insufficient balance for withdrawal');
      return;
    }

    try {
      setStatus('Processing withdrawal...');
      
      // Generate UUID
      const idempotencyKey = crypto.randomUUID();
      
      const response = await apiFetch('/withdrawals', {
        method: 'POST',
        body: JSON.stringify({
          wallet_id: selectedWallet.wallet_id,
          amount: amount,
          currency: 'USD',
          idempotency_key: idempotencyKey,
        }),
      });

      setStatus(`Withdrawal successful! Transaction: ${response.transaction_id}`);
      
      // Refresh wallets and transaction history
      setTimeout(() => {
        fetchWallets();
        if (showHistory) fetchTransactionHistory();
      }, 1000);
    } catch (error) {
      setStatus(`Withdrawal failed: ${error.message}`);
      console.error('Withdrawal error:', error);
    }
  };

  // Fetch transaction history
  const fetchTransactionHistory = async () => {
    if (!selectedWallet) return;
    
    try {
      setStatus('Loading transaction history...');
      const data = await apiFetch(`/transfers/wallet/${selectedWallet.wallet_id}`);
      setTransactions(data.transactions || []);
      setStatus(`Loaded ${data.transactions?.length || 0} transactions`);
    } catch (error) {
      setStatus(`Failed to load transaction history: ${error.message}`);
      console.error('Transaction history error:', error);
    }
  };

  // Toggle transaction history
  const toggleTransactionHistory = async () => {
    if (!showHistory) {
      setShowHistory(true);
      await fetchTransactionHistory();
    } else {
      setShowHistory(false);
      setTransactions([]);
    }
  };

  // Auto-fetch wallets when user logs in
  useEffect(() => {
    if (user) {
      fetchWallets();
    }
  }, [user]);

  const containerStyle = {
    maxWidth: '600px',
    margin: '20px auto',
    padding: '20px',
    fontFamily: 'Arial, sans-serif',
  };

  const sectionStyle = {
    marginBottom: '30px',
    padding: '20px',
    border: '1px solid #ddd',
    borderRadius: '5px',
    backgroundColor: '#f9f9f9',
  };

  const inputStyle = {
    width: '200px',
    padding: '8px',
    margin: '5px',
    borderRadius: '4px',
    border: '1px solid #ccc',
  };

  const buttonStyle = {
    padding: '10px 20px',
    margin: '5px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  };

  const walletStyle = {
    padding: '10px',
    margin: '5px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    cursor: 'pointer',
    backgroundColor: '#fff',
  };

  return (
    <div style={containerStyle}>
      <h1>Digital Wallet - Working Demo</h1>
      
      {/* Status */}
      <div style={{...sectionStyle, backgroundColor: '#e9ecef'}}>
        <strong>Status:</strong> {status}
      </div>

      {/* Login Section */}
      {!user && (
        <div style={sectionStyle}>
          <h2>Login / Register</h2>
          <div>
            <input
              style={inputStyle}
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              style={inputStyle}
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div>
            <button style={buttonStyle} onClick={handleLogin}>
              Login
            </button>
            <button style={{...buttonStyle, backgroundColor: '#28a745'}} onClick={handleRegister}>
              Register
            </button>
          </div>
        </div>
      )}

      {/* Wallet Section */}
      {user && (
        <div style={sectionStyle}>
          <h2>Wallets for {user.email}</h2>
          <div>
            <button style={buttonStyle} onClick={handleCreateWallet}>
              Create New Wallet
            </button>
            <button style={{...buttonStyle, backgroundColor: '#17a2b8'}} onClick={fetchWallets}>
              Refresh Wallets
            </button>
          </div>
          
          {wallets.length === 0 ? (
            <p>No wallets found. Create one above.</p>
          ) : (
            <div>
              <h3>Your Wallets:</h3>
              {wallets.map((wallet) => (
                <div
                  key={wallet.wallet_id}
                  style={{
                    ...walletStyle,
                    backgroundColor: selectedWallet?.wallet_id === wallet.wallet_id ? '#cce5ff' : '#fff',
                  }}
                  onClick={() => setSelectedWallet(wallet)}
                >
                  <div><strong>ID:</strong> {wallet.wallet_id.substring(0, 16)}...</div>
                  <div><strong>Balance:</strong> ${wallet.balance}</div>
                  <div><strong>Currency:</strong> {wallet.currency}</div>
                  <div><strong>Status:</strong> {wallet.status}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Deposit & Withdraw Section */}
      {selectedWallet && (
        <div style={sectionStyle}>
          <h2>Deposit / Withdraw</h2>
          <div><strong>Selected:</strong> {selectedWallet.wallet_id.substring(0, 16)}...</div>
          <div><strong>Current Balance:</strong> ${selectedWallet.balance}</div>
          
          {/* Deposit */}
          <div style={{marginTop: '15px', borderTop: '1px solid #ccc', paddingTop: '15px'}}>
            <h3>Deposit Money</h3>
            <input
              style={inputStyle}
              type="number"
              placeholder="Deposit Amount"
              value={depositAmount}
              onChange={(e) => setDepositAmount(e.target.value)}
              step="0.01"
              min="0.01"
            />
            <button style={{...buttonStyle, backgroundColor: '#28a745'}} onClick={handleDeposit}>
              Deposit
            </button>
          </div>

          {/* Withdraw */}
          <div style={{marginTop: '15px', borderTop: '1px solid #ccc', paddingTop: '15px'}}>
            <h3>Withdraw Money</h3>
            <input
              style={inputStyle}
              type="number"
              placeholder="Withdraw Amount"
              value={withdrawAmount}
              onChange={(e) => setWithdrawAmount(e.target.value)}
              step="0.01"
              min="0.01"
              max={selectedWallet.balance}
            />
            <button 
              style={{...buttonStyle, backgroundColor: '#dc3545'}} 
              onClick={handleWithdraw}
              disabled={parseFloat(withdrawAmount) > parseFloat(selectedWallet.balance)}
            >
              Withdraw
            </button>
            {parseFloat(withdrawAmount) > parseFloat(selectedWallet.balance) && (
              <div style={{color: '#dc3545', fontSize: '12px', marginTop: '5px'}}>
                Insufficient balance (Available: ${selectedWallet.balance})
              </div>
            )}
          </div>
        </div>
      )}

      {/* Transaction History Section */}
      {selectedWallet && (
        <div style={sectionStyle}>
          <h2>Transaction History</h2>
          <div><strong>Wallet:</strong> {selectedWallet.wallet_id.substring(0, 16)}...</div>
          
          <div style={{marginTop: '15px'}}>
            <button 
              style={{...buttonStyle, backgroundColor: '#17a2b8'}} 
              onClick={toggleTransactionHistory}
            >
              {showHistory ? 'Hide History' : 'Show Transaction History'}
            </button>
          </div>

          {showHistory && (
            <div style={{marginTop: '20px'}}>
              {transactions.length === 0 ? (
                <p style={{color: '#666'}}>No transactions found</p>
              ) : (
                <div>
                  <h3>Recent Transactions ({transactions.length})</h3>
                  <div style={{maxHeight: '400px', overflowY: 'auto', border: '1px solid #ddd', borderRadius: '4px'}}>
                    {transactions.map((transaction, index) => (
                      <div
                        key={transaction.transaction_id || index}
                        style={{
                          padding: '12px',
                          borderBottom: index < transactions.length - 1 ? '1px solid #eee' : 'none',
                          backgroundColor: index % 2 === 0 ? '#f9f9f9' : '#fff'
                        }}
                      >
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                          <div>
                            <div style={{fontWeight: 'bold', fontSize: '14px'}}>
                              {transaction.transaction_type?.toUpperCase() || 'TRANSACTION'}
                            </div>
                            <div style={{fontSize: '12px', color: '#666'}}>
                              {transaction.transaction_id?.substring(0, 12)}...
                            </div>
                            <div style={{fontSize: '12px', color: '#666'}}>
                              {new Date(transaction.created_at).toLocaleString()}
                            </div>
                          </div>
                          <div style={{textAlign: 'right'}}>
                            <div style={{
                              fontWeight: 'bold',
                              fontSize: '16px',
                              color: transaction.transaction_type === 'deposit' ? '#28a745' : 
                                     transaction.transaction_type === 'withdraw' ? '#dc3545' : 
                                     transaction.from_wallet_id === selectedWallet.wallet_id ? '#dc3545' : '#28a745'
                            }}>
                              {transaction.transaction_type === 'deposit' ? '+' : 
                               transaction.transaction_type === 'withdraw' ? '-' : 
                               transaction.from_wallet_id === selectedWallet.wallet_id ? '-' : '+'}
                              ${transaction.amount}
                            </div>
                            <div style={{
                              fontSize: '12px',
                              padding: '2px 6px',
                              borderRadius: '3px',
                              backgroundColor: 
                                transaction.status === 'completed' ? '#d4edda' : 
                                transaction.status === 'failed' ? '#f8d7da' : '#fff3cd',
                              color:
                                transaction.status === 'completed' ? '#155724' :
                                transaction.status === 'failed' ? '#721c24' : '#856404'
                            }}>
                              {transaction.status?.toUpperCase() || 'PENDING'}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WorkingDemo;