#!/usr/bin/env python3
"""
Microservices Crawler Dashboard
Real-time visualization of the complete microservices workflow
"""
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import requests
import json
import time
from datetime import datetime
import threading

app = Flask(__name__)
CORS(app)

# Service URLs matching docker-compose ports
SERVICES = {
    'gateway': 'http://localhost:5010',
    'frontier': 'http://localhost:5001',
    'downloader': 'http://localhost:5002',
    'parser': 'http://localhost:5003',
    'deduplication': 'http://localhost:5004',
    'extractor': 'http://localhost:5005',
    'storage': 'http://localhost:5006'
}

# Global state for real-time updates
crawl_state = {
    'is_running': False,
    'crawl_id': None,
    'activity_log': [],
    'stats': {
        'pages_processed': 0,
        'pages_queued': 0,
        'duplicates_found': 0,
        'errors': 0,
        'urls_extracted': 0
    },
    'module_status': {
        'frontier': {'status': 'idle', 'data': {}},
        'downloader': {'status': 'idle', 'data': {}},
        'parser': {'status': 'idle', 'data': {}},
        'deduplication': {'status': 'idle', 'data': {}},
        'extractor': {'status': 'idle', 'data': {}},
        'storage': {'status': 'idle', 'data': {}},
        'gateway': {'status': 'idle', 'data': {}}
    }
}

# HTML Template (similar to monolith UI)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microservices Crawler Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: white; border-radius: 15px; padding: 30px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; }
        .header h1 { color: #333; margin-bottom: 10px; }
        .header p { color: #666; }
        
        .control-panel { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .btn { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; transition: all 0.3s; }
        .btn-start { background: #48bb78; color: white; }
        .btn-start:hover { background: #38a169; }
        .btn-stop { background: #f56565; color: white; }
        .btn-stop:hover { background: #e53e3e; }
        .btn-clear { background: #ed8936; color: white; }
        .input-url { flex: 1; padding: 10px; border: 2px solid #e2e8f0; border-radius: 8px; min-width: 300px; }
        
        .modules-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .module-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); position: relative; overflow: hidden; transition: all 0.3s; }
        .module-card.active { border: 2px solid #48bb78; background: #f0fff4; animation: pulse 1s infinite; }
        .module-card.processing { border: 2px solid #4299e1; background: #ebf8ff; }
        .module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .module-title { font-weight: bold; color: #2d3748; }
        .module-status { padding: 3px 8px; border-radius: 4px; font-size: 12px; text-transform: uppercase; }
        .status-active { background: #48bb78; color: white; }
        .status-idle { background: #cbd5e0; color: #2d3748; }
        .status-processing { background: #4299e1; color: white; }
        .module-stats { font-size: 14px; color: #4a5568; }
        .module-stat { margin: 5px 0; display: flex; justify-content: space-between; }
        .stat-value { font-weight: bold; color: #2d3748; }
        
        .stats-panel { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; }
        .stat-card { text-align: center; padding: 15px; background: #f7fafc; border-radius: 8px; }
        .stat-number { font-size: 32px; font-weight: bold; color: #4299e1; }
        .stat-label { color: #718096; margin-top: 5px; }
        
        .activity-log { background: #1a202c; color: #68d391; padding: 20px; border-radius: 15px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 13px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .log-entry { margin-bottom: 5px; }
        .log-timestamp { color: #9f7aea; }
        .log-module { color: #63b3ed; font-weight: bold; }
        .log-success { color: #68d391; }
        .log-error { color: #fc8181; }
        
        .flow-diagram { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .flow-container { display: flex; justify-content: space-between; align-items: center; padding: 20px; }
        .flow-step { flex: 1; text-align: center; position: relative; }
        .flow-step::after { content: '→'; position: absolute; right: -20px; top: 50%; transform: translateY(-50%); font-size: 24px; color: #4299e1; }
        .flow-step:last-child::after { display: none; }
        .flow-icon { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px; font-size: 24px; transition: all 0.3s; }
        .flow-active { background: #48bb78; color: white; animation: bounce 1s infinite; }
        .flow-idle { background: #e2e8f0; color: #a0aec0; }
        .flow-label { font-weight: bold; color: #2d3748; }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; } }
        @keyframes bounce { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕸️ Microservices Crawler Dashboard</h1>
            <p>Real-time visualization of distributed crawler architecture</p>
        </div>

        <div class="control-panel">
            <div class="controls">
                <input type="url" id="seedUrl" class="input-url" value="https://httpbin.org/html" placeholder="Enter URL to crawl">
                <button class="btn btn-start" onclick="startCrawl()">▶️ Start Crawl</button>
                <button class="btn btn-stop" onclick="stopCrawl()">⏹️ Stop Crawl</button>
                <button class="btn btn-clear" onclick="clearLog()">🗑️ Clear Log</button>
                <span id="crawlStatus" style="margin-left: 20px; font-weight: bold;"></span>
            </div>
        </div>

        <div class="flow-diagram">
            <h3 style="margin-bottom: 10px;">📊 Data Flow Visualization</h3>
            <div class="flow-container">
                <div class="flow-step">
                    <div class="flow-icon flow-idle" id="flow-frontier">📋</div>
                    <div class="flow-label">URL Frontier</div>
                </div>
                <div class="flow-step">
                    <div class="flow-icon flow-idle" id="flow-downloader">⬇️</div>
                    <div class="flow-label">Downloader</div>
                </div>
                <div class="flow-step">
                    <div class="flow-icon flow-idle" id="flow-parser">📄</div>
                    <div class="flow-label">Parser</div>
                </div>
                <div class="flow-step">
                    <div class="flow-icon flow-idle" id="flow-dedup">🔍</div>
                    <div class="flow-label">Deduplication</div>
                </div>
                <div class="flow-step">
                    <div class="flow-icon flow-idle" id="flow-extractor">🔗</div>
                    <div class="flow-label">URL Extractor</div>
                </div>
                <div class="flow-step">
                    <div class="flow-icon flow-idle" id="flow-storage">💾</div>
                    <div class="flow-label">Storage</div>
                </div>
            </div>
        </div>

        <div class="modules-grid">
            <div class="module-card" id="module-frontier">
                <div class="module-header">
                    <span class="module-title">📋 URL Frontier</span>
                    <span class="module-status status-idle" id="status-frontier">IDLE</span>
                </div>
                <div class="module-stats">
                    <div class="module-stat">Queue Size: <span class="stat-value" id="frontier-queue">0</span></div>
                    <div class="module-stat">Enqueued: <span class="stat-value" id="frontier-enqueued">0</span></div>
                    <div class="module-stat">Dequeued: <span class="stat-value" id="frontier-dequeued">0</span></div>
                </div>
            </div>

            <div class="module-card" id="module-downloader">
                <div class="module-header">
                    <span class="module-title">⬇️ HTML Downloader</span>
                    <span class="module-status status-idle" id="status-downloader">IDLE</span>
                </div>
                <div class="module-stats">
                    <div class="module-stat">Downloads: <span class="stat-value" id="downloader-total">0</span></div>
                    <div class="module-stat">Success: <span class="stat-value" id="downloader-success">0</span></div>
                    <div class="module-stat">Bytes: <span class="stat-value" id="downloader-bytes">0</span></div>
                </div>
            </div>

            <div class="module-card" id="module-parser">
                <div class="module-header">
                    <span class="module-title">📄 Content Parser</span>
                    <span class="module-status status-idle" id="status-parser">IDLE</span>
                </div>
                <div class="module-stats">
                    <div class="module-stat">Parsed: <span class="stat-value" id="parser-total">0</span></div>
                    <div class="module-stat">Success: <span class="stat-value" id="parser-success">0</span></div>
                    <div class="module-stat">Links Found: <span class="stat-value" id="parser-links">0</span></div>
                </div>
            </div>

            <div class="module-card" id="module-deduplication">
                <div class="module-header">
                    <span class="module-title">🔍 Deduplication</span>
                    <span class="module-status status-idle" id="status-deduplication">IDLE</span>
                </div>
                <div class="module-stats">
                    <div class="module-stat">Checks: <span class="stat-value" id="dedup-checks">0</span></div>
                    <div class="module-stat">Unique: <span class="stat-value" id="dedup-unique">0</span></div>
                    <div class="module-stat">Duplicates: <span class="stat-value" id="dedup-duplicates">0</span></div>
                </div>
            </div>

            <div class="module-card" id="module-extractor">
                <div class="module-header">
                    <span class="module-title">🔗 URL Extractor</span>
                    <span class="module-status status-idle" id="status-extractor">IDLE</span>
                </div>
                <div class="module-stats">
                    <div class="module-stat">Processed: <span class="stat-value" id="extractor-processed">0</span></div>
                    <div class="module-stat">URLs Found: <span class="stat-value" id="extractor-urls">0</span></div>
                    <div class="module-stat">Filtered: <span class="stat-value" id="extractor-filtered">0</span></div>
                </div>
            </div>

            <div class="module-card" id="module-storage">
                <div class="module-header">
                    <span class="module-title">💾 Content Storage</span>
                    <span class="module-status status-idle" id="status-storage">IDLE</span>
                </div>
                <div class="module-stats">
                    <div class="module-stat">Documents: <span class="stat-value" id="storage-documents">0</span></div>
                    <div class="module-stat">Stored: <span class="stat-value" id="storage-bytes">0</span></div>
                    <div class="module-stat">Duplicates: <span class="stat-value" id="storage-duplicates">0</span></div>
                </div>
            </div>

            <div class="module-card" id="module-gateway">
                <div class="module-header">
                    <span class="module-title">🌐 API Gateway</span>
                    <span class="module-status status-idle" id="status-gateway">IDLE</span>
                </div>
                <div class="module-stats">
                    <div class="module-stat">Orchestrated: <span class="stat-value" id="gateway-orchestrated">0</span></div>
                    <div class="module-stat">Active: <span class="stat-value" id="gateway-active">No</span></div>
                </div>
            </div>
        </div>

        <div class="stats-panel">
            <h3 style="margin-bottom: 15px;">📈 Overall Statistics</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-crawls-started">0</div>
                    <div class="stat-label">Total Crawls Started</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-crawls-completed">0</div>
                    <div class="stat-label">Total Crawls Completed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-pages-processed">0</div>
                    <div class="stat-label">Total Pages Processed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-urls-extracted">0</div>
                    <div class="stat-label">Total URLs Extracted</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-duplicates-found">0</div>
                    <div class="stat-label">Total Duplicates Found</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-errors">0</div>
                    <div class="stat-label">Total Errors</div>
                </div>
            </div>
        </div>

        <div class="activity-log" id="activityLog">
            <div class="log-entry">
                <span class="log-timestamp">[00:00:00]</span> 
                <span class="log-module">SYSTEM</span> 
                <span class="log-success">Microservices Dashboard Ready</span>
            </div>
        </div>
    </div>

    <script>
        // Removed updateInterval - now using single global 10-second interval
        let crawlActive = false;

        function log(module, message, isError = false) {
            const logDiv = document.getElementById('activityLog');
            const timestamp = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> <span class="log-module">${module}</span> <span class="${isError ? 'log-error' : 'log-success'}">${message}</span>`;
            logDiv.appendChild(entry);
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function clearLog() {
            const logDiv = document.getElementById('activityLog');
            logDiv.innerHTML = '<div class="log-entry"><span class="log-timestamp">[00:00:00]</span> <span class="log-module">SYSTEM</span> <span class="log-success">Log cleared</span></div>';
        }

        async function startCrawl() {
            const seedUrl = document.getElementById('seedUrl').value;
            if (!seedUrl) {
                alert('Please enter a URL to crawl');
                return;
            }

            log('GATEWAY', `Starting crawl with seed URL: ${seedUrl}`);
            document.getElementById('crawlStatus').textContent = '🔄 Starting...';
            
            // Visual feedback - activate gateway
            activateModule('gateway');
            
            try {
                const response = await fetch('http://localhost:5010/crawl/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({seed_urls: [seedUrl]})
                });

                const data = await response.json();
                
                if (data.success) {
                    crawlActive = true;
                    document.getElementById('crawlStatus').textContent = '✅ Crawling...';
                    log('GATEWAY', `Crawl started: ${data.crawl_id}`);
                    
                    // Start real-time updates
                    startRealTimeUpdates();
                } else {
                    document.getElementById('crawlStatus').textContent = '❌ Failed to start';
                    log('GATEWAY', data.error || 'Failed to start crawl', true);
                    deactivateAllModules();
                }
            } catch (error) {
                document.getElementById('crawlStatus').textContent = '❌ Error';
                log('GATEWAY', `Error: ${error.message}`, true);
                deactivateAllModules();
            }
        }

        async function stopCrawl() {
            log('GATEWAY', 'Stopping crawl...');
            document.getElementById('crawlStatus').textContent = '⏹️ Stopping...';
            
            try {
                const response = await fetch('http://localhost:5010/crawl/stop', {
                    method: 'POST'
                });

                const data = await response.json();
                
                if (data.success) {
                    crawlActive = false;
                    document.getElementById('crawlStatus').textContent = '⏹️ Stopped';
                    log('GATEWAY', 'Crawl stopped');
                    stopRealTimeUpdates();
                    deactivateAllModules();
                }
            } catch (error) {
                log('GATEWAY', `Error stopping: ${error.message}`, true);
            }
        }

        function activateModule(module) {
            // Update module card
            const card = document.getElementById(`module-${module}`);
            if (card) {
                card.classList.add('active');
                card.classList.remove('processing');
            }
            
            // Update status badge
            const status = document.getElementById(`status-${module}`);
            if (status) {
                status.textContent = 'ACTIVE';
                status.className = 'module-status status-active';
            }
            
            // Update flow diagram
            const flowIcon = document.getElementById(`flow-${module}`);
            if (flowIcon) {
                flowIcon.classList.add('flow-active');
                flowIcon.classList.remove('flow-idle');
            }
        }

        function processingModule(module) {
            const card = document.getElementById(`module-${module}`);
            if (card) {
                card.classList.add('processing');
                card.classList.remove('active');
            }
            
            const status = document.getElementById(`status-${module}`);
            if (status) {
                status.textContent = 'PROCESSING';
                status.className = 'module-status status-processing';
            }
        }

        function deactivateModule(module) {
            const card = document.getElementById(`module-${module}`);
            if (card) {
                card.classList.remove('active', 'processing');
            }
            
            const status = document.getElementById(`status-${module}`);
            if (status) {
                status.textContent = 'IDLE';
                status.className = 'module-status status-idle';
            }
            
            const flowIcon = document.getElementById(`flow-${module}`);
            if (flowIcon) {
                flowIcon.classList.remove('flow-active');
                flowIcon.classList.add('flow-idle');
            }
        }

        function deactivateAllModules() {
            ['frontier', 'downloader', 'parser', 'deduplication', 'extractor', 'storage', 'gateway'].forEach(deactivateModule);
        }

        async function updateStats() {
            // Get crawl status
            console.log('Updating stats...');
            try {
                const statusResponse = await fetch('http://localhost:5010/crawl/status');
                const status = await statusResponse.json();
                console.log('Status response:', status);
                
                // Will update overall stats with service stats below (total-queued updated later with aggregated data)
                
                // Only simulate flow animation if actually running
                // Don't simulate for completed or stopped status
                if (status.status === 'running' && status.pages_processed > 0) {
                    // Simulate the flow
                    simulateFlow();
                } else {
                    // Stop any ongoing flow simulation
                    if (window.flowInterval) {
                        clearInterval(window.flowInterval);
                        window.flowInterval = null;
                    }
                }
                
                // Update gateway status and crawl status display
                if (status.status === 'running') {
                    document.getElementById('gateway-active').textContent = 'Yes';
                    document.getElementById('crawlStatus').textContent = '✅ Crawling...';
                    activateModule('gateway');
                    crawlActive = true;
                } else if (status.status === 'stopped') {
                    document.getElementById('gateway-active').textContent = 'No';
                    document.getElementById('crawlStatus').textContent = '⏹️ Stopped';
                    // Stop all animations and deactivate modules
                    crawlActive = false;
                    stopFlow();
                    stopRealTimeUpdates();
                } else if (status.status === 'completed') {
                    document.getElementById('gateway-active').textContent = 'No';
                    document.getElementById('crawlStatus').textContent = '✅ Completed';
                    // Stop all animations and deactivate modules
                    crawlActive = false;
                    stopFlow();
                    stopRealTimeUpdates();
                } else {
                    // Idle state - only show as active if there are CURRENT queued pages
                    const hasCurrentActivity = (status.pages_queued || 0) > 0;
                    
                    if (hasCurrentActivity) {
                        document.getElementById('gateway-active').textContent = 'Yes';
                        document.getElementById('crawlStatus').textContent = '⏸️ Paused (URLs in queue)';
                        activateModule('gateway');
                    } else {
                        document.getElementById('gateway-active').textContent = 'No';
                        document.getElementById('crawlStatus').textContent = '💤 Idle';
                    }
                    crawlActive = false;
                    stopFlow();
                    stopRealTimeUpdates();
                }
                
                // Update the persistent stats display here while we have the status data
                console.log('Updating UI stats with:', {
                    crawls_started: status.total_crawls_started,
                    crawls_completed: status.total_crawls_completed,
                    pages_processed: status.total_pages_processed,
                    urls_extracted: status.total_urls_extracted,
                    duplicates_found: status.total_duplicates_found,
                    errors: status.total_errors
                });
                
                document.getElementById('total-crawls-started').textContent = status.total_crawls_started || 0;
                document.getElementById('total-crawls-completed').textContent = status.total_crawls_completed || 0;
                document.getElementById('total-pages-processed').textContent = status.total_pages_processed || 0;
                document.getElementById('total-urls-extracted').textContent = status.total_urls_extracted || 0;
                document.getElementById('total-duplicates-found').textContent = status.total_duplicates_found || 0;
                document.getElementById('total-errors').textContent = status.total_errors || 0;
                
                // Add tooltips showing current crawl vs total breakdown
                document.getElementById('total-pages-processed').title = 
                    `Total: ${status.total_pages_processed || 0} (Current crawl: ${status.pages_processed || 0})`;
                document.getElementById('total-duplicates-found').title = 
                    `Total: ${status.total_duplicates_found || 0} (Current crawl: ${status.duplicates_found || 0})`;
                document.getElementById('total-errors').title = 
                    `Total: ${status.total_errors || 0} (Current crawl: ${status.errors_count || 0})`;
                    
            } catch (error) {
                console.error('Error updating stats:', error);
                // Set fallback values on error
                document.getElementById('total-crawls-started').textContent = 'Error';
                document.getElementById('total-crawls-completed').textContent = 'Error';
                document.getElementById('total-pages-processed').textContent = 'Error';
            }

            // Get individual service stats
            try {
                const statsResponse = await fetch('http://localhost:5010/stats');
                const allStats = await statsResponse.json();
                
                // Update frontier stats and status
                if (allStats.frontier && !allStats.frontier.error) {
                    document.getElementById('frontier-queue').textContent = allStats.frontier.total_in_queue || 0;
                    document.getElementById('frontier-enqueued').textContent = allStats.frontier.urls_enqueued || 0;
                    document.getElementById('frontier-dequeued').textContent = allStats.frontier.urls_dequeued || 0;
                    
                    // Only show as active during actual crawling
                    if (crawlActive && (allStats.frontier.total_in_queue || 0) > 0) {
                        activateModule('frontier');
                    } else if (!crawlActive) {
                        deactivateModule('frontier');
                    }
                }
                
                // Update downloader stats and status
                if (allStats.downloader && !allStats.downloader.error) {
                    document.getElementById('downloader-total').textContent = allStats.downloader.total_downloads || 0;
                    document.getElementById('downloader-success').textContent = allStats.downloader.successful_downloads || 0;
                    document.getElementById('downloader-bytes').textContent = formatBytes(allStats.downloader.total_bytes || 0);
                    
                    // Show as active if there have been recent downloads
                    if ((allStats.downloader.total_downloads || 0) > 0 || (allStats.downloader.cache_hits || 0) > 0) {
                        activateModule('downloader');
                    } else {
                        deactivateModule('downloader');
                    }
                }
                
                // Update parser stats and status
                if (allStats.parser && !allStats.parser.error) {
                    document.getElementById('parser-total').textContent = allStats.parser.total_parsed || 0;
                    document.getElementById('parser-success').textContent = allStats.parser.successful_parses || 0;
                    document.getElementById('parser-links').textContent = allStats.parser.total_links_extracted || 0;
                    
                    // Show as active if there have been recent parses
                    if ((allStats.parser.total_parsed || 0) > 0) {
                        activateModule('parser');
                    } else {
                        deactivateModule('parser');
                    }
                }
                
                // Update deduplication stats and status
                if (allStats.deduplication && !allStats.deduplication.error) {
                    document.getElementById('dedup-checks').textContent = allStats.deduplication.total_checks || 0;
                    document.getElementById('dedup-unique').textContent = allStats.deduplication.unique_content || 0;
                    document.getElementById('dedup-duplicates').textContent = allStats.deduplication.duplicates_found || 0;
                    
                    // Show as active if there have been recent checks
                    if ((allStats.deduplication.total_checks || 0) > 0) {
                        activateModule('deduplication');
                    } else {
                        deactivateModule('deduplication');
                    }
                }
                
                // Update extractor stats and status
                if (allStats.extractor && !allStats.extractor.error) {
                    const extractorStats = allStats.extractor.stats || allStats.extractor;
                    document.getElementById('extractor-processed').textContent = extractorStats.pages_processed || 0;
                    document.getElementById('extractor-urls').textContent = extractorStats.urls_extracted || 0;
                    document.getElementById('extractor-filtered').textContent = 
                        (extractorStats.duplicate_urls_filtered || 0) + (extractorStats.invalid_urls_filtered || 0);
                    
                    // Show as active if URLs have been extracted
                    if ((extractorStats.urls_extracted || 0) > 0) {
                        activateModule('extractor');
                    } else {
                        deactivateModule('extractor');
                    }
                }
                
                // Update storage stats and status
                if (allStats.storage && !allStats.storage.error) {
                    const storageStats = allStats.storage.stats || allStats.storage;
                    document.getElementById('storage-documents').textContent = storageStats.documents_stored || 0;
                    document.getElementById('storage-bytes').textContent = formatBytes(storageStats.total_bytes_stored || 0);
                    document.getElementById('storage-duplicates').textContent = storageStats.duplicate_documents || 0;
                    
                    // Show as active if documents have been stored
                    if ((storageStats.documents_stored || 0) > 0) {
                        activateModule('storage');
                    } else {
                        deactivateModule('storage');
                    }
                }
                
                // Update gateway orchestrated count
                document.getElementById('gateway-orchestrated').textContent = 
                    (allStats.downloader?.total_downloads || 0) + (allStats.parser?.total_parsed || 0);
                
                // Stats are now updated in the first try block where status data is available
                
            } catch (error) {
                console.error('Error fetching service stats:', error);
            }
            
            console.log('Stats update completed');
        }

        let flowTimeouts = [];
        
        function simulateFlow() {
            // Clear any existing flow timeouts first
            flowTimeouts.forEach(timeout => clearTimeout(timeout));
            flowTimeouts = [];
            
            // Only simulate if actually crawling
            if (!crawlActive) return;
            
            // Simulate data flow through services
            const sequence = ['frontier', 'downloader', 'parser', 'deduplication', 'extractor', 'storage'];
            let currentIndex = 0;
            
            function activateNext() {
                // Stop if crawl is no longer active
                if (!crawlActive) {
                    deactivateAllModules();
                    return;
                }
                
                if (currentIndex < sequence.length) {
                    const current = sequence[currentIndex];
                    
                    // Log the activity
                    const messages = {
                        'frontier': 'Dequeuing URL from frontier',
                        'downloader': 'Downloading HTML content',
                        'parser': 'Parsing HTML and extracting links',
                        'deduplication': 'Checking for duplicate content',
                        'extractor': 'Extracting URLs from content',
                        'storage': 'Storing processed content'
                    };
                    
                    log(current.toUpperCase(), messages[current]);
                    
                    // Visual activation
                    if (currentIndex > 0) {
                        deactivateModule(sequence[currentIndex - 1]);
                    }
                    processingModule(current);
                    
                    currentIndex++;
                    
                    if (currentIndex < sequence.length) {
                        const timeout = setTimeout(activateNext, 500);
                        flowTimeouts.push(timeout);
                    } else {
                        const timeout = setTimeout(() => {
                            if (crawlActive) {
                                deactivateModule(sequence[sequence.length - 1]);
                                log('GATEWAY', 'URL processing complete');
                            } else {
                                deactivateAllModules();
                            }
                        }, 500);
                        flowTimeouts.push(timeout);
                    }
                }
            }
            
            activateNext();
        }
        
        function stopFlow() {
            // Clear all flow timeouts
            flowTimeouts.forEach(timeout => clearTimeout(timeout));
            flowTimeouts = [];
            deactivateAllModules();
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }

        // Global stats update interval - single source of truth
        let statsUpdateInterval = null;
        let lastUpdateTime = 0;
        
        function startRealTimeUpdates() {
            // During crawling, we still use 10-second updates
            // Just ensure we're updating
            console.log('Crawl started - continuing 10-second update interval');
        }

        function stopRealTimeUpdates() {
            // We no longer stop the interval, just log the state change
            console.log('Crawl stopped - continuing 10-second update interval');
        }
        
        // Wrapper to prevent too frequent updates
        async function updateStatsThrottled() {
            const now = Date.now();
            // Prevent updates more frequent than every 2 seconds
            if (now - lastUpdateTime < 2000) {
                console.log('Skipping stats update - too frequent');
                return;
            }
            lastUpdateTime = now;
            await updateStats();
        }

        // Initial stats update
        updateStats();
        
        // Single consistent interval for all stats updates - every 10 seconds
        // This prevents excessive API calls and provides consistent behavior
        statsUpdateInterval = setInterval(updateStats, 10000);
        console.log('Stats update interval started - updating every 10 seconds');
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the dashboard"""
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    print("🚀 Starting Microservices Crawler Dashboard...")
    print("📊 Dashboard available at: http://localhost:8090")
    print("🔧 This dashboard shows real-time visualization of all microservices working together")
    print("✨ Just like the monolith UI, but for microservices!")
    app.run(host='0.0.0.0', port=8090, debug=False)