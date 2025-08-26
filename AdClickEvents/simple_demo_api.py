#!/usr/bin/env python3
"""
Simple AdClick Demo API - Working Demo System
This demonstrates the complete AdClick Event Aggregation system with realistic data.
"""

import json
import random
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

# Demo data and state
demo_state = {
    'simulation_active': False,
    'current_scenario': 'ecommerce',
    'simulation_speed': 1.0,
    'total_clicks': 0,
    'realtime_data': {},
    'events_generated': []
}

# Realistic demo scenarios
scenarios = {
    'ecommerce': {
        'name': 'E-commerce Holiday Sale',
        'ads': ['fashion_holiday_001', 'electronics_sale_002', 'home_decor_003', 'books_promo_004'],
        'countries': ['USA', 'Canada', 'UK', 'Germany', 'France'],
        'click_rate': 1000,  # clicks per minute
        'fraud_rate': 0.05,  # 5% fraud
        'cpc_range': (0.50, 2.50),
        'conversion_rate': (2.5, 8.0)
    },
    'gaming': {
        'name': 'Mobile Gaming Campaign',
        'ads': ['puzzle_game_001', 'strategy_game_002', 'arcade_game_003', 'rpg_game_004'],
        'countries': ['USA', 'Japan', 'South Korea', 'China', 'India'],
        'click_rate': 2000,
        'fraud_rate': 0.08,
        'cpc_range': (0.80, 3.00),
        'conversion_rate': (5.0, 15.0)
    },
    'finance': {
        'name': 'Financial Services',
        'ads': ['credit_card_001', 'personal_loan_002', 'insurance_003', 'investment_004'],
        'countries': ['USA', 'UK', 'Canada', 'Australia', 'Singapore'],
        'click_rate': 500,
        'fraud_rate': 0.02,
        'cpc_range': (2.00, 8.00),
        'conversion_rate': (1.0, 4.0)
    },
    'social': {
        'name': 'Social Media Platform',
        'ads': ['social_app_001', 'dating_app_002', 'fitness_app_003', 'food_app_004'],
        'countries': ['USA', 'Brazil', 'India', 'UK', 'Mexico'],
        'click_rate': 3000,
        'fraud_rate': 0.12,
        'cpc_range': (0.30, 1.50),
        'conversion_rate': (3.0, 12.0)
    }
}

def generate_realistic_metrics():
    """Generate realistic metrics for the current scenario"""
    scenario = scenarios[demo_state['current_scenario']]
    current_time = datetime.now()
    
    # Generate top ads with realistic performance
    top_ads = []
    for ad_id in scenario['ads']:
        clicks = random.randint(50, 500) if demo_state['simulation_active'] else random.randint(5, 50)
        top_ads.append({
            'ad_id': ad_id,
            'clicks': clicks,
            'name': ad_id.replace('_', ' ').title(),
            'ctr': round(random.uniform(*scenario['conversion_rate']), 2),
            'cpc': round(random.uniform(*scenario['cpc_range']), 2)
        })
    
    # Generate country distribution
    country_distribution = {}
    total_weight = sum([random.uniform(0.5, 2.0) for _ in scenario['countries']])
    
    for country in scenario['countries']:
        weight = random.uniform(0.5, 2.0)
        percentage = round((weight / total_weight) * 100, 1)
        clicks = int((percentage / 100) * demo_state['total_clicks']) if demo_state['total_clicks'] > 0 else random.randint(10, 100)
        
        country_distribution[country] = {
            'clicks': clicks,
            'percentage': percentage
        }
    
    return {
        'timestamp': int(current_time.timestamp()),
        'total_clicks': demo_state['total_clicks'],
        'clicks_per_second': random.randint(5, 50) if demo_state['simulation_active'] else 0,
        'top_ads': sorted(top_ads, key=lambda x: x['clicks'], reverse=True)[:5],
        'country_distribution': country_distribution,
        'fraud_rate': scenario['fraud_rate'] * 100,
        'revenue_per_hour': random.randint(1000, 5000),
        'active_campaigns': len(scenario['ads']),
        'system_health': {
            'cpu_usage': random.randint(20, 80),
            'memory_usage': random.randint(30, 70),
            'kafka_lag': random.randint(0, 100) if demo_state['simulation_active'] else 0,
            'api_latency': random.randint(50, 200)
        }
    }

def simulation_worker():
    """Background worker that simulates click events"""
    while demo_state['simulation_active']:
        scenario = scenarios[demo_state['current_scenario']]
        
        # Generate clicks based on scenario and speed
        clicks_this_second = int((scenario['click_rate'] / 60) * demo_state['simulation_speed'])
        demo_state['total_clicks'] += clicks_this_second
        
        # Generate individual events (sample for logs)
        for _ in range(min(clicks_this_second, 10)):  # Limit stored events
            event = {
                'ad_id': random.choice(scenario['ads']),
                'timestamp': datetime.now().isoformat(),
                'country': random.choice(scenario['countries']),
                'is_fraud': random.random() < scenario['fraud_rate'],
                'user_id': f"user_{random.randint(1000, 9999)}",
                'device': random.choice(['mobile', 'desktop', 'tablet'])
            }
            demo_state['events_generated'].append(event)
            
            # Keep only last 100 events
            if len(demo_state['events_generated']) > 100:
                demo_state['events_generated'] = demo_state['events_generated'][-100:]
        
        time.sleep(1)

# API Endpoints
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'demo-api',
        'scenario': demo_state['current_scenario'],
        'simulation_active': demo_state['simulation_active'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/scenarios')
def get_scenarios():
    return jsonify({
        'scenarios': scenarios,
        'current': demo_state['current_scenario']
    })

@app.route('/api/scenario', methods=['POST'])
def set_scenario():
    data = request.get_json()
    scenario = data.get('scenario')
    
    if scenario in scenarios:
        demo_state['current_scenario'] = scenario
        return jsonify({'success': True, 'scenario': scenario})
    
    return jsonify({'success': False, 'error': 'Invalid scenario'}), 400

@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    data = request.get_json() or {}
    speed = data.get('speed', 1.0)
    
    demo_state['simulation_speed'] = max(0.1, min(speed, 10.0))  # Limit speed
    demo_state['simulation_active'] = True
    
    # Start background worker
    if not any(t.name == 'simulation_worker' for t in threading.enumerate()):
        worker_thread = threading.Thread(target=simulation_worker, name='simulation_worker', daemon=True)
        worker_thread.start()
    
    return jsonify({
        'success': True, 
        'speed': demo_state['simulation_speed'],
        'scenario': demo_state['current_scenario']
    })

@app.route('/api/simulation/stop', methods=['POST'])
def stop_simulation():
    demo_state['simulation_active'] = False
    return jsonify({'success': True})

@app.route('/api/metrics/realtime')
def get_realtime_metrics():
    return jsonify(generate_realistic_metrics())

@app.route('/api/ads/performance')
def get_ads_performance():
    scenario = scenarios[demo_state['current_scenario']]
    
    performance_data = []
    for ad_id in scenario['ads']:
        performance_data.append({
            'ad_id': ad_id,
            'name': ad_id.replace('_', ' ').title(),
            'clicks': random.randint(100, 1000),
            'impressions': random.randint(1000, 10000),
            'ctr': round(random.uniform(*scenario['conversion_rate']), 2),
            'cost': round(random.uniform(50.0, 500.0), 2),
            'revenue': round(random.uniform(100.0, 1000.0), 2),
            'roi': round(random.uniform(1.2, 4.0), 2),
            'cpc': round(random.uniform(*scenario['cpc_range']), 2)
        })
    
    return jsonify({'ads': performance_data})

@app.route('/api/analytics/trends')
def get_trends():
    hours = []
    clicks = []
    revenue = []
    
    for i in range(24):
        hour = datetime.now() - timedelta(hours=i)
        hours.append(hour.strftime('%H:00'))
        clicks.append(random.randint(500, 2000))
        revenue.append(random.randint(1000, 5000))
    
    return jsonify({
        'hours': list(reversed(hours)),
        'clicks': list(reversed(clicks)),
        'revenue': list(reversed(revenue))
    })

@app.route('/api/fraud/alerts')
def get_fraud_alerts():
    alerts = []
    if demo_state['simulation_active']:
        scenario = scenarios[demo_state['current_scenario']]
        
        # Generate random fraud alerts
        for i in range(random.randint(0, 5)):
            alert_types = ['ip_anomaly', 'click_pattern', 'geographic', 'bot_detection']
            severities = ['low', 'medium', 'high']
            
            alerts.append({
                'id': f"alert_{int(time.time())}_{i}",
                'timestamp': int((datetime.now() - timedelta(minutes=random.randint(1, 60))).timestamp()),
                'type': random.choice(alert_types),
                'severity': random.choice(severities),
                'ad_id': random.choice(scenario['ads']),
                'description': f"Suspicious {random.choice(alert_types).replace('_', ' ')} detected",
                'status': random.choice(['new', 'investigating', 'resolved'])
            })
    
    return jsonify({'alerts': alerts})

@app.route('/api/campaigns/comparison')
def get_campaign_comparison():
    scenario = scenarios[demo_state['current_scenario']]
    
    campaigns = []
    for i, ad_id in enumerate(scenario['ads']):
        campaigns.append({
            'campaign_id': f"campaign_{i+1}",
            'name': ad_id.replace('_', ' ').title(),
            'ad_id': ad_id,
            'budget': random.randint(1000, 10000),
            'spent': random.randint(500, 8000),
            'clicks': random.randint(100, 2000),
            'conversions': random.randint(10, 200),
            'conversion_rate': round(random.uniform(*scenario['conversion_rate']), 2),
            'cpc': round(random.uniform(*scenario['cpc_range']), 2),
            'status': random.choice(['active', 'paused', 'completed'])
        })
    
    return jsonify({'campaigns': campaigns})

@app.route('/api/events/recent')
def get_recent_events():
    """Get recent events for debugging/monitoring"""
    return jsonify({
        'events': demo_state['events_generated'][-20:],  # Last 20 events
        'total_generated': len(demo_state['events_generated']),
        'simulation_active': demo_state['simulation_active']
    })

@app.route('/api/system/status')
def get_system_status():
    """System status overview"""
    return jsonify({
        'services': {
            'demo_api': {'status': 'healthy', 'uptime': '99.8%'},
            'event_simulator': {'status': 'healthy' if demo_state['simulation_active'] else 'stopped', 'events_per_second': random.randint(5, 50) if demo_state['simulation_active'] else 0},
            'aggregation_service': {'status': 'healthy', 'lag': random.randint(0, 100)},
            'database': {'status': 'healthy', 'storage_used': f"{random.randint(60, 85)}%"}
        },
        'performance': generate_realistic_metrics()['system_health'],
        'demo_state': {
            'scenario': demo_state['current_scenario'],
            'simulation_active': demo_state['simulation_active'],
            'total_clicks': demo_state['total_clicks'],
            'events_in_memory': len(demo_state['events_generated'])
        }
    })

@app.route('/')
def index():
    """Simple HTML dashboard for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AdClick Demo System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
            .metric { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }
            .metric-value { font-size: 24px; font-weight: bold; color: #333; }
            .metric-label { font-size: 12px; color: #666; margin-top: 5px; }
            button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin: 5px; }
            button:hover { background: #0056b3; }
            .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            .status.active { background: #d4edda; color: #155724; }
            .status.inactive { background: #f8d7da; color: #721c24; }
            select { padding: 8px; margin: 10px; border: 1px solid #ddd; border-radius: 4px; }
            .events { background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card header">
                <h1>🎯 AdClick Demo System</h1>
                <p>Complete Event Aggregation & Analytics Platform</p>
            </div>
            
            <div class="card">
                <h3>📊 Demo Controls</h3>
                <div>
                    <span id="sim-status" class="status inactive">Simulation Stopped</span>
                    <select id="scenario-select">
                        <option value="ecommerce">E-commerce Holiday Sale</option>
                        <option value="gaming">Mobile Gaming Campaign</option>
                        <option value="finance">Financial Services</option>
                        <option value="social">Social Media Platform</option>
                    </select>
                </div>
                <div>
                    <button onclick="startSimulation()">▶️ Start Simulation</button>
                    <button onclick="stopSimulation()">⏹️ Stop Simulation</button>
                    <button onclick="refreshData()">🔄 Refresh Data</button>
                </div>
            </div>

            <div class="card">
                <h3>📈 Real-time Metrics</h3>
                <div class="metrics" id="metrics">
                    <!-- Metrics will be loaded here -->
                </div>
            </div>

            <div class="card">
                <h3>🏆 Top Performing Ads</h3>
                <div id="top-ads">
                    <!-- Top ads will be loaded here -->
                </div>
            </div>

            <div class="card">
                <h3>🔍 Recent Events</h3>
                <div id="recent-events" class="events">
                    <!-- Recent events will be loaded here -->
                </div>
            </div>

            <div class="card">
                <h3>⚠️ Fraud Alerts</h3>
                <div id="fraud-alerts">
                    <!-- Fraud alerts will be loaded here -->
                </div>
            </div>
        </div>

        <script>
            let updateInterval;

            async function startSimulation() {
                try {
                    const response = await fetch('/api/simulation/start', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ speed: 1.0 })
                    });
                    const result = await response.json();
                    if (result.success) {
                        document.getElementById('sim-status').className = 'status active';
                        document.getElementById('sim-status').textContent = 'Simulation Active';
                        startAutoRefresh();
                    }
                } catch (e) {
                    console.error('Error starting simulation:', e);
                }
            }

            async function stopSimulation() {
                try {
                    const response = await fetch('/api/simulation/stop', { method: 'POST' });
                    const result = await response.json();
                    if (result.success) {
                        document.getElementById('sim-status').className = 'status inactive';
                        document.getElementById('sim-status').textContent = 'Simulation Stopped';
                        stopAutoRefresh();
                    }
                } catch (e) {
                    console.error('Error stopping simulation:', e);
                }
            }

            async function changeScenario() {
                const scenario = document.getElementById('scenario-select').value;
                try {
                    await fetch('/api/scenario', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ scenario })
                    });
                    refreshData();
                } catch (e) {
                    console.error('Error changing scenario:', e);
                }
            }

            async function refreshData() {
                try {
                    // Fetch metrics
                    const metricsResponse = await fetch('/api/metrics/realtime');
                    const metrics = await metricsResponse.json();
                    
                    document.getElementById('metrics').innerHTML = `
                        <div class="metric">
                            <div class="metric-value">${metrics.total_clicks.toLocaleString()}</div>
                            <div class="metric-label">Total Clicks</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">$${metrics.revenue_per_hour.toLocaleString()}</div>
                            <div class="metric-label">Revenue/Hour</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${metrics.fraud_rate.toFixed(1)}%</div>
                            <div class="metric-label">Fraud Rate</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${metrics.clicks_per_second}</div>
                            <div class="metric-label">Clicks/Second</div>
                        </div>
                    `;

                    // Top ads
                    const topAdsHtml = metrics.top_ads.map((ad, index) => 
                        `<div style="display: flex; justify-content: space-between; padding: 8px; border-bottom: 1px solid #eee;">
                            <span>#${index + 1} ${ad.name}</span>
                            <strong>${ad.clicks} clicks</strong>
                        </div>`
                    ).join('');
                    document.getElementById('top-ads').innerHTML = topAdsHtml;

                    // Recent events
                    const eventsResponse = await fetch('/api/events/recent');
                    const eventsData = await eventsResponse.json();
                    const eventsHtml = eventsData.events.slice(-10).map(event => 
                        `${event.timestamp.substring(11, 19)} | ${event.ad_id} | ${event.country} | ${event.device} ${event.is_fraud ? '⚠️' : ''}`
                    ).join('\\n');
                    document.getElementById('recent-events').textContent = eventsHtml;

                    // Fraud alerts
                    const fraudResponse = await fetch('/api/fraud/alerts');
                    const fraudData = await fraudResponse.json();
                    const alertsHtml = fraudData.alerts.map(alert => 
                        `<div style="padding: 8px; margin: 4px 0; background: #fff3cd; border-radius: 4px; border-left: 4px solid #ffc107;">
                            <strong>${alert.type.replace('_', ' ').toUpperCase()}</strong> - ${alert.severity}
                            <div style="font-size: 12px; color: #666;">${alert.description}</div>
                        </div>`
                    ).join('');
                    document.getElementById('fraud-alerts').innerHTML = alertsHtml || '<p style="color: #666;">No active fraud alerts</p>';

                } catch (e) {
                    console.error('Error refreshing data:', e);
                }
            }

            function startAutoRefresh() {
                stopAutoRefresh();
                updateInterval = setInterval(refreshData, 2000);
            }

            function stopAutoRefresh() {
                if (updateInterval) {
                    clearInterval(updateInterval);
                }
            }

            // Setup event listeners
            document.getElementById('scenario-select').addEventListener('change', changeScenario);

            // Initial load
            refreshData();
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("🚀 Starting AdClick Demo System...")
    print("📊 Demo Dashboard: http://localhost:8900")
    print("🔧 Health Check: http://localhost:8900/health")
    print("📋 API Docs: All endpoints available at /api/*")
    print("\n🎯 Ready for customer demonstrations!")
    
    app.run(host='0.0.0.0', port=8900, debug=True)