#!/bin/bash

echo "🚀 Starting real-time metrics feeder..."
echo "📊 Adding time-series data every 5 seconds..."
echo "🔄 Press Ctrl+C to stop"

# Base values for realistic metrics
CPU_BASE=45
MEMORY_BASE=60
DISK_BASE=35

while true; do
    TIMESTAMP=$(date +%s)000000000
    
    # Generate realistic values with variation
    CPU_VAR=$((RANDOM % 30 - 15))
    MEMORY_VAR=$((RANDOM % 20 - 10))
    DISK_VAR=$((RANDOM % 10 - 5))
    
    CPU_VALUE=$((CPU_BASE + CPU_VAR))
    MEMORY_VALUE=$((MEMORY_BASE + MEMORY_VAR))
    DISK_VALUE=$((DISK_BASE + DISK_VAR))
    
    # Ensure values are within realistic bounds
    CPU_VALUE=$(( CPU_VALUE < 0 ? 5 : (CPU_VALUE > 100 ? 95 : CPU_VALUE) ))
    MEMORY_VALUE=$(( MEMORY_VALUE < 0 ? 10 : (MEMORY_VALUE > 100 ? 90 : MEMORY_VALUE) ))
    DISK_VALUE=$(( DISK_VALUE < 0 ? 5 : (DISK_VALUE > 100 ? 85 : DISK_VALUE) ))
    
    # Create metrics data
    DATA="cpu.usage,host=demo-host value=${CPU_VALUE} ${TIMESTAMP}
memory.usage_percent,host=demo-host value=${MEMORY_VALUE} ${TIMESTAMP}
disk.usage_percent,host=demo-host value=${DISK_VALUE} ${TIMESTAMP}"
    
    # Send to InfluxDB
    curl -s -X POST "http://localhost:8026/api/v2/write?org=metrics&bucket=metrics" \
      -H "Authorization: Token demo-token-123" \
      -H "Content-Type: text/plain" \
      -d "$DATA" > /dev/null
    
    echo "✅ $(date '+%H:%M:%S') - CPU: ${CPU_VALUE}%, Memory: ${MEMORY_VALUE}%, Disk: ${DISK_VALUE}%"
    
    sleep 5
done