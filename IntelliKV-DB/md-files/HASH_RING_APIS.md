# Hash Ring APIs: Virtual Nodes, Key Distribution & Migration Analysis

## Overview

This document describes the comprehensive set of APIs for analyzing and monitoring the consistent hashing ring behavior in the distributed key-value store. These APIs provide insights into virtual node distribution, key placement, and migration patterns when nodes are added or removed.

## API Endpoints

### 1. Virtual Node Details

#### `GET /ring/virtual-nodes`

Returns detailed information about virtual nodes in the hash ring.

**Response:**
```json
{
  "hash_ring_library": "hashring|fallback",
  "virtual_nodes": 450,
  "virtual_nodes_per_physical": 150,
  "virtual_node_mapping": {
    "127.0.0.1:8080": [
      {
        "virtual_node_name": "127.0.0.1:8080-0",
        "hash": 123456789,
        "position": 0.25
      }
    ]
  },
  "physical_nodes": ["127.0.0.1:8080", "127.0.0.1:8081", "127.0.0.1:8082"],
  "node_count": 3,
  "replication_factor": 3,
  "hash_ring_available": true
}
```

**Example:**
```bash
curl http://localhost:8080/ring/virtual-nodes
```

### 2. Key Distribution Analysis

#### `GET /ring/key-distribution`

Analyzes how keys are distributed across physical and virtual nodes.

**Query Parameters:**
- `keys` (optional): Comma-separated list of specific keys to analyze
- If not provided, analyzes 1000 sample keys

**Response:**
```json
{
  "total_keys_analyzed": 1000,
  "physical_node_distribution": {
    "127.0.0.1:8080": 334,
    "127.0.0.1:8081": 333,
    "127.0.0.1:8082": 333
  },
  "virtual_node_distribution": {
    "127.0.0.1:8080-0": 112,
    "127.0.0.1:8080-1": 111,
    "127.0.0.1:8081-0": 111
  },
  "distribution_stats": {
    "physical_nodes": {
      "min_keys": 333,
      "max_keys": 334,
      "avg_keys": 333.33
    },
    "virtual_nodes": {
      "min_keys": 110,
      "max_keys": 112,
      "avg_keys": 111.11
    }
  }
}
```

**Examples:**
```bash
# Analyze 1000 sample keys
curl http://localhost:8080/ring/key-distribution

# Analyze specific keys
curl "http://localhost:8080/ring/key-distribution?keys=user1,user2,product1,order1"
```

### 3. Key Migration Analysis

#### `GET /ring/migration-analysis`

Analyzes key migration patterns when nodes are added or removed from the cluster.

**Query Parameters:**
- `keys` (optional): Comma-separated list of specific keys to analyze
- `sample_size` (optional): Number of sample keys to generate (default: 1000)

**Response:**
```json
{
  "total_keys_analyzed": 100,
  "migration_summary": {
    "keys_migrated": 21,
    "migration_percentage": 21.0,
    "keys_unchanged": 79,
    "unchanged_percentage": 79.0
  },
  "migration_details": {
    "127.0.0.1:8082 -> 127.0.0.1:8083": {
      "source_node": "127.0.0.1:8082",
      "destination_node": "127.0.0.1:8083",
      "keys": ["key_18", "key_43", "key_52"],
      "count": 9
    },
    "127.0.0.1:8081 -> 127.0.0.1:8083": {
      "source_node": "127.0.0.1:8081",
      "destination_node": "127.0.0.1:8083",
      "keys": ["key_23", "key_27", "key_44"],
      "count": 6
    }
  },
  "current_node_count": 4,
  "previous_node_count": 3
}
```

**Examples:**
```bash
# Analyze with default 1000 sample keys
curl http://localhost:8080/ring/migration-analysis

# Analyze with custom sample size
curl "http://localhost:8080/ring/migration-analysis?sample_size=500"

# Analyze specific keys
curl "http://localhost:8080/ring/migration-analysis?keys=user1,user2,product1"
```

### 4. Reset Migration Tracking

#### `POST /ring/reset-migration-tracking`

Resets the migration tracking state to establish a new baseline.

**Response:**
```json
{
  "message": "Migration tracking reset",
  "previous_mapping_cleared": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/ring/reset-migration-tracking
```

## Usage Scenarios

### 1. Cluster Expansion Planning

When adding new nodes to the cluster:

```bash
# 1. Get current distribution
curl http://localhost:8080/ring/key-distribution

# 2. Reset migration tracking
curl -X POST http://localhost:8080/ring/reset-migration-tracking

# 3. Add new node to cluster (via join API)
curl -X POST http://localhost:8080/join -H "Content-Type: application/json" \
  -d '{"peer_address": "127.0.0.1:8083"}'

# 4. Analyze migration impact
curl http://localhost:8080/ring/migration-analysis
```

### 2. Node Failure Impact Assessment

When a node fails or is removed:

```bash
# 1. Analyze migration after node removal
curl http://localhost:8080/ring/migration-analysis?sample_size=1000

# 2. Check load distribution on remaining nodes
curl http://localhost:8080/ring/key-distribution
```

### 3. Load Balancing Verification

To verify even key distribution:

```bash
# Check physical node distribution
curl http://localhost:8080/ring/key-distribution | jq '.physical_node_distribution'

# Check virtual node distribution (if using fallback implementation)
curl http://localhost:8080/ring/key-distribution | jq '.virtual_node_distribution'
```

## Migration Analysis Workflow

### Step 1: Establish Baseline
```bash
# Reset tracking and establish baseline
curl -X POST http://localhost:8080/ring/reset-migration-tracking
curl http://localhost:8080/ring/migration-analysis
# Returns: "No previous mapping available. Current mapping stored for future comparison."
```

### Step 2: Make Cluster Changes
```bash
# Add or remove nodes from cluster
curl -X POST http://localhost:8080/join -d '{"peer_address": "127.0.0.1:8083"}'
# or
curl -X POST http://localhost:8080/remove_peer -d '{"peer_address": "127.0.0.1:8081"}'
```

### Step 3: Analyze Migration Impact
```bash
# Get migration analysis
curl http://localhost:8080/ring/migration-analysis
# Returns detailed migration information including:
# - Percentage of keys that moved
# - Source and destination nodes for each migration
# - Sample keys that migrated
```

## Response Patterns

### Success Response
All APIs return HTTP 200 with JSON response containing the requested data.

### Error Response
```json
{
  "error": "Hash ring not initialized",
  "message": "Additional error details"
}
```

Common error scenarios:
- Hash ring not initialized
- No nodes available
- Invalid parameters

## Performance Considerations

### Sample Size Impact
- **Small sample (100 keys)**: Fast response, good for demos
- **Medium sample (1000 keys)**: Balanced performance and accuracy
- **Large sample (10000+ keys)**: More accurate but slower response

### Caching
- Virtual node details are cached and updated when nodes change
- Key distribution analysis is computed on-demand
- Migration analysis requires baseline establishment

## Integration with Monitoring

### Prometheus Metrics
These APIs can be used to generate custom metrics:

```python
# Example: Track migration percentage
migration_data = requests.get("http://localhost:8080/ring/migration-analysis").json()
migration_percentage = migration_data['migration_summary']['migration_percentage']
prometheus_gauge.set(migration_percentage)
```

### Grafana Dashboards
Use the APIs to create dashboards showing:
- Key distribution across nodes
- Migration patterns over time
- Virtual node utilization

## Troubleshooting

### Common Issues

1. **"Hash ring not initialized"**
   - Ensure nodes are properly joined to the cluster
   - Check that the node has peers

2. **No migration detected**
   - Verify migration tracking was reset before cluster changes
   - Check that actual node changes occurred

3. **Inconsistent results**
   - Ensure all nodes have the same peer list
   - Check for network partitions

### Debug Commands
```bash
# Check current ring state
curl http://localhost:8080/ring

# Verify peer list
curl http://localhost:8080/peers

# Check node health
curl http://localhost:8080/health
```

## Best Practices

1. **Establish baseline before changes**: Always reset migration tracking before making cluster changes
2. **Use appropriate sample sizes**: Balance accuracy with performance
3. **Monitor migration percentages**: High migration rates (>50%) may indicate issues
4. **Verify even distribution**: Check that keys are evenly distributed across nodes
5. **Track over time**: Use these APIs to monitor cluster health and performance

## Related Documentation

- [Consistency Models Guide](CONSISTENCY_MODELS_GUIDE.md)
- [Cluster Startup Guide](CLUSTER_STARTUP_GUIDE.md)
- [Anti-Entropy Guide](ANTI_ENTROPY_GUIDE.md)
- [CRDT Counters Guide](CRDT_COUNTERS.md) 