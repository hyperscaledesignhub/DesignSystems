// WebSocket connection
const socket = io();

// Chart instance
let metricsChart = null;
let chartData = {
    labels: [],
    datasets: [{
        label: 'Metric Value',
        data: [],
        borderColor: 'rgb(102, 126, 234)',
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        tension: 0.4
    }]
};

// State
let dataGenerator = null;
let metricsCounter = 0;
let queriesCounter = 0;
let alertsCounter = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeChart();
    fetchServiceStatus();
    connectWebSocket();
    startMetricsCounter();
});

// Initialize Chart.js
function initializeChart() {
    const ctx = document.getElementById('metrics-chart').getContext('2d');
    metricsChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Value'
                    }
                }
            }
        }
    });
}

// WebSocket connection
function connectWebSocket() {
    socket.on('welcome', (data) => {
        addConsoleLog('[WebSocket] Connected to Demo UI server');
    });

    socket.on('status-update', (data) => {
        updateServiceStatus(data);
    });

    socket.on('generated-data', (data) => {
        updateChart(data);
        metricsCounter++;
        updateMetricsCounter();
    });

    socket.on('generator-stopped', (data) => {
        if (data.success) {
            addConsoleLog(`[Generator] ${data.type} data generation stopped successfully`);
        } else {
            addConsoleLog(`[Generator] Failed to stop ${data.type} data generation`);
        }
    });

    socket.on('workflow-update', (data) => {
        addConsoleLog(`[Workflow] ${data.workflow} completed`);
    });

    socket.on('disconnect', () => {
        addConsoleLog('[WebSocket] Disconnected from server');
        document.getElementById('connection-status').innerHTML = '<span class="pulse" style="background: red;"></span> Disconnected';
    });

    socket.on('reconnect', () => {
        addConsoleLog('[WebSocket] Reconnected to server');
        document.getElementById('connection-status').innerHTML = '<span class="pulse"></span> Connected';
    });
}

// Fetch and display service status
async function fetchServiceStatus() {
    try {
        const response = await axios.get('/api/status');
        updateServiceStatus(response.data);
    } catch (error) {
        addConsoleLog('[Error] Failed to fetch service status: ' + error.message);
    }
}

// Update service status display
function updateServiceStatus(services) {
    const grid = document.getElementById('services-grid');
    grid.innerHTML = services.map(service => `
        <div class="service-card ${service.status}">
            <div class="service-name">${service.name}</div>
            <div class="service-port">Port: ${service.port}</div>
            <div class="service-status" style="color: ${service.status === 'healthy' ? '#10b981' : '#ef4444'}">
                ${service.status === 'healthy' ? '✓ Healthy' : '✗ Unhealthy'}
            </div>
        </div>
    `).join('');
}

// Run workflow demonstration
async function runWorkflow(workflowName) {
    addConsoleLog(`[Workflow] Starting ${workflowName} demonstration...`);
    
    const vizContainer = document.getElementById('workflow-viz');
    vizContainer.innerHTML = '<div class="workflow-placeholder">Loading workflow...</div>';
    
    try {
        const response = await axios.post(`/api/demo/workflow/${workflowName}`, {
            params: {}
        });
        
        const { steps } = response.data.result;
        vizContainer.innerHTML = '';
        
        // Animate steps one by one
        steps.forEach((step, index) => {
            setTimeout(() => {
                const stepHtml = `
                    <div class="workflow-step">
                        <div class="step-header">
                            <span class="step-title">Step ${index + 1}: ${step.step}</span>
                            <span class="step-status">${step.status}</span>
                        </div>
                        <div class="step-description">${step.description}</div>
                        <div class="step-data">${JSON.stringify(step.data, null, 2)}</div>
                    </div>
                `;
                vizContainer.innerHTML += stepHtml;
                addConsoleLog(`[Workflow] ${step.step}: ${step.description}`);
            }, index * 500);
        });
        
        queriesCounter += steps.length;
        updateQueriesCounter();
        
    } catch (error) {
        vizContainer.innerHTML = `<div class="workflow-placeholder">Error: ${error.message}</div>`;
        addConsoleLog(`[Error] Workflow failed: ${error.message}`);
    }
}

// Start data generation
async function startDataGeneration() {
    const metricType = document.getElementById('metric-type').value;
    addConsoleLog(`[Generator] Starting ${metricType} data generation...`);
    
    try {
        const response = await axios.post('/api/demo/generate-data', {
            type: metricType,
            duration: 30
        });
        
        addConsoleLog(`[Generator] ${response.data.message}`);
        
        // Update chart label
        chartData.datasets[0].label = metricType.charAt(0).toUpperCase() + metricType.slice(1) + ' Metrics';
        metricsChart.update();
        
    } catch (error) {
        addConsoleLog(`[Error] Failed to start generator: ${error.message}`);
    }
}

// Stop data generation
function stopDataGeneration() {
    const metricType = document.getElementById('metric-type').value;
    socket.emit('stop-generator', { type: metricType });
    addConsoleLog(`[Generator] Stopping ${metricType} data generation...`);
}

// Update chart with new data
function updateChart(data) {
    const time = new Date(data.timestamp).toLocaleTimeString();
    
    // Keep only last 20 data points
    if (chartData.labels.length > 20) {
        chartData.labels.shift();
        chartData.datasets[0].data.shift();
    }
    
    chartData.labels.push(time);
    chartData.datasets[0].data.push(data.value);
    metricsChart.update();
}

// Trigger test alert
async function triggerTestAlert(severity) {
    addConsoleLog(`[Alert] Triggering ${severity} alert...`);
    
    const alertHtml = `
        <div class="alert-item ${severity}">
            <div>
                <strong>${severity.toUpperCase()} Alert</strong>
                <div>Test alert triggered at ${new Date().toLocaleTimeString()}</div>
            </div>
            <button class="btn btn-sm" onclick="this.parentElement.remove()">Dismiss</button>
        </div>
    `;
    
    const alertsList = document.getElementById('alerts-list');
    if (alertsList.querySelector('.no-alerts')) {
        alertsList.innerHTML = '';
    }
    alertsList.innerHTML += alertHtml;
    
    alertsCounter++;
    document.getElementById('active-alerts').textContent = alertsCounter;
    
    // Simulate alert workflow
    await runWorkflow('alert-trigger');
}

// Resolve all alerts
function resolveAlerts() {
    document.getElementById('alerts-list').innerHTML = '<div class="no-alerts">No active alerts</div>';
    alertsCounter = 0;
    document.getElementById('active-alerts').textContent = '0';
    addConsoleLog('[Alert] All alerts resolved');
}

// Show feature demonstration
async function showFeatureDemo(feature) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    
    const demos = {
        collection: {
            title: 'Data Collection Demo',
            content: `
                <h3>Pull-Based Metrics Collection</h3>
                <p>The system uses a pull model to collect metrics from registered services.</p>
                <ol>
                    <li>Services expose metrics at /metrics endpoint</li>
                    <li>Collector discovers services via etcd</li>
                    <li>Metrics are pulled every 30 seconds</li>
                    <li>Data is sent to Kafka for processing</li>
                </ol>
                <button class="btn btn-primary" onclick="runWorkflow('metric-collection'); closeModal();">Run Collection Workflow</button>
            `
        },
        storage: {
            title: 'Data Storage Demo',
            content: `
                <h3>Time-Series Data Storage</h3>
                <p>InfluxDB provides optimized storage for time-series data.</p>
                <ul>
                    <li>Raw data retention: 30 days</li>
                    <li>Hourly aggregation: 1 year</li>
                    <li>Automatic downsampling</li>
                    <li>Compression for space optimization</li>
                </ul>
                <button class="btn btn-primary" onclick="runWorkflow('historical-query'); closeModal();">Query Historical Data</button>
            `
        },
        query: {
            title: 'Query Service Demo',
            content: `
                <h3>High-Performance Query Service</h3>
                <p>REST API with Redis caching for fast data retrieval.</p>
                <ul>
                    <li>RESTful API endpoints</li>
                    <li>Redis cache with 5-min TTL</li>
                    <li>Aggregation functions (avg, sum, count)</li>
                    <li>Time-range queries</li>
                </ul>
                <button class="btn btn-primary" onclick="runWorkflow('dashboard-query'); closeModal();">Run Query Demo</button>
            `
        },
        alerting: {
            title: 'Alerting System Demo',
            content: `
                <h3>Intelligent Alert Management</h3>
                <p>Rule-based alerting with multiple notification channels.</p>
                <ul>
                    <li>YAML-configured rules</li>
                    <li>Threshold-based triggers</li>
                    <li>Email and webhook notifications</li>
                    <li>Alert state management</li>
                </ul>
                <button class="btn btn-warning" onclick="triggerTestAlert('warning'); closeModal();">Trigger Alert</button>
            `
        },
        visualization: {
            title: 'Visualization Demo',
            content: `
                <h3>Real-Time Data Visualization</h3>
                <p>Interactive dashboards with live updates.</p>
                <ul>
                    <li>WebSocket for real-time updates</li>
                    <li>Multiple chart types</li>
                    <li>Mobile responsive design</li>
                    <li>30-second auto-refresh</li>
                </ul>
                <button class="btn btn-primary" onclick="openDashboard(); closeModal();">Open Dashboard</button>
            `
        },
        scalability: {
            title: 'Scalability Demo',
            content: `
                <h3>Horizontal Scaling Capabilities</h3>
                <p>Designed to handle massive scale with ease.</p>
                <ul>
                    <li>10M+ metrics per day</li>
                    <li>1000+ queries per second</li>
                    <li>Kafka partitioning for throughput</li>
                    <li>Service auto-scaling</li>
                </ul>
                <button class="btn btn-secondary" onclick="startDataGeneration(); closeModal();">Generate Load</button>
            `
        }
    };
    
    const demo = demos[feature];
    modalBody.innerHTML = `<h2>${demo.title}</h2>${demo.content}`;
    modal.style.display = 'block';
    
    addConsoleLog(`[Demo] Showing ${feature} demonstration`);
}

// Modal controls
function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('modal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}

// Open main dashboard
function openDashboard() {
    window.open('http://localhost:5317', '_blank');
    addConsoleLog('[Dashboard] Opening main dashboard in new tab');
}

// Console logging
function addConsoleLog(message) {
    const console = document.getElementById('console');
    const timestamp = new Date().toLocaleTimeString();
    const line = `<div class="console-line">[${timestamp}] ${message}</div>`;
    console.innerHTML += line;
    console.scrollTop = console.scrollHeight;
    
    // Keep only last 50 lines
    const lines = console.querySelectorAll('.console-line');
    if (lines.length > 50) {
        lines[0].remove();
    }
}

// Update metrics counters
function updateMetricsCounter() {
    document.getElementById('metrics-collected').textContent = metricsCounter;
}

function updateQueriesCounter() {
    document.getElementById('queries-per-second').textContent = (queriesCounter / 10).toFixed(1);
}

function startMetricsCounter() {
    setInterval(() => {
        // Simulate metrics collection
        metricsCounter += Math.floor(Math.random() * 10);
        updateMetricsCounter();
        
        // Simulate queries
        queriesCounter += Math.floor(Math.random() * 5);
        updateQueriesCounter();
        
        // Update cache hit rate
        const hitRate = 65 + Math.random() * 20;
        document.getElementById('cache-hit-rate').textContent = hitRate.toFixed(1) + '%';
    }, 5000);
}

// Auto-refresh service status
setInterval(fetchServiceStatus, 10000);