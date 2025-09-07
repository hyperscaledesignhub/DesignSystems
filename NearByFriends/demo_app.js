// Nearby Friends Demo Application - FIXED VERSION
const API_BASE_URL = 'http://localhost:8900';
const WS_URL = 'ws://localhost:8904/ws';

// Global state
let currentUser = null;
let websocket = null;
let map = null;
let markers = {};
let friendsData = {};
let activityCount = 0;
let metricsData = {
    requests: 0,
    updates: 0,
    messages: 0,
    latencies: []
};

// Demo users data
let demoUsers = [];

// Check if token is expired
function isTokenExpired(token) {
    if (!token) return true;
    
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const now = Math.floor(Date.now() / 1000);
        const timeUntilExpiry = payload.exp - now;
        
        console.log(`Token expires in ${Math.round(timeUntilExpiry / 60)} minutes`);
        
        // Consider token expired if less than 5 minutes remaining
        return timeUntilExpiry < 300;
    } catch (error) {
        console.error('Error checking token expiration:', error);
        return true;
    }
}

// Load demo users from config file
async function loadDemoUsers() {
    try {
        const response = await fetch('/demo_config.json?t=' + Date.now()); // Cache bust
        if (response.ok) {
            const config = await response.json();
            demoUsers = config.users.map(user => ({
                id: user.id,
                name: user.name,
                email: user.email,
                username: user.username,
                token: user.token,
                userId: user.id,
                lat: user.lat || 37.7749,
                lng: user.lng || -122.4194,
                tokenExpired: isTokenExpired(user.token)
            }));
            
            const validUsers = demoUsers.filter(u => !u.tokenExpired);
            const expiredUsers = demoUsers.filter(u => u.tokenExpired);
            
            console.log(`Loaded ${demoUsers.length} demo users (${validUsers.length} valid, ${expiredUsers.length} expired)`);
            
            if (expiredUsers.length > 0) {
                addActivity(`⚠️ ${expiredUsers.length} users have expired tokens`, 'fa-exclamation-triangle');
            }
            
            addActivity(`${validUsers.length} demo users ready`, 'fa-users');
            return true;
        }
    } catch (error) {
        console.error('Error loading demo users:', error);
        addActivity('Failed to load demo users', 'fa-exclamation-triangle');
        return false;
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Initializing Nearby Friends Demo...');
    
    initializeMap();
    startClock();
    
    // Load demo users and populate UI
    const usersLoaded = await loadDemoUsers();
    if (usersLoaded) {
        populateUserSelect();
        document.getElementById('total-users').textContent = demoUsers.length;
        addActivity(`Demo ready with ${demoUsers.length} users`, 'fa-check');
    }
    
    // Check services health
    checkServicesHealth();
    setInterval(checkServicesHealth, 10000);
});

// Initialize Leaflet map
function initializeMap() {
    try {
        map = L.map('map').setView([37.7749, -122.4194], 15);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        addActivity('Map initialized', 'fa-map');
        console.log('Map initialized successfully');
    } catch (error) {
        console.error('Map initialization error:', error);
        addActivity('Map initialization failed', 'fa-exclamation-triangle');
    }
}

// Populate user select dropdown
function populateUserSelect() {
    const select = document.getElementById('user-select');
    if (!select) return;
    
    select.innerHTML = '<option value="">-- Select User --</option>';
    
    demoUsers.forEach(user => {
        const option = document.createElement('option');
        option.value = user.id;
        
        if (user.tokenExpired) {
            option.textContent = `${user.name} (Token Expired)`;
            option.style.color = '#dc3545';
            option.disabled = true;
        } else {
            option.textContent = user.name;
        }
        
        select.appendChild(option);
    });
    
    const validUsers = demoUsers.filter(u => !u.tokenExpired).length;
    console.log(`User select populated: ${validUsers}/${demoUsers.length} users available`);
}

// Login user
async function loginUser() {
    const select = document.getElementById('user-select');
    const userId = parseInt(select.value);
    
    if (!userId) {
        alert('Please select a user');
        return;
    }
    
    const user = demoUsers.find(u => u.id === userId);
    if (!user) {
        alert('User not found');
        return;
    }
    
    if (!user.token) {
        alert('User token not found. Please refresh the page.');
        return;
    }
    
    if (user.tokenExpired || isTokenExpired(user.token)) {
        alert('User token has expired. Please refresh the demo data.');
        addActivity('Login failed: Token expired', 'fa-exclamation-triangle');
        return;
    }
    
    currentUser = user;
    console.log('Logging in as:', user.name, 'ID:', user.id);
    
    // Update UI
    document.getElementById('current-user-info').innerHTML = `
        <div class="user-card current-user">
            <div class="user-avatar">${user.name.charAt(0)}</div>
            <div class="user-info">
                <div class="user-name">${user.name}</div>
                <div class="user-status">
                    <i class="fas fa-circle" style="color: #4caf50; font-size: 8px;"></i>
                    Online - ${user.email}
                </div>
            </div>
        </div>
        <div class="connection-status" id="ws-status">
            <i class="fas fa-plug"></i>
            <span>Connecting to WebSocket...</span>
        </div>
    `;
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Load nearby friends
    await loadNearbyFriends();
    
    // Set initial location
    updateUserLocation(user.lat, user.lng).catch(err => {
        console.error('Initial location update failed:', err);
    });
    
    addActivity(`${user.name} logged in`, 'fa-sign-in-alt');
    incrementMetric('requests');
}

// Connect to WebSocket
function connectWebSocket() {
    if (websocket) {
        websocket.close();
    }
    
    try {
        websocket = new WebSocket(WS_URL);
        
        websocket.onopen = () => {
            console.log('WebSocket connected');
            websocket.send(JSON.stringify({
                type: 'auth',
                token: currentUser.token
            }));
            updateConnectionStatus(true);
            addActivity('WebSocket connected', 'fa-plug');
        };
        
        websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
                incrementMetric('messages');
            } catch (error) {
                console.error('WebSocket message error:', error);
            }
        };
        
        websocket.onclose = () => {
            updateConnectionStatus(false);
            addActivity('WebSocket disconnected', 'fa-plug');
        };
        
        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };
    } catch (error) {
        console.error('WebSocket connection error:', error);
        addActivity('WebSocket connection failed', 'fa-exclamation-triangle');
    }
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    console.log('WebSocket message:', data.type);
    
    switch(data.type) {
        case 'connected':
            console.log('WebSocket authenticated');
            break;
            
        case 'initial_nearby':
            if (data.friends) {
                updateNearbyFriendsList(data.friends);
            }
            break;
            
        case 'nearby_update':
            handleNearbyUpdate(data);
            break;
            
        case 'location_updated':
            console.log('Location update confirmed');
            break;
            
        case 'pong':
            console.log('Heartbeat received');
            break;
    }
}

// Handle nearby friend update
function handleNearbyUpdate(data) {
    const friend = demoUsers.find(u => u.id === data.friend_id);
    if (friend) {
        updateFriendMarker(friend, data.latitude, data.longitude);
        addActivity(`${friend.name} is ${data.distance_miles.toFixed(2)} miles away`, 'fa-location-arrow');
        loadNearbyFriends();
    }
}

// Update user location
async function updateUserLocation(lat, lng) {
    if (!currentUser || !currentUser.token) {
        console.error('No current user or token');
        return;
    }
    
    // Check if token is expired before making API call
    if (isTokenExpired(currentUser.token)) {
        addActivity('Cannot update location - token expired', 'fa-exclamation-triangle');
        showTokenExpiredMessage();
        throw new Error('Token expired');
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/location/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentUser.token}`
            },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        });
        
        if (response.ok) {
            console.log(`Location updated: (${lat}, ${lng})`);
            updateUserMarker(lat, lng);
            
            // Send via WebSocket
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    type: 'location_update',
                    latitude: lat,
                    longitude: lng
                }));
            }
            
            incrementMetric('updates');
            return true;
        } else if (response.status === 401) {
            // Token expired or invalid
            addActivity('Location update failed - token expired', 'fa-exclamation-triangle');
            showTokenExpiredMessage();
            throw new Error('Token expired');
        } else {
            const errorText = await response.text();
            console.error('Location update failed:', response.status, errorText);
            throw new Error(`Location update failed: ${response.status}`);
        }
    } catch (error) {
        console.error('Error updating location:', error);
        throw error;
    }
}

// Load nearby friends
async function loadNearbyFriends() {
    if (!currentUser || !currentUser.token) return;
    
    // Check if token is expired before making API call
    if (isTokenExpired(currentUser.token)) {
        addActivity('Token expired - please refresh demo data', 'fa-exclamation-triangle');
        showTokenExpiredMessage();
        return;
    }
    
    try {
        const userId = currentUser.id;
        const response = await fetch(`${API_BASE_URL}/api/location/nearby/${userId}`, {
            headers: {
                'Authorization': `Bearer ${currentUser.token}`
            }
        });
        
        if (response.ok) {
            const friends = await response.json();
            console.log(`Found ${friends.length} nearby friends`);
            updateNearbyFriendsList(friends);
            incrementMetric('requests');
        } else if (response.status === 401) {
            // Token expired or invalid
            addActivity('Authentication failed - token may be expired', 'fa-exclamation-triangle');
            showTokenExpiredMessage();
        } else {
            console.error('Failed to load nearby friends:', response.status);
            addActivity(`Failed to load friends: ${response.status}`, 'fa-exclamation-triangle');
        }
    } catch (error) {
        console.error('Error loading nearby friends:', error);
        addActivity('Network error loading friends', 'fa-exclamation-triangle');
    }
}

// Update nearby friends list UI
function updateNearbyFriendsList(friends) {
    const container = document.getElementById('nearby-friends-list');
    const countElement = document.getElementById('nearby-count');
    
    if (!container || !countElement) return;
    
    countElement.textContent = friends.length;
    
    if (friends.length === 0) {
        container.innerHTML = '<p style="color: #999; text-align: center;">No friends nearby</p>';
        return;
    }
    
    container.innerHTML = friends.map(friend => {
        const demoUser = demoUsers.find(u => u.id === friend.user_id);
        const name = demoUser ? demoUser.name : `User ${friend.user_id}`;
        const initial = name.charAt(0);
        const distance = friend.distance_miles;
        const badgeClass = distance > 3 ? 'far' : '';
        
        // Update marker on map
        if (demoUser) {
            updateFriendMarker(demoUser, friend.latitude, friend.longitude);
        }
        
        return `
            <div class="user-card" onclick="focusOnFriend(${friend.user_id})">
                <div class="user-avatar">${initial}</div>
                <div class="user-info">
                    <div class="user-name">${name}</div>
                    <div class="user-status">
                        <i class="fas fa-map-marker-alt"></i>
                        ${new Date(friend.last_updated).toLocaleTimeString()}
                    </div>
                </div>
                <div class="distance-badge ${badgeClass}">${distance.toFixed(2)} mi</div>
            </div>
        `;
    }).join('');
}

// Update user marker on map
function updateUserMarker(lat, lng) {
    if (!map || !currentUser) return;
    
    const markerId = `user-${currentUser.id}`;
    
    if (markers[markerId]) {
        markers[markerId].setLatLng([lat, lng]);
    } else {
        const marker = L.marker([lat, lng], {
            icon: L.divIcon({
                className: 'custom-marker',
                html: `<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.3);">${currentUser.name.charAt(0)}</div>`,
                iconSize: [35, 35],
                iconAnchor: [17, 17]
            })
        }).addTo(map);
        
        marker.bindPopup(`<b>${currentUser.name}</b><br>You are here`);
        markers[markerId] = marker;
    }
    
    map.setView([lat, lng], 15);
}

// Update friend marker on map
function updateFriendMarker(friend, lat, lng) {
    if (!map) return;
    
    const markerId = `friend-${friend.id}`;
    
    if (markers[markerId]) {
        markers[markerId].setLatLng([lat, lng]);
    } else {
        const marker = L.marker([lat, lng], {
            icon: L.divIcon({
                className: 'custom-marker',
                html: `<div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">${friend.name.charAt(0)}</div>`,
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            })
        }).addTo(map);
        
        marker.bindPopup(`<b>${friend.name}</b><br>${friend.email}`);
        markers[markerId] = marker;
    }
}

// Share location (continuous updates)
function shareLocation() {
    if (!currentUser) {
        alert('Please login first');
        return;
    }
    
    let moveCount = 0;
    const moveInterval = setInterval(() => {
        if (!currentUser || moveCount >= 10) {
            clearInterval(moveInterval);
            return;
        }
        
        // Small random movement
        const newLat = currentUser.lat + (Math.random() - 0.5) * 0.001;
        const newLng = currentUser.lng + (Math.random() - 0.5) * 0.001;
        
        currentUser.lat = newLat;
        currentUser.lng = newLng;
        
        updateUserLocation(newLat, newLng).catch(err => {
            console.error('Location share error:', err);
        });
        
        moveCount++;
    }, 5000);
    
    addActivity('Started sharing location', 'fa-broadcast-tower');
}

// Stop sharing location
function stopSharing() {
    addActivity('Stopped sharing location', 'fa-stop-circle');
}

// Center map on user
function centerOnUser() {
    if (currentUser && map) {
        const markerId = `user-${currentUser.id}`;
        if (markers[markerId]) {
            map.setView([currentUser.lat, currentUser.lng], 16);
            markers[markerId].openPopup();
        } else {
            updateUserMarker(currentUser.lat, currentUser.lng);
        }
        addActivity('Map centered on you', 'fa-crosshairs');
    }
}

// Show all friends on map
function showAllFriends() {
    if (!map) return;
    
    const bounds = L.latLngBounds();
    let hasMarkers = false;
    
    Object.keys(markers).forEach(key => {
        if (markers[key]) {
            bounds.extend(markers[key].getLatLng());
            hasMarkers = true;
        }
    });
    
    if (hasMarkers && bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50] });
        addActivity('Showing all friends', 'fa-users');
    }
}

// Focus on specific friend
function focusOnFriend(friendId) {
    const friend = demoUsers.find(u => u.id === friendId);
    const markerId = `friend-${friendId}`;
    
    if (friend && markers[markerId] && map) {
        map.setView(markers[markerId].getLatLng(), 17);
        markers[markerId].openPopup();
    }
}

// Run demo scenarios
async function runDemoScenario(scenario) {
    console.log('Running demo scenario:', scenario);
    
    switch(scenario) {
        case 'rush-hour':
            runRushHourDemo();
            break;
        case 'friends-meetup':
            runFriendsMeetupDemo();
            break;
        case 'moving':
            runMovingDemo();
            break;
    }
}

// Rush hour demo
async function runRushHourDemo() {
    addActivity('Starting Rush Hour demo', 'fa-city');
    
    let iterations = 0;
    const moveAllUsers = setInterval(() => {
        if (iterations >= 10) {
            clearInterval(moveAllUsers);
            addActivity('Rush Hour demo completed', 'fa-check-circle');
            return;
        }
        
        demoUsers.forEach(user => {
            if (user.token) {
                const newLat = user.lat + (Math.random() - 0.5) * 0.002;
                const newLng = user.lng + (Math.random() - 0.5) * 0.002;
                
                fetch(`${API_BASE_URL}/api/location/update`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${user.token}`
                    },
                    body: JSON.stringify({ latitude: newLat, longitude: newLng })
                }).catch(err => console.error('Rush hour update error:', err));
                
                user.lat = newLat;
                user.lng = newLng;
                
                const markerId = `friend-${user.id}`;
                if (markers[markerId]) {
                    updateFriendMarker(user, newLat, newLng);
                }
            }
        });
        
        iterations++;
    }, 3000);
}

// Friends meetup demo
async function runFriendsMeetupDemo() {
    addActivity('Starting Friends Meetup demo', 'fa-coffee');
    
    const meetupPoint = { lat: 37.7750, lng: -122.4190 };
    let iterations = 0;
    
    const convergeInterval = setInterval(() => {
        if (iterations >= 10) {
            clearInterval(convergeInterval);
            addActivity('Friends Meetup demo completed', 'fa-check-circle');
            return;
        }
        
        demoUsers.forEach(user => {
            if (user.token) {
                const latDiff = meetupPoint.lat - user.lat;
                const lngDiff = meetupPoint.lng - user.lng;
                
                const newLat = user.lat + latDiff * 0.1;
                const newLng = user.lng + lngDiff * 0.1;
                
                fetch(`${API_BASE_URL}/api/location/update`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${user.token}`
                    },
                    body: JSON.stringify({ latitude: newLat, longitude: newLng })
                }).catch(err => console.error('Meetup update error:', err));
                
                user.lat = newLat;
                user.lng = newLng;
                
                const markerId = `friend-${user.id}`;
                if (markers[markerId]) {
                    updateFriendMarker(user, newLat, newLng);
                }
            }
        });
        
        iterations++;
    }, 2000);
}

// Moving demo
async function runMovingDemo() {
    if (!currentUser) {
        alert('Please login first to run moving demo');
        return;
    }
    
    addActivity('Starting Moving demo', 'fa-route');
    
    const route = [
        { lat: 37.7749, lng: -122.4194, name: "Starting Point" },
        { lat: 37.7755, lng: -122.4200, name: "North Point" },
        { lat: 37.7760, lng: -122.4180, name: "East Point" },
        { lat: 37.7750, lng: -122.4170, name: "Southeast Point" },
        { lat: 37.7740, lng: -122.4190, name: "Final Point" }
    ];
    
    let routeIndex = 0;
    
    const moveInterval = setInterval(async () => {
        if (routeIndex >= route.length) {
            clearInterval(moveInterval);
            addActivity('Moving demo completed', 'fa-check-circle');
            return;
        }
        
        const point = route[routeIndex];
        addActivity(`Moving to ${point.name}`, 'fa-location-arrow');
        
        try {
            await updateUserLocation(point.lat, point.lng);
            currentUser.lat = point.lat;
            currentUser.lng = point.lng;
            addActivity(`✅ Reached ${point.name}`, 'fa-map-marker-alt');
        } catch (error) {
            console.error('Moving demo error:', error);
            // Update map anyway
            updateUserMarker(point.lat, point.lng);
            currentUser.lat = point.lat;
            currentUser.lng = point.lng;
            addActivity(`⚠️ Updated map for ${point.name}`, 'fa-exclamation-triangle');
        }
        
        routeIndex++;
    }, 3000);
}

// Check services health
async function checkServicesHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            const health = await response.json();
            updateServicesStatus(health.services);
        }
    } catch (error) {
        console.error('Error checking services health:', error);
    }
}

// Update services status UI
function updateServicesStatus(services) {
    const container = document.getElementById('services-grid');
    if (!container) return;
    
    const serviceNames = {
        'user-service': 'User Service',
        'friend-service': 'Friend Service',
        'location-service': 'Location Service',
        'websocket-gateway': 'WebSocket'
    };
    
    container.innerHTML = '';
    let healthyCount = 0;
    
    Object.entries(services).forEach(([service, status]) => {
        const isHealthy = status === 'healthy';
        if (isHealthy) healthyCount++;
        
        const div = document.createElement('div');
        div.className = `service-status ${isHealthy ? 'healthy' : 'unhealthy'}`;
        div.innerHTML = `
            <i class="fas fa-${isHealthy ? 'check' : 'times'}-circle"></i>
            ${serviceNames[service] || service}
        `;
        container.appendChild(div);
    });
    
    // Add gateway and UI
    ['API Gateway', 'UI Service'].forEach(service => {
        const div = document.createElement('div');
        div.className = 'service-status healthy';
        div.innerHTML = `
            <i class="fas fa-check-circle"></i>
            ${service}
        `;
        container.appendChild(div);
        healthyCount++;
    });
    
    const statusElement = document.getElementById('services-status');
    if (statusElement) {
        statusElement.textContent = `${healthyCount}/6 Services`;
    }
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('ws-status');
    if (statusEl) {
        statusEl.className = connected ? 'connection-status' : 'connection-status disconnected';
        statusEl.innerHTML = `
            <i class="fas fa-plug"></i>
            <span>WebSocket ${connected ? 'Connected' : 'Disconnected'}</span>
        `;
    }
}

// Add activity to feed
function addActivity(text, icon = 'fa-info-circle') {
    const feed = document.getElementById('activity-feed');
    if (!feed) return;
    
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <div class="activity-icon">
            <i class="fas ${icon}"></i>
        </div>
        <div class="activity-content">
            <div class="activity-text">${text}</div>
            <div class="activity-time">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    
    feed.insertBefore(item, feed.firstChild);
    
    // Keep only last 20 activities
    while (feed.children.length > 20) {
        feed.removeChild(feed.lastChild);
    }
    
    activityCount++;
}

// Increment metric
function incrementMetric(metric) {
    metricsData[metric]++;
    const element = document.getElementById(`metric-${metric}`);
    if (element) {
        element.textContent = metricsData[metric];
    }
}

// Update latency metric
function updateLatency(latency) {
    metricsData.latencies.push(latency);
    if (metricsData.latencies.length > 100) {
        metricsData.latencies.shift();
    }
    
    const avgLatency = metricsData.latencies.reduce((a, b) => a + b, 0) / metricsData.latencies.length;
    const element = document.getElementById('metric-latency');
    if (element) {
        element.textContent = Math.round(avgLatency) + 'ms';
    }
}

// Start clock
function startClock() {
    setInterval(() => {
        const element = document.getElementById('current-time');
        if (element) {
            element.textContent = new Date().toLocaleTimeString();
        }
    }, 1000);
}

// Send heartbeat
setInterval(() => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);

// Show token expired message
function showTokenExpiredMessage() {
    const container = document.getElementById('nearby-friends-list');
    if (container) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #dc3545;">
                <i class="fas fa-exclamation-triangle" style="font-size: 24px; margin-bottom: 10px;"></i>
                <p>Tokens have expired!</p>
                <button class="btn btn-primary" onclick="refreshDemoData()" style="margin-top: 10px;">
                    <i class="fas fa-sync"></i> Refresh Demo Data
                </button>
            </div>
        `;
    }
    
    document.getElementById('nearby-count').textContent = '0';
}

// Refresh demo data (regenerate users and tokens)
async function refreshDemoData() {
    addActivity('Refreshing demo data...', 'fa-sync');
    
    try {
        // Call the setup script to regenerate demo data
        const response = await fetch('/api/refresh-demo-data', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to refresh demo data via API');
        }
        
        // Fallback: Show instructions to user
        showRefreshInstructions();
        
    } catch (error) {
        console.error('Auto-refresh failed:', error);
        showRefreshInstructions();
    }
}

// Show manual refresh instructions
function showRefreshInstructions() {
    const container = document.getElementById('nearby-friends-list');
    if (container) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; background: #fff3cd; border-radius: 8px; margin: 10px 0;">
                <h4 style="color: #856404; margin-bottom: 15px;">
                    <i class="fas fa-tools"></i> Refresh Required
                </h4>
                <p style="color: #856404; margin-bottom: 15px;">
                    Demo tokens have expired. Please run this command to refresh:
                </p>
                <code style="background: #333; color: #fff; padding: 10px; border-radius: 4px; display: block; margin: 10px 0;">
                    python3 setup_demo_data.py
                </code>
                <p style="color: #856404; font-size: 12px; margin-top: 10px;">
                    Then refresh this page (Ctrl+F5)
                </p>
                <button class="btn btn-secondary" onclick="location.reload()" style="margin-top: 10px;">
                    <i class="fas fa-redo"></i> Reload Page
                </button>
            </div>
        `;
    }
    
    addActivity('Please refresh demo data manually', 'fa-exclamation-triangle');
}

// Check for token expiration periodically
setInterval(() => {
    if (currentUser && isTokenExpired(currentUser.token)) {
        addActivity('Current user token expired', 'fa-exclamation-triangle');
        showTokenExpiredMessage();
        currentUser = null; // Clear current user
    }
}, 60000); // Check every minute

console.log('Demo app loaded successfully');