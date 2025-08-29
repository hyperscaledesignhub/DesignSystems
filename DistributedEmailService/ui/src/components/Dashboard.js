import React, { useState, useEffect } from 'react';
import axios from 'axios';

function Dashboard({ user, onLogout }) {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCompose, setShowCompose] = useState(false);
  const [activeTab, setActiveTab] = useState('emails');
  const [composeForm, setComposeForm] = useState({
    to: '',
    subject: '',
    content: ''
  });
  const [sending, setSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [serviceHealth, setServiceHealth] = useState({});

  useEffect(() => {
    loadEmails();
    loadNotifications();
    checkServiceHealth();
  }, []);

  const loadNotifications = async () => {
    try {
      const response = await axios.get(`/notifications/user/${user.id}`);
      setNotifications(response.data.notifications || []);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  };

  const checkServiceHealth = async () => {
    try {
      const response = await axios.get('/health');
      setServiceHealth(response.data);
    } catch (error) {
      console.error('Failed to check service health:', error);
    }
  };

  const searchEmails = async () => {
    if (!searchQuery.trim()) return;
    try {
      const response = await axios.post('/search', { query: searchQuery });
      setSearchResults(response.data.results || []);
      setActiveTab('search');
    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  const loadEmails = async () => {
    try {
      const response = await axios.get('/emails');
      setEmails(Array.isArray(response.data) ? response.data : []);
      setError('');
    } catch (error) {
      console.error('Failed to load emails:', error);
      setError('Failed to load emails');
    } finally {
      setLoading(false);
    }
  };

  const sendEmail = async () => {
    if (!composeForm.to || !composeForm.subject || !composeForm.content) {
      alert('Please fill in all fields');
      return;
    }

    setSending(true);
    try {
      await axios.post('/emails', {
        to_recipients: [composeForm.to],
        subject: composeForm.subject,
        body: composeForm.content
      });
      
      setComposeForm({ to: '', subject: '', content: '' });
      setShowCompose(false);
      await loadEmails(); // Reload emails
      alert('Email sent successfully!');
    } catch (error) {
      console.error('Failed to send email:', error);
      alert('Failed to send email: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setSending(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const headerStyle = {
    backgroundColor: '#007bff',
    color: 'white',
    padding: '1rem 2rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const buttonStyle = {
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.9rem'
  };

  const primaryButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#28a745',
    color: 'white'
  };

  const secondaryButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#6c757d',
    color: 'white'
  };

  const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
    marginBottom: '1rem'
  };

  const textareaStyle = {
    ...inputStyle,
    minHeight: '120px',
    resize: 'vertical'
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading emails...</div>
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={headerStyle}>
        <div>
          <h2 style={{ margin: 0 }}>Email System - Microservices Demo</h2>
          <small>Welcome, {user.full_name || user.email}</small>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Search emails..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchEmails()}
              style={{
                padding: '0.5rem',
                borderRadius: '4px',
                border: '1px solid #ddd',
                fontSize: '0.9rem'
              }}
            />
            <button 
              style={primaryButtonStyle}
              onClick={searchEmails}
            >
              Search
            </button>
          </div>
          <button 
            style={primaryButtonStyle}
            onClick={() => setShowCompose(true)}
          >
            Compose Email
          </button>
          <button 
            style={secondaryButtonStyle}
            onClick={onLogout}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{
        backgroundColor: '#f8f9fa',
        borderBottom: '1px solid #dee2e6',
        padding: '0 2rem'
      }}>
        <div style={{ display: 'flex', gap: '2rem' }}>
          {[
            { id: 'emails', label: `📧 Emails (${emails.length})` },
            { id: 'search', label: `🔍 Search Results (${searchResults.length})` },
            { id: 'notifications', label: `🔔 Notifications (${notifications.length})` },
            { id: 'services', label: '🏗️ Services Health' },
            { id: 'monitoring', label: '📊 System Monitor' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '1rem 1.5rem',
                border: 'none',
                backgroundColor: activeTab === tab.id ? '#007bff' : 'transparent',
                color: activeTab === tab.id ? 'white' : '#495057',
                cursor: 'pointer',
                borderBottom: activeTab === tab.id ? '3px solid #007bff' : 'none',
                fontSize: '0.9rem',
                fontWeight: activeTab === tab.id ? '600' : 'normal'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: '2rem', overflow: 'auto' }}>
        {error && (
          <div style={{
            color: 'red',
            backgroundColor: '#ffebee',
            padding: '1rem',
            borderRadius: '4px',
            marginBottom: '1rem'
          }}>
            {error}
          </div>
        )}

        {/* Compose Email Modal */}
        {showCompose && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000
          }}>
            <div style={{
              backgroundColor: 'white',
              padding: '2rem',
              borderRadius: '8px',
              width: '90%',
              maxWidth: '600px',
              maxHeight: '80vh',
              overflow: 'auto'
            }}>
              <h3 style={{ marginTop: 0 }}>Compose Email</h3>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                  To:
                </label>
                <input
                  type="email"
                  value={composeForm.to}
                  onChange={(e) => setComposeForm({...composeForm, to: e.target.value})}
                  style={inputStyle}
                  placeholder="recipient@example.com"
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                  Subject:
                </label>
                <input
                  type="text"
                  value={composeForm.subject}
                  onChange={(e) => setComposeForm({...composeForm, subject: e.target.value})}
                  style={inputStyle}
                  placeholder="Email subject"
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                  Content:
                </label>
                <textarea
                  value={composeForm.content}
                  onChange={(e) => setComposeForm({...composeForm, content: e.target.value})}
                  style={textareaStyle}
                  placeholder="Email content..."
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                <button 
                  style={secondaryButtonStyle}
                  onClick={() => setShowCompose(false)}
                  disabled={sending}
                >
                  Cancel
                </button>
                <button 
                  style={{
                    ...primaryButtonStyle,
                    opacity: sending ? 0.7 : 1,
                    cursor: sending ? 'not-allowed' : 'pointer'
                  }}
                  onClick={sendEmail}
                  disabled={sending}
                >
                  {sending ? 'Sending...' : 'Send Email'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'emails' && (
          <div>
            <h3>📧 Your Emails ({emails.length})</h3>
            
            {emails.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                color: '#666', 
                padding: '2rem',
                backgroundColor: '#f8f9fa',
                borderRadius: '8px'
              }}>
                No emails found. Try composing your first email!
              </div>
            ) : (
              <div>
                {emails.map((email) => (
                  <div key={email.id} style={{
                    backgroundColor: 'white',
                    border: '1px solid #ddd',
                    borderRadius: '8px',
                    padding: '1rem',
                    marginBottom: '1rem',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'flex-start',
                      marginBottom: '0.5rem'
                    }}>
                      <div>
                        <strong style={{ fontSize: '1.1rem' }}>{email.subject}</strong>
                        <div style={{ color: '#666', fontSize: '0.9rem', marginTop: '0.25rem' }}>
                          From: {email.from_email} | To: {Array.isArray(email.to_recipients) ? email.to_recipients.join(', ') : email.to_recipients}
                        </div>
                        <div style={{ color: '#999', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                          📊 Spam Score: {email.spam_score || 0}/100
                        </div>
                      </div>
                      <div style={{ 
                        fontSize: '0.8rem', 
                        color: '#999',
                        textAlign: 'right'
                      }}>
                        {formatDate(email.created_at)}
                        <br />
                        <span style={{ 
                          backgroundColor: email.status === 'sent' ? '#28a745' : '#ffc107',
                          color: email.status === 'sent' ? 'white' : 'black',
                          padding: '0.2rem 0.4rem',
                          borderRadius: '3px',
                          fontSize: '0.7rem'
                        }}>
                          {email.status}
                        </span>
                      </div>
                    </div>
                    <div style={{ 
                      color: '#333',
                      lineHeight: '1.4',
                      paddingTop: '0.5rem',
                      borderTop: '1px solid #eee'
                    }}>
                      {email.body}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <button 
              style={{
                ...secondaryButtonStyle,
                marginTop: '1rem'
              }}
              onClick={loadEmails}
            >
              Refresh Emails
            </button>
          </div>
        )}

        {activeTab === 'search' && (
          <div>
            <h3>🔍 Search Results ({searchResults.length})</h3>
            {searchResults.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                color: '#666', 
                padding: '2rem',
                backgroundColor: '#f8f9fa',
                borderRadius: '8px'
              }}>
                {searchQuery ? 'No emails found for your search.' : 'Enter a search query to find emails.'}
              </div>
            ) : (
              <div>
                {searchResults.map((email) => (
                  <div key={email.id} style={{
                    backgroundColor: 'white',
                    border: '1px solid #ddd',
                    borderRadius: '8px',
                    padding: '1rem',
                    marginBottom: '1rem',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                  }}>
                    <strong>{email.subject}</strong>
                    <div style={{ color: '#666', fontSize: '0.9rem' }}>
                      {email.from_email} → {email.to_recipients}
                    </div>
                    <div style={{ marginTop: '0.5rem' }}>{email.body}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'notifications' && (
          <div>
            <h3>🔔 Notifications ({notifications.length})</h3>
            {notifications.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                color: '#666', 
                padding: '2rem',
                backgroundColor: '#f8f9fa',
                borderRadius: '8px'
              }}>
                No notifications yet.
              </div>
            ) : (
              <div>
                {notifications.map((notification, index) => (
                  <div key={index} style={{
                    backgroundColor: 'white',
                    border: '1px solid #ddd',
                    borderRadius: '8px',
                    padding: '1rem',
                    marginBottom: '1rem',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                  }}>
                    <strong>{notification.title}</strong>
                    <div style={{ color: '#666' }}>{notification.message}</div>
                  </div>
                ))}
              </div>
            )}
            <button 
              style={{
                ...secondaryButtonStyle,
                marginTop: '1rem'
              }}
              onClick={loadNotifications}
            >
              Refresh Notifications
            </button>
          </div>
        )}

        {activeTab === 'services' && (
          <div>
            <h3>🏗️ Microservices Health Status</h3>
            <div style={{ marginBottom: '1rem' }}>
              <button 
                style={primaryButtonStyle}
                onClick={checkServiceHealth}
              >
                Check Service Health
              </button>
            </div>
            
            {Object.keys(serviceHealth).length > 0 && (
              <div>
                <div style={{
                  backgroundColor: 'white',
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem'
                }}>
                  <h4>Gateway Status: <span style={{ 
                    color: serviceHealth.gateway === 'healthy' ? '#28a745' : '#dc3545' 
                  }}>{serviceHealth.gateway || 'unknown'}</span></h4>
                </div>

                {serviceHealth.services && (
                  <div>
                    <h4>Individual Services:</h4>
                    {Object.entries(serviceHealth.services).map(([serviceName, status]) => (
                      <div key={serviceName} style={{
                        backgroundColor: 'white',
                        border: '1px solid #ddd',
                        borderRadius: '8px',
                        padding: '1rem',
                        marginBottom: '0.5rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <span style={{ fontWeight: '500' }}>{serviceName}-service</span>
                        <span style={{ 
                          color: status === 'healthy' ? '#28a745' : '#dc3545',
                          fontWeight: '600'
                        }}>
                          {status === 'healthy' ? '✅' : '❌'} {status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'monitoring' && (
          <div>
            <h3>📊 System Monitoring</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
              
              <div style={{
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '1.5rem'
              }}>
                <h4>🔍 Jaeger Tracing</h4>
                <p>View distributed traces across all microservices:</p>
                <button 
                  style={primaryButtonStyle}
                  onClick={() => window.open('http://localhost:16686', '_blank')}
                >
                  Open Jaeger UI
                </button>
              </div>

              <div style={{
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '1.5rem'
              }}>
                <h4>📊 User Stats</h4>
                <p>Email: {user.email}</p>
                <p>Role: {user.role}</p>
                <p>Storage: {Math.round(user.storage_used / 1024 / 1024)} MB / {Math.round(user.storage_limit / 1024 / 1024 / 1024)} GB</p>
                <p>Account Created: {formatDate(user.created_at)}</p>
              </div>

              <div style={{
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '1.5rem'
              }}>
                <h4>🛠️ API Endpoints</h4>
                <div style={{ fontSize: '0.9rem' }}>
                  <div>✅ Authentication Service</div>
                  <div>✅ Email Service</div>
                  <div>✅ Search Service</div>
                  <div>✅ Notification Service</div>
                  <div>✅ Spam Detection Service</div>
                  <div>✅ Attachment Service</div>
                </div>
              </div>

              <div style={{
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '1.5rem'
              }}>
                <h4>💾 Infrastructure</h4>
                <div style={{ fontSize: '0.9rem' }}>
                  <div>🗄️ PostgreSQL Database</div>
                  <div>⚡ Redis Cache</div>
                  <div>🔍 Elasticsearch</div>
                  <div>📁 MinIO Object Storage</div>
                  <div>🐳 Docker Compose</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;