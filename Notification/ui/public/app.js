// API Endpoints
const API_BASE = 'http://localhost:7841';
const NOTIFICATION_SERVER = 'http://localhost:7842';
const USER_DB = 'http://localhost:7846';

// Service health check endpoints
const SERVICES = {
    'api-gateway': 'http://localhost:7841/health',
    'notification-server': 'http://localhost:7842/health',
    'user-database': 'http://localhost:7846/health',
    'email-worker': 'http://localhost:7843/health',
    'sms-worker': 'http://localhost:7844/health',
    'push-worker': 'http://localhost:7845/health'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkServices();
    loadUsers();
    setupEventListeners();
    addLog('System initialized', 'info');
});

// Event Listeners
function setupEventListeners() {
    // Update subject field visibility based on notification type
    document.querySelectorAll('input[name="notification-type"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const subjectGroup = document.getElementById('subject-group');
            if (e.target.value === 'email') {
                subjectGroup.style.display = 'block';
            } else {
                subjectGroup.style.display = 'none';
            }
        });
    });
}

// Service Status Check
async function checkServices() {
    addLog('Checking service status...', 'info');
    
    for (const [service, url] of Object.entries(SERVICES)) {
        const indicator = document.getElementById(`status-${service}`);
        indicator.className = 'status-indicator checking';
        
        try {
            const response = await fetch(url, { 
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });
            const data = await response.json();
            
            if (data.status === 'healthy') {
                indicator.className = 'status-indicator online';
                indicator.title = 'Online';
            } else {
                indicator.className = 'status-indicator offline';
                indicator.title = 'Unhealthy';
            }
        } catch (error) {
            indicator.className = 'status-indicator offline';
            indicator.title = 'Offline';
        }
    }
    
    addLog('Service status check complete', 'success');
}

// User Management
async function createUser() {
    const email = document.getElementById('user-email').value;
    const phone = document.getElementById('user-phone').value;
    
    if (!email && !phone) {
        addLog('Please provide at least email or phone number', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${USER_DB}/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email || null,
                phone_number: phone || null,
                country_code: phone ? '+1' : null
            })
        });
        
        const data = await response.json();
        addLog(`User created with ID: ${data.user_id}`, 'success');
        
        // Clear form
        document.getElementById('user-email').value = '';
        document.getElementById('user-phone').value = '';
        
        // Reload users
        loadUsers();
    } catch (error) {
        addLog(`Failed to create user: ${error.message}`, 'error');
    }
}

async function addDevice() {
    const userId = document.getElementById('device-user-id').value;
    const token = document.getElementById('device-token').value;
    const type = document.getElementById('device-type').value;
    
    if (!userId || !token) {
        addLog('Please provide User ID and Device Token', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${USER_DB}/users/${userId}/devices`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_token: token,
                device_type: type
            })
        });
        
        const data = await response.json();
        addLog(`Device added for user ${userId}`, 'success');
        
        // Clear form
        document.getElementById('device-user-id').value = '';
        document.getElementById('device-token').value = '';
        
        // Reload users
        loadUsers();
    } catch (error) {
        addLog(`Failed to add device: ${error.message}`, 'error');
    }
}

async function loadUsers() {
    try {
        // For demo, we'll try to load first 10 users
        const userList = document.getElementById('user-list');
        userList.innerHTML = '';
        
        for (let i = 1; i <= 5; i++) {
            try {
                const response = await fetch(`${USER_DB}/users/${i}`);
                if (response.ok) {
                    const user = await response.json();
                    const userItem = document.createElement('div');
                    userItem.className = 'user-item';
                    userItem.innerHTML = `
                        <strong>User ID: ${user.user_id}</strong>
                        <div class="user-details">
                            ${user.email ? `Email: ${user.email}` : ''}
                            ${user.phone_number ? `<br>Phone: ${user.phone_number}` : ''}
                        </div>
                    `;
                    userList.appendChild(userItem);
                }
            } catch (e) {
                // User doesn't exist, continue
            }
        }
        
        if (userList.children.length === 0) {
            userList.innerHTML = '<p style="color: #999;">No users found. Create one above.</p>';
        }
    } catch (error) {
        addLog(`Failed to load users: ${error.message}`, 'error');
    }
}

// Send Notification
async function sendNotification() {
    const userId = document.getElementById('notification-user-id').value;
    const type = document.querySelector('input[name="notification-type"]:checked').value;
    const subject = document.getElementById('notification-subject').value;
    const message = document.getElementById('notification-message').value;
    
    if (!userId || !message) {
        addLog('Please provide User ID and Message', 'error');
        return;
    }
    
    if (type === 'email' && !subject) {
        addLog('Subject is required for email notifications', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/notifications/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: parseInt(userId),
                type: type,
                subject: subject || null,
                message: message,
                metadata: {
                    source: 'demo-ui',
                    timestamp: new Date().toISOString()
                }
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            addLog(`Notification sent! ID: ${data.notification_id}`, 'success');
            addLog(`Status: ${data.status}, Queue: ${data.queue}`, 'info');
            
            // Clear form
            document.getElementById('notification-message').value = '';
            document.getElementById('notification-subject').value = '';
        } else {
            addLog(`Failed to send notification: ${data.detail}`, 'error');
        }
    } catch (error) {
        addLog(`Failed to send notification: ${error.message}`, 'error');
    }
}

// Load Notification History
async function loadNotificationHistory() {
    const userId = document.getElementById('history-user-id').value;
    const notificationList = document.getElementById('notification-list');
    
    if (!userId) {
        addLog('Please provide a User ID to load history', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${NOTIFICATION_SERVER}/users/${userId}/notifications`);
        const data = await response.json();
        
        notificationList.innerHTML = '';
        
        if (data.notifications && data.notifications.length > 0) {
            data.notifications.forEach(notification => {
                const item = document.createElement('div');
                item.className = 'notification-item';
                item.innerHTML = `
                    <div class="notification-header">
                        <span class="notification-type ${notification.type}">${notification.type}</span>
                        <span class="notification-status ${notification.status}">${notification.status}</span>
                    </div>
                    <div>ID: ${notification.notification_id}</div>
                    <div>Created: ${new Date(notification.created_at).toLocaleString()}</div>
                `;
                notificationList.appendChild(item);
            });
            
            addLog(`Loaded ${data.count} notifications for user ${userId}`, 'success');
        } else {
            notificationList.innerHTML = '<p style="color: #999;">No notifications found for this user.</p>';
        }
    } catch (error) {
        addLog(`Failed to load notification history: ${error.message}`, 'error');
        notificationList.innerHTML = '<p style="color: #999;">Failed to load notifications.</p>';
    }
}

// Demo Scenarios
async function runScenario(scenario) {
    const output = document.getElementById('scenario-output');
    output.innerHTML = `Running ${scenario} scenario...\n`;
    
    switch(scenario) {
        case 'single-email':
            output.innerHTML += 'Creating user with email...\n';
            // Create a test user
            const emailUser = await createTestUser('test@example.com', null);
            if (emailUser) {
                output.innerHTML += `User created: ID ${emailUser.user_id}\n`;
                output.innerHTML += 'Sending email notification...\n';
                
                const result = await sendTestNotification(emailUser.user_id, 'email', 
                    'Test Email', 'This is a test email notification from the demo.');
                
                if (result) {
                    output.innerHTML += `✅ Email notification sent: ${result.notification_id}\n`;
                } else {
                    output.innerHTML += '❌ Failed to send email notification\n';
                }
            }
            break;
            
        case 'bulk-sms':
            output.innerHTML += 'Creating 3 users with phone numbers...\n';
            for (let i = 0; i < 3; i++) {
                const phone = `+155512340${i}`;
                const user = await createTestUser(null, phone);
                if (user) {
                    output.innerHTML += `User ${i+1} created: ID ${user.user_id}\n`;
                    const result = await sendTestNotification(user.user_id, 'sms', 
                        null, `SMS Alert ${i+1}: Your order is ready!`);
                    if (result) {
                        output.innerHTML += `✅ SMS sent to ${phone}\n`;
                    }
                }
            }
            break;
            
        case 'push-broadcast':
            output.innerHTML += 'Creating user with device tokens...\n';
            const pushUser = await createTestUser('push@example.com', null);
            if (pushUser) {
                output.innerHTML += `User created: ID ${pushUser.user_id}\n`;
                
                // Add iOS device
                await addTestDevice(pushUser.user_id, 'ios_token_123', 'ios');
                output.innerHTML += 'Added iOS device\n';
                
                // Add Android device
                await addTestDevice(pushUser.user_id, 'android_token_456', 'android');
                output.innerHTML += 'Added Android device\n';
                
                const result = await sendTestNotification(pushUser.user_id, 'push', 
                    null, 'Breaking News: Demo notification system is working!');
                
                if (result) {
                    output.innerHTML += `✅ Push notification broadcast: ${result.notification_id}\n`;
                } else {
                    output.innerHTML += '❌ Failed to send push notification\n';
                }
            }
            break;
            
        case 'multi-channel':
            output.innerHTML += 'Creating user with all contact methods...\n';
            const multiUser = await createTestUser('multi@example.com', '+15551234567');
            if (multiUser) {
                output.innerHTML += `User created: ID ${multiUser.user_id}\n`;
                
                // Add device
                await addTestDevice(multiUser.user_id, 'multi_device_789', 'android');
                output.innerHTML += 'Added device token\n';
                
                // Send to all channels
                const channels = ['email', 'sms', 'push'];
                for (const channel of channels) {
                    const subject = channel === 'email' ? 'Multi-Channel Test' : null;
                    const result = await sendTestNotification(multiUser.user_id, channel, 
                        subject, `Testing ${channel} channel notification!`);
                    
                    if (result) {
                        output.innerHTML += `✅ ${channel} notification sent\n`;
                    } else {
                        output.innerHTML += `❌ Failed to send ${channel} notification\n`;
                    }
                }
            }
            break;
            
        case 'stress-test':
            output.innerHTML += 'Starting stress test (10 notifications)...\n';
            const stressUser = await createTestUser('stress@example.com', '+15559999999');
            if (stressUser) {
                output.innerHTML += `User created: ID ${stressUser.user_id}\n`;
                let successCount = 0;
                
                for (let i = 0; i < 10; i++) {
                    const type = ['email', 'sms'][i % 2];
                    const subject = type === 'email' ? `Stress Test ${i+1}` : null;
                    const result = await sendTestNotification(stressUser.user_id, type, 
                        subject, `Stress test message ${i+1}`);
                    
                    if (result) {
                        successCount++;
                        output.innerHTML += `.`;
                    } else {
                        output.innerHTML += `x`;
                    }
                }
                
                output.innerHTML += `\n✅ Sent ${successCount}/10 notifications successfully\n`;
            }
            break;
    }
    
    output.innerHTML += '\nScenario complete!';
}

// Helper Functions for Scenarios
async function createTestUser(email, phone) {
    try {
        const response = await fetch(`${USER_DB}/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                phone_number: phone,
                country_code: phone ? '+1' : null
            })
        });
        
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to create test user:', error);
    }
    return null;
}

async function addTestDevice(userId, token, type) {
    try {
        const response = await fetch(`${USER_DB}/users/${userId}/devices`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_token: token,
                device_type: type
            })
        });
        
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to add test device:', error);
    }
    return null;
}

async function sendTestNotification(userId, type, subject, message) {
    try {
        const response = await fetch(`${API_BASE}/api/v1/notifications/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                type: type,
                subject: subject,
                message: message,
                metadata: {
                    source: 'demo-scenario',
                    timestamp: new Date().toISOString()
                }
            })
        });
        
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to send test notification:', error);
    }
    return null;
}

// Logging
function addLog(message, type = 'info') {
    const log = document.getElementById('response-log');
    const timestamp = new Date().toLocaleTimeString();
    const prefix = {
        'info': '[INFO]',
        'success': '[SUCCESS]',
        'error': '[ERROR]',
        'warning': '[WARNING]'
    }[type] || '[LOG]';
    
    log.innerHTML += `${timestamp} ${prefix} ${message}\n`;
    log.scrollTop = log.scrollHeight;
}

function clearLog() {
    document.getElementById('response-log').innerHTML = '';
    addLog('Log cleared', 'info');
}