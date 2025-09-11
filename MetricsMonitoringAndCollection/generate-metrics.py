#!/usr/bin/env python3
"""
Real-time metrics generator for dashboard demo.
Generates realistic system metrics and sends them directly to InfluxDB.
"""

import requests
import time
import random
import psutil
import json
from datetime import datetime

INFLUXDB_URL = "http://localhost:8026"
INFLUXDB_TOKEN = "demo-token-123"
INFLUXDB_ORG = "metrics"
INFLUXDB_BUCKET = "metrics"

def get_real_system_metrics():
    """Get actual system metrics."""
    return {
        'cpu_usage': psutil.cpu_percent(interval=1),
        'memory_usage_percent': psutil.virtual_memory().percent,
        'disk_usage_percent': psutil.disk_usage('/').percent,
        'network_bytes_sent': psutil.net_io_counters().bytes_sent,
        'network_bytes_recv': psutil.net_io_counters().bytes_recv,
    }

def generate_realistic_metrics():
    """Generate realistic metrics with some variation."""
    base_metrics = get_real_system_metrics()
    
    # Add some realistic variation for demo purposes
    cpu_variation = random.uniform(-10, 10)
    memory_variation = random.uniform(-5, 5)
    disk_variation = random.uniform(-2, 2)
    
    return {
        'cpu.usage': max(0, min(100, base_metrics['cpu_usage'] + cpu_variation)),
        'memory.usage_percent': max(0, min(100, base_metrics['memory_usage_percent'] + memory_variation)),
        'disk.usage_percent': max(0, min(100, base_metrics['disk_usage_percent'] + disk_variation)),
        'network.bytes_sent': base_metrics['network_bytes_sent'],
        'network.bytes_recv': base_metrics['network_bytes_recv'],
    }

def write_metrics_to_influxdb(metrics):
    """Write metrics to InfluxDB."""
    timestamp = int(time.time() * 1000000000)  # nanoseconds
    lines = []
    
    for metric_name, value in metrics.items():
        line = f"{metric_name},host=demo-host value={value} {timestamp}"
        lines.append(line)
    
    data = "\n".join(lines)
    
    url = f"{INFLUXDB_URL}/api/v2/write"
    headers = {
        "Authorization": f"Token {INFLUXDB_TOKEN}",
        "Content-Type": "text/plain"
    }
    params = {
        "org": INFLUXDB_ORG,
        "bucket": INFLUXDB_BUCKET
    }
    
    try:
        response = requests.post(url, headers=headers, params=params, data=data, timeout=5)
        if response.status_code == 204:
            print(f"✅ Written metrics: CPU={metrics['cpu.usage']:.1f}%, Memory={metrics['memory.usage_percent']:.1f}%, Disk={metrics['disk.usage_percent']:.1f}%")
        else:
            print(f"❌ Failed to write metrics: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error writing metrics: {e}")

def main():
    print("🚀 Starting real-time metrics generator...")
    print("📊 Generating system metrics every 10 seconds...")
    print("🔄 Press Ctrl+C to stop")
    
    try:
        while True:
            metrics = generate_realistic_metrics()
            write_metrics_to_influxdb(metrics)
            time.sleep(10)  # Generate metrics every 10 seconds
    except KeyboardInterrupt:
        print("\n🛑 Metrics generator stopped")

if __name__ == "__main__":
    main()