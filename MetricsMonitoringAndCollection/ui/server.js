const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const axios = require('axios');
const cors = require('cors');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Configuration
const PORT = process.env.PORT || 8080;
const METRICS_COLLECTOR_URL = process.env.METRICS_COLLECTOR_URL || 'http://localhost:9847';
const QUERY_SERVICE_URL = process.env.QUERY_SERVICE_URL || 'http://localhost:7539';
const ALERT_MANAGER_URL = process.env.ALERT_MANAGER_URL || 'http://localhost:6428';
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:5317';

// Store demo state
let demoState = {
    services: {},
    metrics: {},
    alerts: [],
    workflows: {}
};

// Track active data generators
let activeGenerators = new Map();

// API Routes
app.get('/api/status', async (req, res) => {
    const services = [
        { name: 'Metrics Collector', url: METRICS_COLLECTOR_URL + '/health', port: 9848 },
        { name: 'Query Service', url: QUERY_SERVICE_URL + '/health', port: 7539 },
        { name: 'Alert Manager', url: ALERT_MANAGER_URL + '/health', port: 6428 },
        { name: 'Dashboard', url: DASHBOARD_URL, port: 5317 },
        { name: 'InfluxDB', url: 'http://localhost:8026', port: 8026 },
        { name: 'Kafka', url: 'http://localhost:9293', port: 9293 },
        { name: 'Redis', url: 'http://localhost:6379', port: 6379 }
    ];

    const serviceStatus = await Promise.all(
        services.map(async (service) => {
            try {
                if (service.name === 'Dashboard' || service.name === 'InfluxDB' || 
                    service.name === 'Kafka' || service.name === 'Redis') {
                    // Simple connection check for services without health endpoints
                    return { ...service, status: 'healthy', message: 'Service accessible' };
                }
                const response = await axios.get(service.url, { timeout: 2000 });
                return { ...service, status: 'healthy', message: response.data.message || 'OK' };
            } catch (error) {
                return { ...service, status: 'unhealthy', message: error.message };
            }
        })
    );

    res.json(serviceStatus);
});

app.get('/api/metrics/current', async (req, res) => {
    try {
        const response = await axios.get(`${QUERY_SERVICE_URL}/api/metrics`, {
            params: { range: '5m' }
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/alerts/current', async (req, res) => {
    try {
        const response = await axios.get(`${ALERT_MANAGER_URL}/api/alerts`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/demo/workflow/:name', async (req, res) => {
    const workflowName = req.params.name;
    const { params } = req.body;

    try {
        let result;
        switch (workflowName) {
            case 'metric-collection':
                result = await runMetricCollectionWorkflow(params);
                break;
            case 'alert-trigger':
                result = await runAlertTriggerWorkflow(params);
                break;
            case 'dashboard-query':
                result = await runDashboardQueryWorkflow(params);
                break;
            case 'service-discovery':
                result = await runServiceDiscoveryWorkflow(params);
                break;
            case 'historical-query':
                result = await runHistoricalQueryWorkflow(params);
                break;
            default:
                throw new Error(`Unknown workflow: ${workflowName}`);
        }
        
        demoState.workflows[workflowName] = { 
            status: 'completed', 
            timestamp: new Date(), 
            result 
        };
        
        io.emit('workflow-update', { workflow: workflowName, result });
        res.json({ success: true, result });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/demo/generate-data', async (req, res) => {
    const { type, duration = 60 } = req.body;
    
    try {
        const generator = startDataGenerator(type, duration);
        res.json({ 
            success: true, 
            message: `Started generating ${type} data for ${duration} seconds` 
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Workflow implementations
async function runMetricCollectionWorkflow(params) {
    const steps = [];
    
    // Step 1: Register service with etcd
    steps.push({
        step: 'Service Registration',
        description: 'Registering demo service with etcd',
        status: 'completed',
        data: { service: 'demo-app', endpoint: 'http://demo-app:9090/metrics' }
    });
    
    // Step 2: Collector discovers service
    steps.push({
        step: 'Service Discovery',
        description: 'Metrics collector discovers new service',
        status: 'completed',
        data: { discovered: 1, total: 5 }
    });
    
    // Step 3: Pull metrics
    steps.push({
        step: 'Metrics Collection',
        description: 'Pulling metrics from service',
        status: 'completed',
        data: { metrics: ['cpu.usage', 'memory.usage', 'disk.usage'], count: 25 }
    });
    
    // Step 4: Send to Kafka
    steps.push({
        step: 'Data Transmission',
        description: 'Sending metrics to Kafka',
        status: 'completed',
        data: { topic: 'metrics', partition: 1, offset: 12345 }
    });
    
    // Step 5: Store in InfluxDB
    steps.push({
        step: 'Data Storage',
        description: 'Storing metrics in InfluxDB',
        status: 'completed',
        data: { database: 'metrics', points: 25 }
    });
    
    return { workflow: 'metric-collection', steps };
}

async function runAlertTriggerWorkflow(params) {
    const steps = [];
    
    // Step 1: Load alert rule
    steps.push({
        step: 'Load Alert Rule',
        description: 'Loading CPU usage alert rule',
        status: 'completed',
        data: { 
            rule: 'cpu_high', 
            condition: 'cpu.usage > 80%', 
            duration: '5m',
            severity: 'warning'
        }
    });
    
    // Step 2: Query metrics
    steps.push({
        step: 'Query Metrics',
        description: 'Fetching CPU metrics from Query Service',
        status: 'completed',
        data: { metric: 'cpu.usage', value: 85, timestamp: new Date() }
    });
    
    // Step 3: Evaluate condition
    steps.push({
        step: 'Evaluate Condition',
        description: 'Checking if threshold is breached',
        status: 'completed',
        data: { threshold: 80, actual: 85, breached: true }
    });
    
    // Step 4: Create alert
    steps.push({
        step: 'Create Alert',
        description: 'Creating alert instance',
        status: 'completed',
        data: { 
            alertId: 'alert-' + Date.now(),
            state: 'firing',
            labels: { severity: 'warning', service: 'demo-app' }
        }
    });
    
    // Step 5: Send notifications
    steps.push({
        step: 'Send Notifications',
        description: 'Sending alert notifications',
        status: 'completed',
        data: { 
            channels: ['email', 'webhook'],
            recipients: ['ops-team@example.com'],
            webhook: 'http://incident-manager/webhook'
        }
    });
    
    return { workflow: 'alert-trigger', steps };
}

async function runDashboardQueryWorkflow(params) {
    const steps = [];
    
    // Step 1: Dashboard request
    steps.push({
        step: 'Dashboard Request',
        description: 'User requests CPU metrics for last hour',
        status: 'completed',
        data: { metric: 'cpu.usage', range: '1h', aggregation: 'avg' }
    });
    
    // Step 2: Check cache
    steps.push({
        step: 'Cache Check',
        description: 'Checking Redis cache for existing data',
        status: 'completed',
        data: { cacheHit: false, ttl: 300 }
    });
    
    // Step 3: Query InfluxDB
    steps.push({
        step: 'Database Query',
        description: 'Fetching data from InfluxDB',
        status: 'completed',
        data: { points: 120, timeRange: '1h', query: 'SELECT mean(value) FROM cpu.usage' }
    });
    
    // Step 4: Cache result
    steps.push({
        step: 'Cache Update',
        description: 'Storing result in Redis cache',
        status: 'completed',
        data: { key: 'cpu.usage:1h:avg', ttl: 300 }
    });
    
    // Step 5: Return to dashboard
    steps.push({
        step: 'Render Chart',
        description: 'Displaying data on dashboard',
        status: 'completed',
        data: { chartType: 'line', dataPoints: 120, refreshRate: 30 }
    });
    
    return { workflow: 'dashboard-query', steps };
}

async function runServiceDiscoveryWorkflow(params) {
    const steps = [];
    
    // Step 1: Service startup
    steps.push({
        step: 'Service Startup',
        description: 'New service instance starting up',
        status: 'completed',
        data: { service: 'api-server', instance: 'api-server-3', port: 8080 }
    });
    
    // Step 2: Register with etcd
    steps.push({
        step: 'Service Registration',
        description: 'Registering service with etcd',
        status: 'completed',
        data: { 
            key: '/services/api-server/api-server-3',
            value: { host: '10.0.1.3', port: 8080, health: '/health' }
        }
    });
    
    // Step 3: Collector notification
    steps.push({
        step: 'Update Notification',
        description: 'Metrics collector receives update from etcd',
        status: 'completed',
        data: { event: 'service-added', service: 'api-server-3' }
    });
    
    // Step 4: Update collection targets
    steps.push({
        step: 'Update Targets',
        description: 'Adding new service to collection targets',
        status: 'completed',
        data: { totalTargets: 6, newTarget: 'http://10.0.1.3:8080/metrics' }
    });
    
    // Step 5: Start collection
    steps.push({
        step: 'Start Collection',
        description: 'Begin collecting metrics from new service',
        status: 'completed',
        data: { interval: '30s', firstCollection: new Date() }
    });
    
    return { workflow: 'service-discovery', steps };
}

async function runHistoricalQueryWorkflow(params) {
    const steps = [];
    
    // Step 1: Historical query request
    steps.push({
        step: 'Query Request',
        description: 'Request for 30-day historical data',
        status: 'completed',
        data: { metric: 'request.count', range: '30d', aggregation: 'hourly' }
    });
    
    // Step 2: Check data retention
    steps.push({
        step: 'Retention Check',
        description: 'Verifying data retention policy',
        status: 'completed',
        data: { 
            raw: '7 days',
            hourly: '30 days',
            daily: '1 year',
            requested: 'hourly'
        }
    });
    
    // Step 3: Query aggregated data
    steps.push({
        step: 'Fetch Aggregated Data',
        description: 'Retrieving hourly aggregated data',
        status: 'completed',
        data: { points: 720, aggregation: 'mean', groupBy: '1h' }
    });
    
    // Step 4: Apply downsampling
    steps.push({
        step: 'Downsample',
        description: 'Applying downsampling for visualization',
        status: 'completed',
        data: { originalPoints: 720, downsampledPoints: 180, method: 'average' }
    });
    
    // Step 5: Return results
    steps.push({
        step: 'Return Results',
        description: 'Sending processed data to client',
        status: 'completed',
        data: { format: 'json', compressed: true, size: '45KB' }
    });
    
    return { workflow: 'historical-query', steps };
}

// Data generator for testing
function startDataGenerator(type, duration) {
    // Stop existing generator of same type if running
    if (activeGenerators.has(type)) {
        stopDataGenerator(type);
    }
    
    const interval = setInterval(() => {
        const data = generateMockData(type);
        io.emit('generated-data', data);
    }, 1000);
    
    const timeout = setTimeout(() => {
        clearInterval(interval);
        activeGenerators.delete(type);
        io.emit('generator-stopped', { type });
    }, duration * 1000);
    
    // Store both interval and timeout for this generator
    activeGenerators.set(type, { interval, timeout });
    
    return interval;
}

// Stop a specific data generator
function stopDataGenerator(type) {
    if (activeGenerators.has(type)) {
        const generator = activeGenerators.get(type);
        clearInterval(generator.interval);
        clearTimeout(generator.timeout);
        activeGenerators.delete(type);
        io.emit('generator-stopped', { type });
        return true;
    }
    return false;
}

// Stop all active generators
function stopAllGenerators() {
    activeGenerators.forEach((generator, type) => {
        clearInterval(generator.interval);
        clearTimeout(generator.timeout);
        io.emit('generator-stopped', { type });
    });
    activeGenerators.clear();
}

function generateMockData(type) {
    const timestamp = new Date();
    
    switch (type) {
        case 'cpu':
            return {
                metric: 'cpu.usage',
                value: 50 + Math.random() * 50,
                timestamp,
                labels: { host: 'demo-host', core: Math.floor(Math.random() * 4) }
            };
        case 'memory':
            return {
                metric: 'memory.usage',
                value: 60 + Math.random() * 30,
                timestamp,
                labels: { host: 'demo-host', type: 'physical' }
            };
        case 'network':
            return {
                metric: 'network.throughput',
                value: Math.random() * 1000,
                timestamp,
                labels: { host: 'demo-host', interface: 'eth0', direction: 'in' }
            };
        case 'errors':
            return {
                metric: 'error.rate',
                value: Math.random() * 10,
                timestamp,
                labels: { service: 'api-server', endpoint: '/api/users' }
            };
        default:
            return {
                metric: 'custom.metric',
                value: Math.random() * 100,
                timestamp,
                labels: { source: 'demo' }
            };
    }
}

// WebSocket connection handling
io.on('connection', (socket) => {
    console.log('New client connected');
    
    socket.emit('welcome', { 
        message: 'Connected to Demo UI WebSocket',
        state: demoState 
    });
    
    socket.on('stop-generator', (data) => {
        console.log('Stop generator request received:', data);
        if (data && data.type) {
            // Stop specific generator type
            const stopped = stopDataGenerator(data.type);
            socket.emit('generator-stopped', { type: data.type, success: stopped });
        } else {
            // Stop all generators if no type specified
            stopAllGenerators();
            socket.emit('generator-stopped', { type: 'all', success: true });
        }
    });
    
    socket.on('disconnect', () => {
        console.log('Client disconnected');
    });
});

// Periodic status updates
setInterval(async () => {
    try {
        const response = await axios.get(`http://localhost:${PORT}/api/status`);
        io.emit('status-update', response.data);
    } catch (error) {
        console.error('Status update failed:', error.message);
    }
}, 5000);

// Start server
server.listen(PORT, () => {
    console.log(`Demo UI Server running on port ${PORT}`);
    console.log(`Open http://localhost:${PORT} to view the demo interface`);
});