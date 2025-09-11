#!/usr/bin/env python3
"""
Enhanced metrics source that supports both regular metrics and batch job metrics
Extends the original test-metrics-source.py with job metric push capabilities
"""

from flask import Flask, Response, request, jsonify
import time
import random
import json
from datetime import datetime
from threading import Lock
from typing import Dict, List

app = Flask(__name__)

# Thread-safe storage for pushed job metrics
job_metrics_store = {}
metrics_lock = Lock()

# Store for historical job metrics
historical_jobs = []

@app.route('/metrics')
def metrics():
    """Expose Prometheus format metrics including job metrics"""
    timestamp = int(time.time())
    cpu_usage = 30 + random.random() * 40
    memory_usage = 60 + random.random() * 20
    disk_usage = 40 + random.random() * 30
    network_in = random.random() * 1000
    network_out = random.random() * 500
    
    # Original system metrics
    metrics_output = f"""# HELP cpu_usage_percent CPU usage percentage
# TYPE cpu_usage_percent gauge
cpu_usage_percent{{host="demo-app",core="0"}} {cpu_usage:.2f}
cpu_usage_percent{{host="demo-app",core="1"}} {cpu_usage + random.gauss(0, 5):.2f}

# HELP memory_usage_percent Memory usage percentage  
# TYPE memory_usage_percent gauge
memory_usage_percent{{host="demo-app",type="physical"}} {memory_usage:.2f}

# HELP disk_usage_percent Disk usage percentage
# TYPE disk_usage_percent gauge
disk_usage_percent{{host="demo-app",device="/dev/sda1"}} {disk_usage:.2f}

# HELP network_bytes_total Network bytes transferred
# TYPE network_bytes_total counter
network_bytes_total{{host="demo-app",direction="in"}} {network_in:.0f}
network_bytes_total{{host="demo-app",direction="out"}} {network_out:.0f}

# HELP request_count_total HTTP requests total
# TYPE request_count_total counter
request_count_total{{host="demo-app",method="GET",status="200"}} {random.randint(1000, 5000)}
request_count_total{{host="demo-app",method="POST",status="200"}} {random.randint(500, 2000)}

# HELP response_time_seconds HTTP response time in seconds
# TYPE response_time_seconds histogram
response_time_seconds{{host="demo-app",endpoint="/api/users"}} {random.uniform(0.01, 0.5):.3f}

"""
    
    # Add job metrics if any exist
    with metrics_lock:
        if job_metrics_store:
            metrics_output += "\n# Job Metrics\n"
            for metric_name, metric_data in job_metrics_store.items():
                labels_str = ",".join([f'{k}="{v}"' for k, v in metric_data.get("labels", {}).items()])
                if labels_str:
                    metrics_output += f'{metric_name}{{{labels_str}}} {metric_data["value"]}\n'
                else:
                    metrics_output += f'{metric_name} {metric_data["value"]}\n'
    
    return Response(metrics_output, mimetype='text/plain')

@app.route('/push', methods=['POST'])
def push_metric():
    """Accept pushed metrics from batch jobs"""
    try:
        metric_data = request.get_json()
        
        if not metric_data or 'name' not in metric_data or 'value' not in metric_data:
            return jsonify({"error": "Invalid metric data"}), 400
        
        # Store the metric
        with metrics_lock:
            job_metrics_store[metric_data['name']] = {
                "value": float(metric_data['value']),
                "labels": metric_data.get('labels', {}),
                "timestamp": metric_data.get('timestamp', datetime.utcnow().isoformat())
            }
        
        # If this is a job completion/failure metric, add to historical data
        if metric_data['name'] in ['job_end_time', 'job_failure_count']:
            with metrics_lock:
                historical_jobs.append({
                    "metric": metric_data,
                    "received_at": datetime.utcnow().isoformat()
                })
        
        return jsonify({"status": "success", "message": "Metric received"}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/jobs/metrics')
def job_metrics():
    """Return current job metrics in JSON format"""
    with metrics_lock:
        return jsonify({
            "current_metrics": job_metrics_store,
            "historical_count": len(historical_jobs),
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/jobs/historical')
def historical_job_metrics():
    """Return historical job metrics"""
    with metrics_lock:
        return jsonify({
            "historical_jobs": historical_jobs,
            "count": len(historical_jobs),
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/jobs/status')
def job_status():
    """Return current job status summary"""
    with metrics_lock:
        active_jobs = {}
        completed_jobs = 0
        failed_jobs = 0
        
        # Analyze current metrics for job status
        for name, data in job_metrics_store.items():
            if 'job_id' in data.get('labels', {}):
                job_id = data['labels']['job_id']
                job_type = data['labels'].get('job_type', 'unknown')
                status = data['labels'].get('status', 'unknown')
                
                if job_id not in active_jobs:
                    active_jobs[job_id] = {
                        "job_type": job_type,
                        "status": status,
                        "metrics": {}
                    }
                
                active_jobs[job_id]["metrics"][name] = data["value"]
                
                if status == "completed":
                    completed_jobs += 1
                elif status == "failed":
                    failed_jobs += 1
        
        return jsonify({
            "active_jobs": active_jobs,
            "summary": {
                "total_active": len(active_jobs),
                "completed": completed_jobs,
                "failed": failed_jobs
            },
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "timestamp": int(time.time()),
        "metrics_count": len(job_metrics_store),
        "historical_count": len(historical_jobs)
    })

@app.route('/clear', methods=['POST'])
def clear_metrics():
    """Clear stored job metrics (for testing)"""
    with metrics_lock:
        job_metrics_store.clear()
        historical_jobs.clear()
    
    return jsonify({"status": "success", "message": "Metrics cleared"})

@app.route('/')
def index():
    """Root endpoint with service info"""
    return jsonify({
        "service": "Enhanced Metrics Source",
        "version": "1.1.0",
        "endpoints": {
            "/metrics": "Prometheus format metrics",
            "/push": "Push job metrics (POST)",
            "/jobs/metrics": "Current job metrics (JSON)",
            "/jobs/historical": "Historical job data",
            "/jobs/status": "Job status summary",
            "/health": "Health check",
            "/clear": "Clear metrics (POST)"
        },
        "current_metrics": len(job_metrics_store),
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Enhanced Metrics Source starting...")
    print("📊 Supports both system metrics and batch job metrics")
    print("🔗 Endpoints:")
    print("   • GET  /metrics - Prometheus format")
    print("   • POST /push - Push job metrics")
    print("   • GET  /jobs/metrics - Job metrics JSON")
    print("   • GET  /jobs/status - Job status summary")
    print("   • GET  /health - Health check")
    
    app.run(host='0.0.0.0', port=3001, debug=False)