const express = require('express');
const path = require('path');
const axios = require('axios');
const WebSocket = require('ws');
const http = require('http');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = process.env.DASHBOARD_PORT || 5317;
const QUERY_SERVICE_URL = process.env.QUERY_SERVICE_URL || 'http://localhost:7539';
const ALERT_MANAGER_URL = process.env.ALERT_MANAGER_URL || 'http://localhost:6428';

// Middleware
app.use(express.json());
app.use(express.static('public'));

// API Routes
app.get('/api/dashboard/metrics', async (req, res) => {
    try {
        const endTime = new Date();
        const startTime = new Date(endTime.getTime() - 60 * 60 * 1000); // Last hour
        
        // Get multiple metrics
        const metrics = ['cpu.usage', 'memory.usage_percent', 'disk.usage_percent'];
        const metricsData = {};
        
        for (const metric of metrics) {
            try {
                const response = await axios.get(`${QUERY_SERVICE_URL}/query/metrics`, {
                    params: {
                        start: startTime.toISOString().replace('Z', '+00:00').split('.')[0],
                        end: endTime.toISOString().replace('Z', '+00:00').split('.')[0],
                        metric: metric
                    },
                    timeout: 5000
                });
                metricsData[metric] = response.data;
            } catch (error) {
                console.error(`Failed to fetch ${metric}:`, error.message);
                metricsData[metric] = { data: [], count: 0, error: error.message };
            }
        }
        
        res.json({
            timestamp: endTime.toISOString(),
            metrics: metricsData
        });
        
    } catch (error) {
        console.error('Dashboard metrics error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/dashboard/latest', async (req, res) => {
    try {
        const metrics = ['cpu.usage', 'memory.usage_percent', 'disk.usage_percent'];
        const latestData = {};
        
        for (const metric of metrics) {
            try {
                const response = await axios.get(`${QUERY_SERVICE_URL}/query/latest/${metric}`, {
                    timeout: 5000
                });
                latestData[metric] = response.data;
            } catch (error) {
                console.error(`Failed to fetch latest ${metric}:`, error.message);
                latestData[metric] = { error: error.message };
            }
        }
        
        res.json(latestData);
        
    } catch (error) {
        console.error('Latest metrics error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/dashboard/alerts', async (req, res) => {
    try {
        const response = await axios.get(`${ALERT_MANAGER_URL}/alerts/active`, {
            timeout: 5000
        });
        res.json(response.data);
        
    } catch (error) {
        console.error('Alerts fetch error:', error);
        res.status(500).json({ error: error.message, alerts: [], count: 0 });
    }
});

// Health check
app.get('/health', async (req, res) => {
    try {
        const checks = {};
        
        // Check query service
        try {
            await axios.get(`${QUERY_SERVICE_URL}/health`, { timeout: 3000 });
            checks.query_service = { status: 'ok' };
        } catch (error) {
            checks.query_service = { status: 'error', error: error.message };
        }
        
        // Check alert manager
        try {
            await axios.get(`${ALERT_MANAGER_URL}/health`, { timeout: 3000 });
            checks.alert_manager = { status: 'ok' };
        } catch (error) {
            checks.alert_manager = { status: 'error', error: error.message };
        }
        
        const healthy = Object.values(checks).every(check => check.status === 'ok');
        
        res.status(healthy ? 200 : 503).json({
            healthy,
            checks,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        res.status(503).json({
            healthy: false,
            error: error.message
        });
    }
});

// WebSocket for real-time updates
wss.on('connection', (ws) => {
    console.log('Client connected to WebSocket');
    
    ws.on('close', () => {
        console.log('Client disconnected from WebSocket');
    });
    
    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
    });
});

// Broadcast updates to all connected clients
async function broadcastUpdate() {
    if (wss.clients.size === 0) return;
    
    try {
        // Get latest metrics
        const response = await axios.get(`http://localhost:${PORT}/api/dashboard/latest`);
        const data = {
            type: 'metrics_update',
            data: response.data,
            timestamp: new Date().toISOString()
        };
        
        wss.clients.forEach((client) => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify(data));
            }
        });
        
    } catch (error) {
        console.error('Broadcast update error:', error);
    }
}

// Start broadcasting updates every 30 seconds
setInterval(broadcastUpdate, 30000);

// Root route - serve dashboard
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/alerts', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'alerts.html'));
});

// Start server
server.listen(PORT, '0.0.0.0', () => {
    console.log(`Dashboard server running on port ${PORT}`);
    console.log(`Query Service URL: ${QUERY_SERVICE_URL}`);
    console.log(`Alert Manager URL: ${ALERT_MANAGER_URL}`);
});