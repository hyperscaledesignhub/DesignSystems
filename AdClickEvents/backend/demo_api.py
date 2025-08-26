#!/usr/bin/env python3
"""
Simple AdClick Demo API - Working Demo System
This demonstrates the complete AdClick Event Aggregation system with realistic data.
"""

import json
import random
import time
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

app = Flask(__name__)
CORS(app)

# InfluxDB Configuration
INFLUX_URL = f"http://{os.getenv('INFLUXDB_HOST', 'localhost')}:{os.getenv('INFLUXDB_PORT', '8086')}"
INFLUX_TOKEN = os.getenv('INFLUXDB_TOKEN', 'demo-token')
INFLUX_ORG = os.getenv('INFLUXDB_ORG', 'demo-org') 
INFLUX_BUCKET = os.getenv('INFLUXDB_BUCKET', 'adclick-demo')

# Initialize InfluxDB client
influx_client = None
write_api = None
query_api = None

def init_influxdb():
    global influx_client, write_api, query_api
    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        query_api = influx_client.query_api()
        print(f"✅ Connected to InfluxDB at {INFLUX_URL}")
        
        # Clear old data on startup for clean demo
        try:
            delete_api = influx_client.delete_api()
            delete_api.delete(
                start="1970-01-01T00:00:00Z",
                stop="2030-01-01T00:00:00Z", 
                predicate='_measurement="adclick_events"',
                bucket=INFLUX_BUCKET,
                org=INFLUX_ORG
            )
            print("🧹 Cleared old InfluxDB data for clean demo")
        except Exception as e:
            print(f"⚠️ Could not clear old data: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to connect to InfluxDB: {e}")
        return False

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

def write_event_to_influx(event):
    """Write a single event to InfluxDB"""
    if not write_api:
        return False
    
    try:
        point = Point("adclick_events") \
            .tag("ad_id", event['ad_id']) \
            .tag("country", event['country']) \
            .tag("device", event['device']) \
            .tag("user_id", event['user_id']) \
            .field("is_fraud", event['is_fraud']) \
            .field("click_value", event.get('click_value', random.uniform(0.5, 3.0))) \
            .time(datetime.now(), WritePrecision.NS)
        
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        return True
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")
        return False

def simulation_worker():
    """Background worker that simulates click events"""
    while demo_state['simulation_active']:
        scenario = scenarios[demo_state['current_scenario']]
        
        # Generate clicks based on scenario and speed (reduced rate for demo)
        clicks_this_second = max(1, int((scenario['click_rate'] / 60) * demo_state['simulation_speed'] * 0.1))  # 10% of original rate
        demo_state['total_clicks'] += clicks_this_second
        
        # Generate individual events
        for _ in range(clicks_this_second):
            event = {
                'ad_id': random.choice(scenario['ads']),
                'timestamp': datetime.now().isoformat(),
                'country': random.choice(scenario['countries']),
                'is_fraud': random.random() < scenario['fraud_rate'],
                'user_id': f"user_{random.randint(1000, 9999)}",
                'device': random.choice(['mobile', 'desktop', 'tablet']),
                'click_value': random.uniform(*scenario['cpc_range'])
            }
            
            # Store in memory for recent events display
            demo_state['events_generated'].append(event)
            
            # Write to InfluxDB
            write_event_to_influx(event)
            
            # Keep only last 50 events in memory
            if len(demo_state['events_generated']) > 50:
                demo_state['events_generated'] = demo_state['events_generated'][-50:]
        
        time.sleep(1)

# API Endpoints
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'demo-api',
        'scenario': demo_state['current_scenario'],
        'simulation_active': demo_state['simulation_active'],
        'influxdb_connected': influx_client is not None,
        'database_url': INFLUX_URL,
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
        print(f"🎯 Scenario switch requested: {demo_state['current_scenario']} -> {scenario}", flush=True)
        
        # Stop current simulation when switching scenarios
        demo_state['simulation_active'] = False
        demo_state['current_scenario'] = scenario
        demo_state['total_clicks'] = 0
        demo_state['events_generated'] = []
        
        # Clear InfluxDB data when switching scenarios for clean demo
        print(f"🧹 Attempting to clear InfluxDB data for scenario switch to {scenario}", flush=True)
        
        # Use direct HTTP API call to InfluxDB instead of subprocess
        try:
            import requests
            
            # Use InfluxDB v2 delete API
            delete_url = f"http://{INFLUX_HOST}:{INFLUX_PORT}/api/v2/delete"
            headers = {
                'Authorization': f'Token {INFLUX_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            # Delete all adclick_events data  
            delete_data = {
                "start": "1970-01-01T00:00:00Z",
                "stop": "2030-01-01T00:00:00Z", 
                "predicate": "_measurement=\"adclick_events\""
            }
            
            params = {
                'org': INFLUX_ORG,
                'bucket': INFLUX_BUCKET
            }
            
            response = requests.post(delete_url, json=delete_data, headers=headers, params=params, timeout=10)
            
            print(f"🔍 HTTP delete result: status={response.status_code}, text='{response.text}'", flush=True)
            
            if response.status_code in [200, 204]:
                print(f"✅ Successfully cleared InfluxDB data via HTTP API for scenario switch to {scenario}", flush=True)
            else:
                print(f"⚠️ InfluxDB HTTP clear failed: {response.status_code} - {response.text}", flush=True)
                
        except Exception as e:
            print(f"⚠️ Could not clear data via HTTP API on scenario switch: {e}", flush=True)
        
        # Always reset state regardless of clearing success
        demo_state['simulation_active'] = False
        demo_state['total_clicks'] = 0
        demo_state['events_generated'] = []
        
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
    print("=== REALTIME METRICS CALLED ===")
    print(f"Simulation active: {demo_state['simulation_active']}")
    print(f"Current scenario: {demo_state['current_scenario']}")
    
    if not query_api:
        print("No query_api - using mock data")
        return jsonify(generate_realistic_metrics())  # Fallback to mock if no DB
    
    # If simulation is not active, return minimal data
    if not demo_state['simulation_active']:
        print(f"DEBUG: Simulation inactive, returning zero data for scenario {demo_state['current_scenario']}")
        scenario = scenarios[demo_state['current_scenario']]
        return jsonify({
            'timestamp': int(datetime.now().timestamp()),
            'total_clicks': 0,
            'clicks_per_second': 0,
            'top_ads': [],
            'country_distribution': {country: {'clicks': 0, 'percentage': 0.0} for country in scenario['countries']},
            'fraud_rate': 0.0,
            'revenue_per_hour': 0,
            'active_campaigns': len(scenario['ads']),
            'system_health': {
                'cpu_usage': random.randint(20, 40),
                'memory_usage': random.randint(30, 50),
                'kafka_lag': 0,
                'api_latency': random.randint(50, 100)
            }
        })
    
    try:
        # Query real data from InfluxDB
        current_time = datetime.now()
        
        # Get current scenario info
        scenario = scenarios[demo_state['current_scenario']]
        
        # Create filter conditions for each ad in current scenario (fixed syntax)
        ad_conditions = [f'r["ad_id"] == "{ad}"' for ad in scenario['ads']]
        ad_filters = '(' + ' or '.join(ad_conditions) + ')'
        print(f"DEBUG: Scenario: {demo_state['current_scenario']}")
        print(f"DEBUG: Ads: {scenario['ads']}")
        print(f"DEBUG: Filter: {ad_filters}")
        
        # Enhanced debug: print the actual query
        print(f"DEBUG: Query filter will be: |> filter(fn: (r) => {ad_filters})")
        
        # Total clicks (count unique events by filtering one field only, current scenario)
        query_total = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["_measurement"] == "adclick_events")
        |> filter(fn: (r) => r["_field"] == "click_value")
        |> filter(fn: (r) => {ad_filters})
        |> count()
        '''
        
        # Clicks per second (last minute, current scenario)
        query_rate = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -1m)
        |> filter(fn: (r) => r["_measurement"] == "adclick_events")
        |> filter(fn: (r) => r["_field"] == "click_value")
        |> filter(fn: (r) => {ad_filters})
        |> count()
        '''
        
        # Fraud rate (last hour) - count fraud vs total, current scenario
        query_fraud_count = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["_measurement"] == "adclick_events")
        |> filter(fn: (r) => r["_field"] == "is_fraud")
        |> filter(fn: (r) => r["_value"] == true)
        |> filter(fn: (r) => {ad_filters})
        |> count()
        '''
        
        # Top ads (last hour - count unique events per ad, filtered by current scenario)
        query_top_ads = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -1h) 
        |> filter(fn: (r) => r["_measurement"] == "adclick_events")
        |> filter(fn: (r) => r["_field"] == "click_value")
        |> filter(fn: (r) => {ad_filters})
        |> group(columns: ["ad_id"])
        |> count()
        |> sort(columns: ["_value"], desc: true)
        |> limit(n: 5)
        '''
        
        # Execute queries
        total_result = list(query_api.query(query_total, org=INFLUX_ORG))
        rate_result = list(query_api.query(query_rate, org=INFLUX_ORG))
        fraud_result = list(query_api.query(query_fraud_count, org=INFLUX_ORG))
        top_ads_result = list(query_api.query(query_top_ads, org=INFLUX_ORG))
        
        # Process results
        total_clicks = sum([record.get_value() for table in total_result for record in table.records]) if total_result and total_result[0].records else 0
        clicks_per_second = sum([record.get_value() for table in rate_result for record in table.records]) if rate_result and rate_result[0].records else 0
        fraud_count = sum([record.get_value() for table in fraud_result for record in table.records]) if fraud_result and fraud_result[0].records else 0
        fraud_rate = (fraud_count / max(total_clicks, 1)) * 100 if total_clicks > 0 else 5.0
        
        # Top ads data from InfluxDB
        top_ads = []
        if top_ads_result:
            for table in top_ads_result:
                for record in table.records:
                    ad_id = record.values.get('ad_id', 'unknown')
                    clicks = record.get_value()
                    top_ads.append({
                        'ad_id': ad_id,
                        'clicks': clicks,
                        'name': ad_id.replace('_', ' ').title()
                    })
        else:
            # Fallback to in-memory events if no InfluxDB data
            scenario = scenarios[demo_state['current_scenario']]
            for ad_id in scenario['ads']:
                event_count = len([e for e in demo_state['events_generated'] if e['ad_id'] == ad_id])
                if event_count > 0:
                    top_ads.append({
                        'ad_id': ad_id,
                        'clicks': event_count,
                        'name': ad_id.replace('_', ' ').title()
                    })
            top_ads = sorted(top_ads, key=lambda x: x['clicks'], reverse=True)[:5]
        
        # Country distribution from recent events (fallback to in-memory)
        scenario = scenarios[demo_state['current_scenario']]
        country_distribution = {}
        recent_events = demo_state['events_generated'][-20:] if demo_state['events_generated'] else []
        
        for country in scenario['countries']:
            country_clicks = len([e for e in recent_events if e['country'] == country])
            country_distribution[country] = {
                'clicks': country_clicks,
                'percentage': round((country_clicks / max(len(recent_events), 1)) * 100, 1)
            }
        
        return jsonify({
            'timestamp': int(current_time.timestamp()),
            'total_clicks': int(total_clicks),
            'clicks_per_second': int(clicks_per_second),
            'top_ads': top_ads[:5],
            'country_distribution': country_distribution,
            'fraud_rate': round(fraud_rate, 1),
            'revenue_per_hour': int(total_clicks * random.uniform(1.0, 3.0)),  # Estimated from clicks
            'active_campaigns': len(scenario['ads']),
            'system_health': {
                'cpu_usage': random.randint(20, 80),
                'memory_usage': random.randint(30, 70),
                'kafka_lag': 0,
                'api_latency': random.randint(50, 200)
            }
        })
        
    except Exception as e:
        print(f"ERROR in realtime metrics: {e}")
        print(f"ERROR: Falling back to generate_realistic_metrics()")
        return jsonify(generate_realistic_metrics())  # Fallback to mock

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
    if not query_api:
        # Fallback to mock data if no DB connection
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
    
    try:
        # Query hourly trends from InfluxDB
        query_hourly = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -24h)
        |> filter(fn: (r) => r["_measurement"] == "adclick_events")
        |> aggregateWindow(every: 1h, fn: count, createEmpty: true)
        |> fill(value: 0)
        |> sort(columns: ["_time"])
        '''
        
        result = list(query_api.query(query_hourly, org=INFLUX_ORG))
        
        hours = []
        clicks = []
        revenue = []
        
        if result and result[0].records:
            for record in result[0].records[-24:]:  # Last 24 hours
                hour_time = record.get_time()
                hours.append(hour_time.strftime('%H:00'))
                click_count = record.get_value() or 0
                clicks.append(int(click_count))
                revenue.append(int(click_count * random.uniform(1.5, 3.0)))  # Estimate revenue from clicks
        else:
            # Fallback if no data yet
            for i in range(24):
                hour = datetime.now() - timedelta(hours=23-i)
                hours.append(hour.strftime('%H:00'))
                clicks.append(0)
                revenue.append(0)
        
        return jsonify({
            'hours': hours,
            'clicks': clicks,
            'revenue': revenue
        })
        
    except Exception as e:
        print(f"Error querying trends from InfluxDB: {e}")
        # Fallback to mock data
        hours = []
        clicks = []
        revenue = []
        
        for i in range(24):
            hour = datetime.now() - timedelta(hours=i)
            hours.append(hour.strftime('%H:00'))
            clicks.append(random.randint(100, 500))
            revenue.append(random.randint(500, 2000))
        
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
    
    # Initialize InfluxDB connection
    print("🔌 Connecting to InfluxDB...")
    if init_influxdb():
        print("✅ InfluxDB connected - real data storage enabled!")
    else:
        print("⚠️ InfluxDB connection failed - using mock data fallback")
    
    print("\n🎯 Ready for customer demonstrations!")
    
    app.run(host='0.0.0.0', port=8900, debug=True)