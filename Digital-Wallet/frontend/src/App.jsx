import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:9080/api/v1';

function App() {
  // Initialize from localStorage
  const storedToken = localStorage.getItem('token');
  const storedUser = localStorage.getItem('user');
  
  const [currentView, setCurrentView] = useState(storedToken ? 'dashboard' : 'login');
  const [user, setUser] = useState(storedUser ? JSON.parse(storedUser) : null);
  const [token, setToken] = useState(storedToken);
  const [wallets, setWallets] = useState([]);
  const [selectedWallet, setSelectedWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Form states
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ email: '', password: '', full_name: '' });
  const [transferForm, setTransferForm] = useState({ to_wallet: '', amount: '' });
  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');

  // API Helper
  const apiCall = async (endpoint, method = 'GET', body = null) => {
    try {
      const options = {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` })
        }
      };
      if (body) options.body = JSON.stringify(body);

      const response = await fetch(`${API_BASE}${endpoint}`, options);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || data.message || 'API Error');
      }
      return data;
    } catch (error) {
      setMessage(`Error: ${error.message}`);
      throw error;
    }
  };

  // 1. User Registration
  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiCall('/auth/register', 'POST', registerForm);
      setMessage('Registration successful! Please login.');
      setCurrentView('login');
    } catch (error) {
      setMessage(`Registration failed: ${error.message}`);
    }
    setLoading(false);
  };

  // 2. User Login
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await apiCall('/auth/login', 'POST', loginForm);
      const userData = { id: data.user_id, email: loginForm.email };
      
      // Store both token and user info
      setToken(data.access_token);
      localStorage.setItem('token', data.access_token);
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      
      setMessage('Login successful!');
      setCurrentView('dashboard');
    } catch (error) {
      setMessage(`Login failed: ${error.message}`);
    }
    setLoading(false);
  };

  // 3. Create Wallet
  const createWallet = async () => {
    setLoading(true);
    try {
      const data = await apiCall('/wallets', 'POST', {
        user_id: user.id,
        currency: 'USD'
      });
      setMessage(`Wallet created successfully! ID: ${data.wallet_id}`);
      await fetchWallets();
    } catch (error) {
      setMessage(`Failed to create wallet: ${error.message}`);
    }
    setLoading(false);
  };

  // 4. Fetch Wallets
  const fetchWallets = async () => {
    if (!user) return;
    try {
      const data = await apiCall(`/wallets/user/${user.id}`);
      setWallets(data.wallets || []);
      if (data.wallets?.length > 0 && !selectedWallet) {
        setSelectedWallet(data.wallets[0]);
      }
    } catch (error) {
      console.error('Failed to fetch wallets:', error);
    }
  };

  // 5. Transfer Money
  const handleTransfer = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const idempotencyKey = crypto.randomUUID();
      const data = await apiCall('/transfers', 'POST', {
        from_wallet_id: selectedWallet.wallet_id,
        to_wallet_id: transferForm.to_wallet,
        amount: parseFloat(transferForm.amount),
        currency: 'USD',
        idempotency_key: idempotencyKey
      });
      setMessage(`Transfer successful! Transaction ID: ${data.transaction_id}`);
      setTransferForm({ to_wallet: '', amount: '' });
      await fetchWallets();
      await fetchTransactions();
    } catch (error) {
      setMessage(`Transfer failed: ${error.message}`);
    }
    setLoading(false);
  };

  // Deposit Money
  const handleDeposit = async () => {
    setLoading(true);
    try {
      const idempotencyKey = crypto.randomUUID();
      const data = await apiCall('/deposits', 'POST', {
        wallet_id: selectedWallet.wallet_id,
        amount: parseFloat(depositAmount),
        currency: 'USD',
        idempotency_key: idempotencyKey
      });
      setMessage(`Deposit successful! Transaction ID: ${data.transaction_id}`);
      setDepositAmount('');
      await fetchWallets();
      await fetchTransactions();
    } catch (error) {
      setMessage(`Deposit failed: ${error.message}`);
    }
    setLoading(false);
  };

  // Withdraw Money
  const handleWithdraw = async () => {
    setLoading(true);
    try {
      const idempotencyKey = crypto.randomUUID();
      const data = await apiCall('/withdrawals', 'POST', {
        wallet_id: selectedWallet.wallet_id,
        amount: parseFloat(withdrawAmount),
        currency: 'USD',
        idempotency_key: idempotencyKey
      });
      setMessage(`Withdrawal successful! Transaction ID: ${data.transaction_id}`);
      setWithdrawAmount('');
      await fetchWallets();
      await fetchTransactions();
    } catch (error) {
      setMessage(`Withdrawal failed: ${error.message}`);
    }
    setLoading(false);
  };

  // Fetch Transactions
  const fetchTransactions = async () => {
    if (!selectedWallet) return;
    try {
      const data = await apiCall(`/transfers/wallet/${selectedWallet.wallet_id}`);
      setTransactions(data.transactions || []);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    }
  };

  // Logout
  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setWallets([]);
    setSelectedWallet(null);
    setTransactions([]);
    setCurrentView('login');
    setMessage('Logged out successfully');
  };

  // Auto-fetch data
  useEffect(() => {
    if (user) {
      fetchWallets();
    }
  }, [user]);

  useEffect(() => {
    if (selectedWallet) {
      fetchTransactions();
    }
  }, [selectedWallet]);

  // Validate token on mount
  useEffect(() => {
    const validateToken = async () => {
      if (token && user) {
        try {
          // Try to fetch wallets to validate token
          await fetchWallets();
        } catch (error) {
          // Token is invalid, clear everything
          handleLogout();
        }
      }
    };
    validateToken();
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🏦 Digital Wallet System</h1>
        {user && (
          <div className="user-info">
            <span>👤 {user.email}</span>
            <button onClick={handleLogout} className="btn-logout">Logout</button>
          </div>
        )}
      </header>

      {message && (
        <div className={`message ${message.includes('Error') || message.includes('failed') ? 'error' : 'success'}`}>
          {message}
          <button onClick={() => setMessage('')}>×</button>
        </div>
      )}

      <main className="app-main">
        {/* Login/Register View */}
        {currentView === 'login' && (
          <div className="auth-container">
            <div className="auth-card">
              <h2>Login</h2>
              <form onSubmit={handleLogin}>
                <input
                  type="email"
                  placeholder="Email"
                  value={loginForm.email}
                  onChange={(e) => setLoginForm({...loginForm, email: e.target.value})}
                  required
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                  required
                />
                <button type="submit" disabled={loading}>
                  {loading ? 'Loading...' : 'Login'}
                </button>
              </form>
              <p>
                Don't have an account? 
                <button onClick={() => setCurrentView('register')} className="link-btn">
                  Register
                </button>
              </p>
            </div>
          </div>
        )}

        {currentView === 'register' && (
          <div className="auth-container">
            <div className="auth-card">
              <h2>Register</h2>
              <form onSubmit={handleRegister}>
                <input
                  type="text"
                  placeholder="Full Name"
                  value={registerForm.full_name}
                  onChange={(e) => setRegisterForm({...registerForm, full_name: e.target.value})}
                  required
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={registerForm.email}
                  onChange={(e) => setRegisterForm({...registerForm, email: e.target.value})}
                  required
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={registerForm.password}
                  onChange={(e) => setRegisterForm({...registerForm, password: e.target.value})}
                  required
                />
                <button type="submit" disabled={loading}>
                  {loading ? 'Loading...' : 'Register'}
                </button>
              </form>
              <p>
                Already have an account? 
                <button onClick={() => setCurrentView('login')} className="link-btn">
                  Login
                </button>
              </p>
            </div>
          </div>
        )}

        {/* Dashboard View */}
        {currentView === 'dashboard' && (
          <div className="dashboard">
            {/* Wallets Section */}
            <div className="section">
              <div className="section-header">
                <h2>💳 My Wallets</h2>
                <button onClick={createWallet} className="btn-primary" disabled={loading}>
                  + Create Wallet
                </button>
              </div>
              
              <div className="wallets-grid">
                {wallets.length === 0 ? (
                  <p className="no-data">No wallets yet. Create your first wallet!</p>
                ) : (
                  wallets.map(wallet => (
                    <div
                      key={wallet.wallet_id}
                      className={`wallet-card ${selectedWallet?.wallet_id === wallet.wallet_id ? 'selected' : ''}`}
                      onClick={() => setSelectedWallet(wallet)}
                    >
                      <div className="wallet-id-full">
                        <span title={wallet.wallet_id}>ID: {wallet.wallet_id.substring(0, 8)}...</span>
                        <button 
                          className="copy-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigator.clipboard.writeText(wallet.wallet_id);
                            setMessage('Wallet ID copied!');
                            setTimeout(() => setMessage(''), 2000);
                          }}
                          title="Copy full wallet ID"
                        >
                          📋
                        </button>
                      </div>
                      <div className="wallet-balance">
                        ${wallet.balance}
                      </div>
                      <div className="wallet-info">
                        <span className="currency">{wallet.currency}</span>
                        <span className={`status ${wallet.status}`}>{wallet.status}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Operations Section */}
            {selectedWallet && (
              <>
                <div className="section">
                  <h2>💰 Operations</h2>
                  <div className="operations-grid">
                    {/* Deposit */}
                    <div className="operation-card">
                      <h3>💵 Deposit</h3>
                      <div className="balance-display">Current Balance: ${selectedWallet.balance}</div>
                      <input
                        type="number"
                        placeholder="Amount to deposit"
                        value={depositAmount}
                        onChange={(e) => setDepositAmount(e.target.value)}
                        step="0.01"
                        min="0.01"
                      />
                      <button 
                        onClick={handleDeposit} 
                        className="btn-success"
                        disabled={loading || !depositAmount}
                      >
                        Deposit Money
                      </button>
                    </div>

                    {/* Withdraw */}
                    <div className="operation-card">
                      <h3>💸 Withdraw Cash</h3>
                      <div className="balance-display">Available: ${selectedWallet.balance}</div>
                      <input
                        type="number"
                        placeholder="Amount to withdraw"
                        value={withdrawAmount}
                        onChange={(e) => setWithdrawAmount(e.target.value)}
                        step="0.01"
                        min="0.01"
                        max={selectedWallet.balance}
                      />
                      <button 
                        onClick={handleWithdraw} 
                        className="btn-danger"
                        disabled={loading || !withdrawAmount || parseFloat(withdrawAmount) > parseFloat(selectedWallet.balance)}
                      >
                        Withdraw Cash
                      </button>
                      {parseFloat(withdrawAmount) > parseFloat(selectedWallet.balance) && withdrawAmount && (
                        <span className="error-text">Insufficient balance</span>
                      )}
                    </div>

                    {/* Transfer */}
                    <div className="operation-card">
                      <h3>Transfer</h3>
                      <div className="transfer-info">
                        <div className="from-wallet">
                          <label>From:</label>
                          <div className="wallet-display">
                            <span>{selectedWallet.wallet_id}</span>
                            <button 
                              type="button"
                              className="copy-btn-small"
                              onClick={() => {
                                navigator.clipboard.writeText(selectedWallet.wallet_id);
                                setMessage('Wallet ID copied!');
                                setTimeout(() => setMessage(''), 2000);
                              }}
                            >
                              📋
                            </button>
                          </div>
                          <span className="balance-info">Balance: ${selectedWallet.balance}</span>
                        </div>
                      </div>
                      <form onSubmit={handleTransfer}>
                        <input
                          type="text"
                          placeholder="To Wallet ID (paste recipient's wallet ID)"
                          value={transferForm.to_wallet}
                          onChange={(e) => setTransferForm({...transferForm, to_wallet: e.target.value})}
                          required
                        />
                        <input
                          type="number"
                          placeholder="Amount"
                          value={transferForm.amount}
                          onChange={(e) => setTransferForm({...transferForm, amount: e.target.value})}
                          step="0.01"
                          min="0.01"
                          max={selectedWallet.balance}
                          required
                        />
                        <button 
                          type="submit" 
                          className="btn-primary"
                          disabled={loading || parseFloat(transferForm.amount) > parseFloat(selectedWallet.balance)}
                        >
                          Transfer
                        </button>
                        {parseFloat(transferForm.amount) > parseFloat(selectedWallet.balance) && (
                          <span className="error-text">Insufficient balance</span>
                        )}
                      </form>
                    </div>
                  </div>
                </div>

                {/* Transactions Section */}
                <div className="section">
                  <h2>📊 Transaction History</h2>
                  <div className="transactions-list">
                    {transactions.length === 0 ? (
                      <p className="no-data">No transactions yet</p>
                    ) : (
                      transactions.map(tx => (
                        <div key={tx.transaction_id} className="transaction-item">
                          <div className="tx-info">
                            <div className="tx-type">{tx.transaction_type}</div>
                            <div className="tx-id">{tx.transaction_id.substring(0, 12)}...</div>
                            <div className="tx-date">
                              {new Date(tx.created_at).toLocaleString()}
                            </div>
                          </div>
                          <div className="tx-amount">
                            <span className={
                              tx.transaction_type === 'deposit' ? 'positive' : 
                              tx.transaction_type === 'withdraw' ? 'negative' :
                              tx.from_wallet_id === selectedWallet.wallet_id ? 'negative' : 'positive'
                            }>
                              {tx.transaction_type === 'deposit' ? '+' : 
                               tx.transaction_type === 'withdraw' ? '-' :
                               tx.from_wallet_id === selectedWallet.wallet_id ? '-' : '+'}${tx.amount}
                            </span>
                            <span className={`tx-status ${tx.status}`}>
                              {tx.status}
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;