#!/usr/bin/env python3
"""
Simple metrics source that exposes Prometheus format metrics
"""

from flask import Flask, Response
import time
import random

app = Flask(__name__)

@app.route('/metrics')
def metrics():
    """Expose Prometheus format metrics"""
    timestamp = int(time.time())
    cpu_usage = 30 + random.random() * 40
    memory_usage = 60 + random.random() * 20
    disk_usage = 40 + random.random() * 30
    network_in = random.random() * 1000
    network_out = random.random() * 500
    
    metrics = f"""# HELP cpu_usage_percent CPU usage percentage
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
    
    return Response(metrics, mimetype='text/plain')

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": int(time.time())}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=False)