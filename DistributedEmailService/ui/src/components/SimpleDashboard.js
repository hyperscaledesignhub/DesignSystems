import React, { useState, useEffect } from 'react';
import axios from 'axios';

function SimpleDashboard({ user, onLogout }) {
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
  const [serviceHealth, setServiceHealth] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    loadEmails();
    checkServiceHealth();
    loadNotifications();
    setupWebSocket();
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const setupWebSocket = () => {
    const wsUrl = `ws://localhost:8000/notifications/ws/${user.id}`;
    const websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setWs(websocket);
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'notification') {
        setNotifications(prev => [data.data, ...prev]);
        setUnreadCount(prev => prev + 1);
        showNotificationAlert(data.data);
      }
    };
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setTimeout(setupWebSocket, 3000);
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  const showNotificationAlert = (notification) => {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'notification-alert';
    alertDiv.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #4CAF50;
      color: white;
      padding: 15px;
      border-radius: 5px;
      z-index: 1000;
      max-width: 300px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `;
    alertDiv.innerHTML = `
      <strong>${notification.title}</strong><br>
      ${notification.message}
    `;
    
    document.body.appendChild(alertDiv);
    setTimeout(() => {
      document.body.removeChild(alertDiv);
    }, 4000);
  };

  const loadNotifications = async () => {
    try {
      const response = await axios.get(`/notifications/${user.id}`);
      setNotifications(response.data || []);
      
      const unreadResponse = await axios.get(`/notifications/user/${user.id}/unread-count`);
      setUnreadCount(unreadResponse.data.unread_count || 0);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  };

  const markNotificationAsRead = async (notificationId) => {
    try {
      await axios.patch(`/notifications/${notificationId}/read`);
      setNotifications(prev => 
        prev.map(n => 
          n.id === notificationId ? { ...n, is_read: true } : n
        )
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      await axios.patch(`/notifications/user/${user.id}/read-all`);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const getNotificationIcon = (type) => {
    const iconMap = {
      'email_sent': { icon: '📤', color: '#28a745' },
      'email_received': { icon: '📨', color: '#007bff' },
      'spam_detected': { icon: '🚨', color: '#dc3545' },
      'attachment_uploaded': { icon: '📎', color: '#ffc107' },
      'system_alert': { icon: '⚠️', color: '#fd7e14' }
    };
    return iconMap[type] || { icon: '📧', color: '#6c757d' };
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

  const checkServiceHealth = async () => {
    try {
      const response = await axios.get('/health');
      setServiceHealth(response.data);
    } catch (error) {
      console.error('Failed to check service health:', error);
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
      await loadEmails();
      alert('Email sent successfully!');
    } catch (error) {
      console.error('Failed to send email:', error);
      alert('Failed to send email: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setSending(false);
    }
  };

  const searchEmails = async () => {
    if (!searchQuery.trim()) {
      alert('Please enter a search term');
      return;
    }
    
    try {
      const response = await axios.post('/search', { query: searchQuery });
      
      if (response.data.total > 0) {
        const results = response.data.results.map(r => `• ${r.subject}`).join('\n');
        alert(`🎉 Search Success!\n\nFound ${response.data.total} email(s) matching "${searchQuery}":\n\n${results}`);
      } else {
        alert(`🔍 Search completed for "${searchQuery}"\n\nNo emails found matching your query.\n\n💡 Try sending an email first, then search for it!`);
      }
      
      console.log('Search results:', response.data);
    } catch (error) {
      console.error('Search failed:', error);
      alert(`❌ Search failed: ${error.response?.data?.detail || 'Unknown error'}\n\nPlease try again or contact support.`);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const buttonStyle = {
    padding: '0.75rem 1.5rem',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.9rem',
    fontWeight: '500',
    marginRight: '0.5rem',
    marginBottom: '0.5rem'
  };

  const primaryButton = {
    ...buttonStyle,
    backgroundColor: '#007bff',
    color: 'white'
  };

  const secondaryButton = {
    ...buttonStyle,
    backgroundColor: '#6c757d',
    color: 'white'
  };

  const successButton = {
    ...buttonStyle,
    backgroundColor: '#28a745',
    color: 'white'
  };

  const warningButton = {
    ...buttonStyle,
    backgroundColor: '#ffc107',
    color: 'black'
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      {/* Header */}
      <div style={{
        backgroundColor: '#007bff',
        color: 'white',
        padding: '1.5rem 2rem',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.8rem' }}>🏗️ Distributed Email System</h1>
            <p style={{ margin: '0.5rem 0 0 0', opacity: 0.9 }}>
              Welcome, {user.full_name || user.email} | Demo Ready for Customers
            </p>
          </div>
          <button style={secondaryButton} onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>

      {/* Action Bar */}
      <div style={{
        backgroundColor: 'white',
        padding: '1rem 2rem',
        borderBottom: '1px solid #dee2e6',
        display: 'flex',
        gap: '1rem',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <button style={primaryButton} onClick={() => setShowCompose(true)}>
          📧 Compose Email
        </button>
        
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
              minWidth: '200px'
            }}
          />
          <button style={primaryButton} onClick={searchEmails}>
            🔍 Search
          </button>
        </div>

        <button style={successButton} onClick={loadEmails}>
          🔄 Refresh
        </button>

        <button style={warningButton} onClick={checkServiceHealth}>
          🏥 Health Check
        </button>

        <button 
          style={primaryButton}
          onClick={() => window.open('http://localhost:16686', '_blank')}
        >
          📊 Jaeger Tracing
        </button>

        <button 
          style={{
            ...buttonStyle,
            backgroundColor: unreadCount > 0 ? '#dc3545' : '#6c757d',
            color: 'white',
            position: 'relative'
          }}
          onClick={() => {
            setActiveTab('notifications');
            if (unreadCount > 0) markAllAsRead();
          }}
        >
          🔔 Notifications
          {unreadCount > 0 && (
            <span style={{
              position: 'absolute',
              top: '-5px',
              right: '-5px',
              backgroundColor: '#dc3545',
              color: 'white',
              borderRadius: '50%',
              width: '20px',
              height: '20px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold'
            }}>
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* Navigation Tabs */}
      <div style={{
        backgroundColor: '#f8f9fa',
        padding: '0 2rem',
        borderBottom: '1px solid #dee2e6'
      }}>
        <div style={{ display: 'flex', gap: '0' }}>
          {[
            { id: 'emails', label: `📧 Emails (${emails.length})`, color: '#007bff' },
            { id: 'notifications', label: `🔔 Notifications (${notifications.length})`, color: '#dc3545' },
            { id: 'services', label: '🏗️ Services Health', color: '#28a745' },
            { id: 'demo', label: '🎯 Demo Guide', color: '#17a2b8' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '1rem 2rem',
                border: 'none',
                backgroundColor: activeTab === tab.id ? tab.color : 'transparent',
                color: activeTab === tab.id ? 'white' : '#495057',
                cursor: 'pointer',
                fontWeight: activeTab === tab.id ? '600' : 'normal',
                borderBottom: activeTab === tab.id ? `3px solid ${tab.color}` : 'none'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ padding: '2rem' }}>
        {error && (
          <div style={{
            color: 'red',
            backgroundColor: '#ffebee',
            padding: '1rem',
            borderRadius: '8px',
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
              borderRadius: '12px',
              width: '90%',
              maxWidth: '600px',
              boxShadow: '0 10px 25px rgba(0,0,0,0.2)'
            }}>
              <h3>✉️ Compose New Email</h3>
              
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>To:</label>
                <input
                  type="email"
                  value={composeForm.to}
                  onChange={(e) => setComposeForm({...composeForm, to: e.target.value})}
                  placeholder="recipient@example.com"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Subject:</label>
                <input
                  type="text"
                  value={composeForm.subject}
                  onChange={(e) => setComposeForm({...composeForm, subject: e.target.value})}
                  placeholder="Email subject"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Message:</label>
                <textarea
                  value={composeForm.content}
                  onChange={(e) => setComposeForm({...composeForm, content: e.target.value})}
                  placeholder="Type your message here..."
                  rows="6"
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ddd', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                <button 
                  style={secondaryButton}
                  onClick={() => setShowCompose(false)}
                  disabled={sending}
                >
                  Cancel
                </button>
                <button 
                  style={{
                    ...successButton,
                    opacity: sending ? 0.7 : 1,
                    cursor: sending ? 'not-allowed' : 'pointer'
                  }}
                  onClick={sendEmail}
                  disabled={sending}
                >
                  {sending ? 'Sending...' : '📤 Send Email'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'emails' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <h2>📧 Email Management ({emails.length} emails)</h2>
            </div>
            
            {emails.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '3rem',
                backgroundColor: 'white',
                borderRadius: '12px',
                border: '2px dashed #dee2e6'
              }}>
                <h3>📭 No emails yet</h3>
                <p>Click "Compose Email" to send your first message and test the system!</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '1rem' }}>
                {emails.map((email) => (
                  <div key={email.id} style={{
                    backgroundColor: 'white',
                    border: '1px solid #dee2e6',
                    borderRadius: '12px',
                    padding: '1.5rem',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                      <div style={{ flex: 1 }}>
                        <h4 style={{ margin: 0, color: '#333', fontSize: '1.2rem' }}>{email.subject}</h4>
                        <p style={{ margin: '0.5rem 0', color: '#666', fontSize: '0.9rem' }}>
                          <strong>From:</strong> {email.from_email} → <strong>To:</strong> {Array.isArray(email.to_recipients) ? email.to_recipients.join(', ') : email.to_recipients}
                        </p>
                        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#999' }}>
                          <span>📊 Spam Score: {email.spam_score || 0}/100</span>
                          <span>📅 {formatDate(email.created_at)}</span>
                        </div>
                      </div>
                      <span style={{
                        backgroundColor: email.status === 'sent' ? '#28a745' : '#ffc107',
                        color: email.status === 'sent' ? 'white' : 'black',
                        padding: '0.3rem 0.8rem',
                        borderRadius: '20px',
                        fontSize: '0.8rem',
                        fontWeight: '500'
                      }}>
                        {email.status}
                      </span>
                    </div>
                    <div style={{
                      backgroundColor: '#f8f9fa',
                      padding: '1rem',
                      borderRadius: '8px',
                      border: '1px solid #e9ecef',
                      lineHeight: '1.5'
                    }}>
                      {email.body}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'notifications' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <h2>🔔 Real-time Notifications ({notifications.length} total)</h2>
              <div style={{ display: 'flex', gap: '1rem' }}>
                {unreadCount > 0 && (
                  <button style={warningButton} onClick={markAllAsRead}>
                    Mark All Read ({unreadCount})
                  </button>
                )}
                <button style={primaryButton} onClick={loadNotifications}>
                  🔄 Refresh
                </button>
              </div>
            </div>
            
            {notifications.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '3rem',
                backgroundColor: 'white',
                borderRadius: '12px',
                border: '2px dashed #dee2e6'
              }}>
                <h3>🔕 No notifications yet</h3>
                <p>Send an email to see real-time notifications in action!</p>
                <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                  <strong>💡 Demo Tip:</strong> When you send emails, you'll get instant notifications via WebSocket connection!
                </div>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '1rem' }}>
                {notifications.map((notification) => (
                  <div key={notification.id} style={{
                    backgroundColor: notification.is_read ? 'white' : '#e7f3ff',
                    border: notification.is_read ? '1px solid #dee2e6' : '2px solid #007bff',
                    borderRadius: '12px',
                    padding: '1.5rem',
                    position: 'relative',
                    boxShadow: notification.is_read ? '0 1px 3px rgba(0,0,0,0.1)' : '0 2px 8px rgba(0,123,255,0.2)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                          <span style={{ 
                            fontSize: '1.2rem',
                            backgroundColor: getNotificationIcon(notification.type).color,
                            padding: '4px 8px',
                            borderRadius: '6px'
                          }}>
                            {getNotificationIcon(notification.type).icon}
                          </span>
                          <h4 style={{ margin: 0, color: '#495057' }}>{notification.title}</h4>
                          {!notification.is_read && (
                            <span style={{
                              backgroundColor: '#dc3545',
                              color: 'white',
                              padding: '2px 6px',
                              borderRadius: '10px',
                              fontSize: '0.75rem',
                              fontWeight: 'bold'
                            }}>
                              NEW
                            </span>
                          )}
                        </div>
                        <p style={{ margin: '0.5rem 0', color: '#6c757d' }}>
                          {notification.message}
                        </p>
                        <div style={{ fontSize: '0.85rem', color: '#999', marginTop: '0.5rem' }}>
                          {new Date(notification.created_at).toLocaleString()}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '1rem' }}>
                        {!notification.is_read && (
                          <button 
                            style={{
                              ...buttonStyle,
                              backgroundColor: '#28a745',
                              color: 'white',
                              padding: '0.25rem 0.5rem',
                              fontSize: '0.75rem'
                            }}
                            onClick={() => markNotificationAsRead(notification.id)}
                          >
                            Mark Read
                          </button>
                        )}
                      </div>
                    </div>
                    
                    {notification.data && Object.keys(notification.data).length > 0 && (
                      <div style={{
                        marginTop: '1rem',
                        padding: '0.75rem',
                        backgroundColor: '#f8f9fa',
                        borderRadius: '6px',
                        fontSize: '0.85rem'
                      }}>
                        <strong>Details:</strong>
                        <pre style={{ margin: '0.5rem 0 0 0', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {JSON.stringify(notification.data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            <div style={{
              marginTop: '2rem',
              padding: '1.5rem',
              backgroundColor: '#e8f5e8',
              borderRadius: '12px',
              border: '1px solid #c3e6c3'
            }}>
              <h4 style={{ color: '#155724', margin: '0 0 1rem 0' }}>🚀 Notification Service Features</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
                <div>
                  <strong>📡 Real-time WebSocket:</strong> Instant notifications when emails are sent/received
                </div>
                <div>
                  <strong>🔢 Unread Counter:</strong> Track unread notifications with badge system
                </div>
                <div>
                  <strong>📋 Persistent Storage:</strong> All notifications stored in PostgreSQL database
                </div>
                <div>
                  <strong>🎯 Event-Driven:</strong> Automatic notifications triggered by email service events
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'services' && (
          <div>
            <h2>🏗️ Microservices Health Dashboard</h2>
            
            {Object.keys(serviceHealth).length > 0 && (
              <div style={{ display: 'grid', gap: '1rem', marginTop: '2rem' }}>
                <div style={{
                  backgroundColor: 'white',
                  padding: '1.5rem',
                  borderRadius: '12px',
                  border: '1px solid #dee2e6'
                }}>
                  <h3>🚪 API Gateway Status</h3>
                  <div style={{
                    fontSize: '1.5rem',
                    fontWeight: '600',
                    color: serviceHealth.gateway === 'healthy' ? '#28a745' : '#dc3545'
                  }}>
                    {serviceHealth.gateway === 'healthy' ? '✅ HEALTHY' : '❌ UNHEALTHY'} 
                  </div>
                </div>

                {serviceHealth.services && (
                  <div>
                    <h3>🔧 Individual Microservices</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
                      {Object.entries(serviceHealth.services).map(([serviceName, status]) => (
                        <div key={serviceName} style={{
                          backgroundColor: 'white',
                          padding: '1.5rem',
                          borderRadius: '12px',
                          border: '1px solid #dee2e6',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}>
                          <div>
                            <h4 style={{ margin: 0 }}>{serviceName}-service</h4>
                            <small style={{ color: '#666' }}>Microservice Component</small>
                          </div>
                          <div style={{
                            fontSize: '1.2rem',
                            fontWeight: '600',
                            color: status === 'healthy' ? '#28a745' : '#dc3545'
                          }}>
                            {status === 'healthy' ? '✅' : '❌'} {status.toUpperCase()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div style={{ marginTop: '2rem', padding: '1.5rem', backgroundColor: '#e7f3ff', borderRadius: '12px' }}>
              <h4>🎯 Architecture Overview</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                <div>✅ API Gateway (FastAPI)</div>
                <div>✅ Authentication Service</div>
                <div>✅ Email Service</div>
                <div>✅ Search Service (Elasticsearch)</div>
                <div>✅ Spam Detection Service</div>
                <div>✅ Notification Service</div>
                <div>✅ Attachment Service (MinIO)</div>
                <div>✅ PostgreSQL Database</div>
                <div>✅ Redis Cache</div>
                <div>✅ Jaeger Distributed Tracing</div>
                <div>✅ Docker Compose Orchestration</div>
                <div>✅ React Frontend (Nginx)</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'demo' && (
          <div>
            <h2>🎯 Customer Demo Guide</h2>
            
            <div style={{ display: 'grid', gap: '2rem' }}>
              <div style={{ backgroundColor: '#d4edda', padding: '1.5rem', borderRadius: '12px', border: '1px solid #c3e6cb' }}>
                <h3>✅ Currently Working Features (Demo-Ready)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                  <div>
                    <h4>👤 Authentication</h4>
                    <ul>
                      <li>User Registration</li>
                      <li>User Login</li>
                      <li>JWT Token Management</li>
                      <li>Session Persistence</li>
                    </ul>
                  </div>
                  <div>
                    <h4>📧 Email System</h4>
                    <ul>
                      <li>Compose & Send Emails</li>
                      <li>View Email List</li>
                      <li>Spam Score Detection</li>
                      <li>Real-time Updates</li>
                    </ul>
                  </div>
                  <div>
                    <h4>🔍 Search & Monitoring</h4>
                    <ul>
                      <li>Email Search (Elasticsearch)</li>
                      <li>Service Health Monitoring</li>
                      <li>Distributed Tracing (Jaeger)</li>
                      <li>System Status Dashboard</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div style={{ backgroundColor: 'white', padding: '2rem', borderRadius: '12px', border: '1px solid #dee2e6' }}>
                <h3>🚀 5-Minute Demo Script</h3>
                <div style={{ display: 'grid', gap: '1.5rem' }}>
                  
                  <div style={{ padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                    <h4>Step 1: Registration & Login (30 seconds)</h4>
                    <p>1. Show customer the login page<br/>
                    2. Click "Register here" and create account<br/>
                    3. Automatic login to dashboard</p>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                    <h4>Step 2: Email Functionality (2 minutes)</h4>
                    <p>1. Click "📧 Compose Email"<br/>
                    2. Send email to: demo@example.com<br/>
                    3. Show email appears with spam score<br/>
                    4. Demonstrate refresh functionality</p>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                    <h4>Step 3: Search Feature (30 seconds)</h4>
                    <p>1. Use search bar to find emails<br/>
                    2. Show Elasticsearch integration<br/>
                    3. Demonstrate full-text search</p>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                    <h4>Step 4: Microservices Architecture (1 minute)</h4>
                    <p>1. Click "🏗️ Services Health" tab<br/>
                    2. Show all 7+ microservices status<br/>
                    3. Explain scalability and resilience</p>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                    <h4>Step 5: Observability & Monitoring (1 minute)</h4>
                    <p>1. Click "📊 Jaeger Tracing" button<br/>
                    2. Show distributed traces in new tab<br/>
                    3. Demonstrate request flow across services</p>
                  </div>
                </div>
              </div>

              <div style={{ backgroundColor: '#fff3cd', padding: '1.5rem', borderRadius: '12px', border: '1px solid #ffeaa7' }}>
                <h3>🎯 Key Customer Selling Points</h3>
                <ul>
                  <li><strong>Cloud-Native Architecture:</strong> Docker containers, Kubernetes-ready</li>
                  <li><strong>Microservices:</strong> Independent scaling, fault isolation</li>
                  <li><strong>Modern Tech Stack:</strong> React, FastAPI, PostgreSQL, Redis, Elasticsearch</li>
                  <li><strong>Production-Ready:</strong> JWT authentication, API gateway, proper error handling</li>
                  <li><strong>Observability:</strong> Distributed tracing, health monitoring, metrics</li>
                  <li><strong>Scalable Storage:</strong> Object storage (MinIO), full-text search</li>
                </ul>
              </div>

              <div style={{ backgroundColor: '#d1ecf1', padding: '1.5rem', borderRadius: '12px', border: '1px solid #bee5eb' }}>
                <h3>🔗 Demo URLs</h3>
                <div style={{ fontSize: '1.1rem', fontFamily: 'monospace' }}>
                  <p><strong>Main Application:</strong> <a href="http://localhost:3000" target="_blank">http://localhost:3000</a></p>
                  <p><strong>API Gateway:</strong> <a href="http://localhost:8000" target="_blank">http://localhost:8000</a></p>
                  <p><strong>Jaeger Tracing:</strong> <a href="http://localhost:16686" target="_blank">http://localhost:16686</a></p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SimpleDashboard;