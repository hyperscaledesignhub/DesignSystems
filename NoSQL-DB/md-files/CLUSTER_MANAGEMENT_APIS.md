# Cluster Management APIs

This document describes the cluster management APIs that allow dynamic addition and removal of nodes in the distributed database cluster.

## Overview

The cluster management APIs provide programmatic control over cluster topology, enabling:
- Dynamic node addition with automatic process management
- Node removal with optional process termination
- Cluster status monitoring and health checks
- Node listing and information retrieval

## API Endpoints

### 1. Add Node to Cluster

**Endpoint:** `POST /cluster/add-node`

**Description:** Start a new node process and automatically join it to the cluster.

**Request Body:**
```json
{
  "node_id": "db-node-4",           // Optional: Auto-generated if not provided
  "port": 8083,                     // Optional: Auto-assigned if not provided
  "host": "127.0.0.1",             // Optional: Defaults to 127.0.0.1
  "config_file": "config/config-local.yaml"  // Optional: Defaults to config/config-local.yaml
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Node db-node-4 started and joined cluster successfully",
  "node_id": "db-node-4",
  "node_address": "127.0.0.1:8083",
  "port": 8083,
  "process_info": {
    "pid": 12345,
    "command": "python distributed/node.py --node-id db-node-4 --host 127.0.0.1 --port 8083 --config-file config/config-local.yaml",
    "node_id": "db-node-4",
    "port": 8083
  },
  "cluster_size": 2
}
```

**Response (Error - 400/500):**
```json
{
  "error": "Port 8083 is not available",
  "available_ports": [8084, 8085, 8086]
}
```

**Features:**
- Automatic port allocation if not specified
- Node ID generation based on existing nodes
- Process management with PID tracking
- Automatic cluster joining
- Port availability validation

### 2. Remove Node from Cluster

**Endpoint:** `POST /cluster/remove-node`

**Description:** Remove a node from the cluster and optionally stop its process.

**Request Body:**
```json
{
  "node_address": "127.0.0.1:8083",  // Required: Node address to remove
  "stop_process": true                 // Optional: Whether to stop the process (default: true)
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Node 127.0.0.1:8083 removed from cluster",
  "node_address": "127.0.0.1:8083",
  "process_stopped": true,
  "cluster_size": 1
}
```

**Response (Error - 400/500):**
```json
{
  "error": "Failed to remove node 127.0.0.1:8083 from cluster"
}
```

**Features:**
- Logical removal from cluster membership
- Optional process termination using `lsof` and `kill`
- Graceful handling of process not found scenarios

### 3. List Cluster Nodes

**Endpoint:** `GET /cluster/list-nodes`

**Description:** Get information about all nodes in the cluster.

**Response (Success - 200):**
```json
{
  "cluster_size": 3,
  "nodes": [
    {
      "node_address": "127.0.0.1:8080",
      "node_id": "db-node-1",
      "is_current": true,
      "status": "running"
    },
    {
      "node_address": "127.0.0.1:8081",
      "node_id": "db-node-2",
      "is_current": false,
      "status": "running"
    },
    {
      "node_address": "127.0.0.1:8082",
      "node_id": "db-node-3",
      "is_current": false,
      "status": "running"
    }
  ],
  "current_node": "127.0.0.1:8080"
}
```

**Features:**
- Complete cluster topology information
- Current node identification
- Node status tracking
- Node ID mapping

### 4. Cluster Status

**Endpoint:** `GET /cluster/status`

**Description:** Get comprehensive cluster status including health information.

**Response (Success - 200):**
```json
{
  "cluster_size": 3,
  "current_node": "127.0.0.1:8080",
  "peers": ["127.0.0.1:8081", "127.0.0.1:8082"],
  "hash_ring_initialized": true,
  "replication_factor": 3,
  "peer_health": {
    "127.0.0.1:8081": {
      "status": "healthy",
      "response_time": 0.002
    },
    "127.0.0.1:8082": {
      "status": "healthy",
      "response_time": 0.003
    }
  }
}
```

**Response (Error - 500):**
```json
{
  "error": "Failed to get cluster status",
  "details": "Connection timeout"
}
```

**Features:**
- Real-time health monitoring
- Response time measurements
- Hash ring status
- Replication factor information

## Usage Examples

### Adding Nodes Dynamically

```bash
# Add a node with auto-assigned port
curl -X POST http://127.0.0.1:8080/cluster/add-node \
  -H "Content-Type: application/json" \
  -d '{"node_id": "db-node-4"}'

# Add a node with specific port
curl -X POST http://127.0.0.1:8080/cluster/add-node \
  -H "Content-Type: application/json" \
  -d '{"node_id": "db-node-5", "port": 8084}'
```

### Removing Nodes

```bash
# Remove a node and stop its process
curl -X POST http://127.0.0.1:8080/cluster/remove-node \
  -H "Content-Type: application/json" \
  -d '{"node_address": "127.0.0.1:8083", "stop_process": true}'

# Remove a node without stopping process
curl -X POST http://127.0.0.1:8080/cluster/remove-node \
  -H "Content-Type: application/json" \
  -d '{"node_address": "127.0.0.1:8083", "stop_process": false}'
```

### Monitoring Cluster

```bash
# Get cluster status
curl http://127.0.0.1:8080/cluster/status

# List all nodes
curl http://127.0.0.1:8080/cluster/list-nodes
```

## Python Client Example

```python
import requests
import time

class ClusterManager:
    def __init__(self, base_url="http://127.0.0.1:8080"):
        self.base_url = base_url
    
    def add_node(self, node_id=None, port=None, host="127.0.0.1"):
        """Add a new node to the cluster"""
        data = {"host": host}
        if node_id:
            data["node_id"] = node_id
        if port:
            data["port"] = port
            
        response = requests.post(f"{self.base_url}/cluster/add-node", json=data)
        return response.json()
    
    def remove_node(self, node_address, stop_process=True):
        """Remove a node from the cluster"""
        data = {
            "node_address": node_address,
            "stop_process": stop_process
        }
        response = requests.post(f"{self.base_url}/cluster/remove-node", json=data)
        return response.json()
    
    def get_status(self):
        """Get cluster status"""
        response = requests.get(f"{self.base_url}/cluster/status")
        return response.json()
    
    def list_nodes(self):
        """List all nodes"""
        response = requests.get(f"{self.base_url}/cluster/list-nodes")
        return response.json()

# Usage
manager = ClusterManager()

# Add nodes
result = manager.add_node("db-node-4", 8083)
print(f"Added node: {result}")

# Check status
status = manager.get_status()
print(f"Cluster size: {status['cluster_size']}")

# Remove node
result = manager.remove_node("127.0.0.1:8083")
print(f"Removed node: {result}")
```

## Process Management

### Node Startup Process

When adding a node, the system:

1. **Port Allocation:** Finds an available port if not specified
2. **Process Creation:** Starts a new Python process with the node script
3. **Configuration:** Sets environment variables for configuration
4. **Health Check:** Waits for the node to start successfully
5. **Cluster Join:** Automatically joins the new node to the cluster
6. **Status Update:** Updates cluster topology

### Node Shutdown Process

When removing a node, the system:

1. **Logical Removal:** Removes the node from cluster membership
2. **Process Termination:** Uses `lsof` to find processes using the port
3. **Signal Sending:** Sends TERM signal to gracefully stop the process
4. **Cleanup:** Updates cluster topology

## Error Handling

### Common Error Scenarios

1. **Port Already in Use:**
   ```json
   {
     "error": "Port 8083 is not available",
     "available_ports": [8084, 8085, 8086]
   }
   ```

2. **Process Start Failure:**
   ```json
   {
     "error": "Failed to start node process",
     "details": {
       "error": "Process failed to start",
       "stdout": "",
       "stderr": "ImportError: No module named 'config'",
       "return_code": 1
     }
   }
   ```

3. **Join Failure:**
   ```json
   {
     "error": "Node started but failed to join cluster",
     "node_address": "127.0.0.1:8083",
     "process_info": {...}
   }
   ```

### Recovery Strategies

1. **Port Conflicts:** Use the `available_ports` list to select a different port
2. **Process Failures:** Check the `stderr` output for configuration issues
3. **Join Failures:** The process may still be running and can be manually joined

## Security Considerations

### Access Control

- APIs are accessible via HTTP without authentication
- Consider implementing authentication for production use
- Network-level security (firewall rules) recommended

### Process Management

- Uses `lsof` for process discovery (Unix/Linux systems)
- Graceful termination with TERM signal
- Fallback handling when `lsof` is not available

## Performance Considerations

### Timeouts

- Node addition: 30 seconds timeout
- Node removal: 10 seconds timeout
- Status checks: 5 seconds timeout

### Resource Usage

- Each node runs as a separate Python process
- Memory usage scales with cluster size
- Network connections for inter-node communication

## Integration with Existing APIs

### Hash Ring Updates

When nodes are added/removed:
- Hash ring is automatically rebuilt
- Key distribution is recalculated
- Virtual node mappings are updated

### Health Monitoring

- Health checks continue for all nodes
- Failed nodes are automatically detected
- Peer discovery maintains cluster connectivity

## Best Practices

### Node Addition

1. **Plan Port Allocation:** Avoid port conflicts by checking available ports
2. **Monitor Resources:** Ensure sufficient system resources for new nodes
3. **Verify Configuration:** Test node startup with the intended configuration
4. **Check Health:** Verify the new node is healthy after addition

### Node Removal

1. **Graceful Shutdown:** Allow time for the node to stop gracefully
2. **Data Migration:** Ensure data is replicated before removing nodes
3. **Health Verification:** Check cluster health after removal
4. **Process Cleanup:** Verify processes are properly terminated

### Monitoring

1. **Regular Status Checks:** Monitor cluster status periodically
2. **Health Alerts:** Set up alerts for unhealthy nodes
3. **Resource Monitoring:** Track CPU, memory, and network usage
4. **Log Analysis:** Monitor logs for errors and warnings

## Troubleshooting

### Common Issues

1. **Node Won't Start:**
   - Check Python environment and dependencies
   - Verify configuration file exists and is valid
   - Check port availability

2. **Node Won't Join:**
   - Verify network connectivity
   - Check firewall settings
   - Ensure seed nodes are accessible

3. **Process Won't Stop:**
   - Check if `lsof` is available
   - Verify process permissions
   - Use manual process termination if needed

### Debug Commands

```bash
# Check if port is in use
lsof -i :8083

# Find Python processes
ps aux | grep python

# Check node logs
tail -f logs/node-8083.log

# Test node connectivity
curl http://127.0.0.1:8083/health
```

## Future Enhancements

### Planned Features

1. **Authentication:** Add API key or token-based authentication
2. **Load Balancing:** Automatic load distribution across nodes
3. **Backup/Restore:** Node state backup and restoration
4. **Metrics:** Detailed performance and health metrics
5. **Web UI:** Graphical cluster management interface

### Configuration Options

1. **Custom Scripts:** Allow custom node startup scripts
2. **Resource Limits:** CPU and memory limits for nodes
3. **Network Policies:** Custom network configuration
4. **Security Policies:** Enhanced security controls

## Conclusion

The cluster management APIs provide comprehensive control over cluster topology, enabling dynamic scaling and maintenance operations. The APIs are designed to be reliable, with proper error handling and recovery mechanisms.

For more information, see:
- [Hash Ring APIs](HASH_RING_APIS.md)
- [Quick Reference](HASH_RING_API_QUICK_REFERENCE.md)
- [Demo Scripts](../demo_cluster_management.py) 