# Cluster Verification Scripts

This directory contains scripts to verify the functionality of your distributed key-value database cluster.

## Available Scripts

### 1. `quick-verify.sh` (Recommended)
- **Purpose**: Quick verification of all cluster functionality
- **Duration**: ~2-3 minutes
- **Behavior**: Runs all tests and exits, leaving cluster running
- **Usage**: `./quick-verify.sh`

### 2. `verify-cluster-functionality.sh`
- **Purpose**: Comprehensive verification with continuous monitoring
- **Duration**: Continuous (until Ctrl+C)
- **Behavior**: Runs all tests and keeps running to monitor cluster
- **Usage**: `./verify-cluster-functionality.sh`

## What the Scripts Test

### ✅ **Persistence**
- Stores data and verifies it survives node restarts
- Checks that data is written to disk (`kvstore.log` files)
- Tests automatic data recovery after node failures

### ✅ **Replication**
- Verifies data is replicated to all 3 nodes
- Tests cross-node data access
- Confirms consistent hashing distribution

### ✅ **Fault Tolerance**
- Tests cluster operation with one node down
- Verifies graceful degradation and recovery
- Confirms quorum-based operations work correctly

### ✅ **Consistency**
- Ensures all nodes return identical data
- Tests coordinator flexibility (any node can handle requests)
- Verifies data integrity across the cluster

### ✅ **Availability**
- Confirms data is accessible from any node
- Tests health checks and node status
- Verifies cluster formation and peer connections

## Prerequisites

1. **Cluster must be running**: Start with `./start-cluster.sh`
2. **Dependencies**: `curl`, `python3`, `yaml` module
3. **Permissions**: Scripts must be executable (`chmod +x *.sh`)

## Usage Examples

```bash
# Start the cluster first
./start-cluster.sh

# In another terminal, run quick verification
./quick-verify.sh

# Or run comprehensive verification (keeps running)
./verify-cluster-functionality.sh
```

## Expected Output

Successful verification will show:
```
✅ PERSISTENCE: Data survives node restarts
✅ REPLICATION: All data replicated to 3 nodes
✅ FAULT TOLERANCE: Cluster works with node failures
✅ CONSISTENCY: All nodes return same data
✅ AVAILABILITY: Data accessible from any node
✅ HEALTH CHECKS: All nodes are healthy

🎉 All tests passed! Your cluster is working perfectly!
```

## Troubleshooting

### Script fails to start
- Ensure cluster is running: `./start-cluster.sh`
- Check if ports are available: `netstat -an | grep 5500`
- Verify config.yaml exists and is readable

### Tests fail
- Check node logs: `tail -f node*.log`
- Verify all nodes are healthy: `curl http://127.0.0.1:55001/health`
- Restart cluster if needed: `pkill -f node.py && ./start-cluster.sh`

### Permission denied
- Make scripts executable: `chmod +x *.sh`

## Manual Testing

You can also test manually with curl commands:

```bash
# Store data
curl -X PUT -H 'Content-Type: application/json' -d '{"value":"test"}' http://127.0.0.1:55001/kv/mykey

# Retrieve data
curl http://127.0.0.1:55002/kv/mykey

# Check node status
curl http://127.0.0.1:55003/info
```

## Cluster Management

- **Start cluster**: `./start-cluster.sh`
- **Stop cluster**: `pkill -f node.py`
- **Check status**: `curl http://127.0.0.1:55001/info`
- **View logs**: `tail -f node*.log` 