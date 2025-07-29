# Quorum Read and Write API Guide

This guide shows how to invoke quorum-based read and write operations via the HTTP API in the distributed key-value database.

## API Endpoints Overview

### Quorum Operations
- **Quorum Write**: `PUT /kv/<key>` - Write with quorum consistency
- **Quorum Read**: `GET /kv/<key>` - Read with quorum consistency  
- **Quorum Info**: `GET /quorum/<key>` - Get quorum information for a key

### Causal Consistency with Quorum
- **Causal Quorum Write**: `PUT /causal/kv/<key>` - Write with causal consistency + quorum replication
- **Causal Quorum Read**: `GET /causal/kv/<key>` - Read with causal consistency + quorum reads

### Direct Operations (Internal Use)
- **Direct Write**: `PUT /kv/<key>/direct` - Write directly to local node
- **Direct Read**: `GET /kv/<key>/direct` - Read directly from local node

## 1. Quorum Write Operations

### Basic Quorum Write
```bash
# Write a key-value pair with quorum consistency
curl -X PUT http://localhost:9999/kv/my-key \
  -H "Content-Type: application/json" \
  -d '{"value": "my-value"}'
```

**Response (Success):**
```json
{
  "key": "my-key",
  "value": "my-value",
  "replicas": ["localhost:9999", "localhost:10000", "localhost:10001"],
  "coordinator": "localhost:9999",
  "successful_writes": 2,
  "total_replicas": 3,
  "write_quorum": 2,
  "replication_factor": 3,
  "successful_nodes": ["localhost:9999", "localhost:10000"],
  "failed_nodes": [],
  "async_replication": ["localhost:10001"],
  "optimistic": true
}
```

**Response (Failure):**
```json
{
  "error": "Write failed - quorum not reached (required: 2, succeeded: 1)",
  "successful_writes": 1,
  "write_quorum": 2,
  "total_replicas": 3,
  "replication_factor": 3,
  "successful_nodes": ["localhost:9999"],
  "failed_nodes": ["localhost:10000 (status 500)", "localhost:10001 (error: Connection failed)"]
}
```

### Quorum Write with Custom Value
```bash
# Write complex data
curl -X PUT http://localhost:9999/kv/user-123 \
  -H "Content-Type: application/json" \
  -d '{"value": "{\"name\": \"John Doe\", \"email\": \"john@example.com\"}"}'
```

## 2. Quorum Read Operations

### Basic Quorum Read
```bash
# Read a key with quorum consistency
curl -X GET http://localhost:9999/kv/my-key
```

**Response (Success):**
```json
{
  "key": "my-key",
  "value": "my-value",
  "node_id": "localhost:9999",
  "read_quorum": 1,
  "nodes_contacted": ["localhost:9999", "localhost:10000"],
  "consistency_level": "QUORUM"
}
```

**Response (Not Found):**
```json
{
  "error": "Key not found"
}
```

### Quorum Read with Error Handling
```bash
# Read with proper error handling
curl -X GET http://localhost:9999/kv/nonexistent-key
```

## 3. Quorum Information

### Get Quorum Info for a Key
```bash
# Get detailed quorum information for a specific key
curl -X GET http://localhost:9999/quorum/my-key
```

**Response:**
```json
{
  "key": "my-key",
  "replication_factor": 3,
  "write_quorum": 2,
  "read_quorum": 1,
  "responsible_nodes": ["localhost:9999", "localhost:10000", "localhost:10001"],
  "explanation": "Key 'my-key' requires 2 out of 3 nodes for write quorum, 1 out of 3 for read quorum"
}
```

## 4. Causal Consistency with Quorum

### Causal Quorum Write
```bash
# Write with causal consistency using quorum replication
curl -X PUT http://localhost:9999/causal/kv/my-key \
  -H "Content-Type: application/json" \
  -d '{"value": "my-value"}'
```

**Response (Success):**
```json
{
  "key": "my-key",
  "value": "my-value",
  "vector_clock": {"node1": 1, "node2": 0, "node3": 0},
  "node_id": "node1",
  "causal_operation": true,
  "quorum_result": {
    "successful_writes": 2,
    "write_quorum": 2,
    "successful_nodes": ["localhost:9999", "localhost:10000"],
    "async_replication": ["localhost:10001"]
  },
  "successful_writes": 2,
  "async_replication": ["localhost:10001"]
}
```

**Response (Partial Success):**
```json
{
  "key": "my-key",
  "value": "my-value",
  "vector_clock": {"node1": 1, "node2": 0, "node3": 0},
  "node_id": "node1",
  "causal_operation": true,
  "quorum_error": "Write failed - quorum not reached (required: 2, succeeded: 1)",
  "warning": "Causal operation succeeded locally but quorum replication failed"
}
```

### Causal Quorum Read
```bash
# Read with causal consistency using quorum reads
curl -X GET http://localhost:9999/causal/kv/my-key
```

**Response (Causal + Quorum):**
```json
{
  "key": "my-key",
  "value": "my-value",
  "vector_clock": {"node1": 1, "node2": 0, "node3": 0},
  "node_id": "node1",
  "creation_time": 1640995200.123,
  "causal_operation": true,
  "source": "local_causal",
  "quorum_result": {
    "key": "my-key",
    "value": "my-value",
    "node_id": "localhost:9999"
  },
  "consistency_level": "causal_with_quorum"
}
```

**Response (Quorum Only):**
```json
{
  "key": "my-key",
  "value": "my-value",
  "node_id": "localhost:9999",
  "causal_operation": true,
  "source": "quorum_only",
  "quorum_result": {
    "key": "my-key",
    "value": "my-value",
    "node_id": "localhost:9999"
  },
  "consistency_level": "quorum_only",
  "warning": "No causal metadata available, using quorum read result"
}
```

## 4. Direct Operations (Internal Use)

### Direct Write (Bypass Quorum)
```bash
# Write directly to local node without replication
curl -X PUT http://localhost:9999/kv/my-key/direct \
  -H "Content-Type: application/json" \
  -d '{"value": "direct-value"}'
```

**Response:**
```json
{
  "key": "my-key",
  "value": "direct-value",
  "node_id": "localhost:9999",
  "timestamp": 1640995200.123
}
```

### Direct Read (Bypass Quorum)
```bash
# Read directly from local node
curl -X GET http://localhost:9999/kv/my-key/direct
```

**Response:**
```json
{
  "key": "my-key",
  "value": "direct-value",
  "node_id": "localhost:9999"
}
```

## 5. Python Examples

### Using requests library
```python
import requests
import json

# Quorum Write
def quorum_write(node_url, key, value):
    response = requests.put(
        f"{node_url}/kv/{key}",
        json={"value": value},
        headers={"Content-Type": "application/json"}
    )
    return response.json()

# Quorum Read
def quorum_read(node_url, key):
    response = requests.get(f"{node_url}/kv/{key}")
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Get Quorum Info
def get_quorum_info(node_url, key):
    response = requests.get(f"{node_url}/quorum/{key}")
    return response.json()

# Example usage
node_url = "http://localhost:9999"

# Write with quorum
result = quorum_write(node_url, "user-123", "John Doe")
print(f"Write result: {result}")

# Read with quorum
value = quorum_read(node_url, "user-123")
print(f"Read result: {value}")

# Get quorum info
info = get_quorum_info(node_url, "user-123")
print(f"Quorum info: {info}")
```

## 6. JavaScript/Node.js Examples

### Using fetch API
```javascript
// Quorum Write
async function quorumWrite(nodeUrl, key, value) {
    const response = await fetch(`${nodeUrl}/kv/${key}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ value })
    });
    return await response.json();
}

// Quorum Read
async function quorumRead(nodeUrl, key) {
    const response = await fetch(`${nodeUrl}/kv/${key}`);
    if (response.ok) {
        return await response.json();
    }
    return null;
}

// Get Quorum Info
async function getQuorumInfo(nodeUrl, key) {
    const response = await fetch(`${nodeUrl}/quorum/${key}`);
    return await response.json();
}

// Example usage
const nodeUrl = 'http://localhost:9999';

// Write with quorum
quorumWrite(nodeUrl, 'user-123', 'John Doe')
    .then(result => console.log('Write result:', result))
    .catch(error => console.error('Write error:', error));

// Read with quorum
quorumRead(nodeUrl, 'user-123')
    .then(value => console.log('Read result:', value))
    .catch(error => console.error('Read error:', error));
```

## 7. Configuration

### Current Quorum Settings
The quorum settings are configured in `yaml/config-local.yaml`:

```yaml
quorum:
  read_quorum: 1    # Read from 1 node
  write_quorum: 2   # Write to 2 nodes for quorum
```

### Understanding Quorum Behavior

1. **Write Quorum**: 
   - Requires `write_quorum` successful writes (currently 2)
   - Uses optimistic replication: returns success after quorum is achieved
   - Remaining nodes are replicated asynchronously

2. **Read Quorum**:
   - Requires `read_quorum` successful reads (currently 1)
   - Returns the first successful response

3. **Replication Factor**: 
   - Total number of nodes responsible for the key (currently 3)
   - Determined by consistent hashing

## 8. Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "error": "No value provided"
}
```

**404 Not Found:**
```json
{
  "error": "Key not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Write failed - quorum not reached (required: 2, succeeded: 1)"
}
```

### Best Practices

1. **Always check response status codes**
2. **Handle quorum failures gracefully**
3. **Use retry logic for transient failures**
4. **Monitor quorum info for key distribution**
5. **Use direct operations only for internal/debugging purposes**

## 9. Testing Quorum Operations

### Start a Local Cluster
```bash
# Start 3-node cluster
cd scripts
./start-cluster-local.sh
```

### Test Quorum Operations
```bash
# Test write
curl -X PUT http://localhost:9999/kv/test-key \
  -H "Content-Type: application/json" \
  -d '{"value": "test-value"}'

# Test read
curl -X GET http://localhost:9999/kv/test-key

# Get quorum info
curl -X GET http://localhost:9999/quorum/test-key
```

This guide covers all the essential quorum operations available through the API. The quorum system ensures consistency while providing high availability through replication. 