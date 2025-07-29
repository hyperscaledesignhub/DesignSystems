# Quick Reference Guide

## Consistency Models Decision Tree

```
Data Type? → Choose Consistency Model
├── Time-sensitive (logs, metrics) → QUORUM
├── Data with dependencies → CAUSAL  
├── Business-critical (financial) → STRONG
└── High availability needed → QUORUM
```

## Conflict Resolution Strategies

| Operation Type | Conflict Resolution | When Used |
|----------------|-------------------|-----------|
| **Quorum Read** | Last-Write-Wins (LWW) | Inconsistent values detected |
| **Causal Read** | Vector Clock Ordering | Concurrent writes |
| **Quorum Write** | Timestamp-based | Always (for ordering) |

## API Quick Reference

### Quorum Operations
```bash
# Write
PUT /kv/{key}
{"value": "data"}

# Read  
GET /kv/{key}
```

### Causal Operations
```bash
# Write
PUT /causal/kv/{key}
{"value": "data", "vector_clock": {"node-1": 5}}

# Read
GET /causal/kv/{key}
```

## Response Patterns

### Quorum Read - Consistent
```json
{
  "value": "data",
  "consistency_level": "quorum_consistent"
}
```

### Quorum Read - Conflict Resolved
```json
{
  "value": "resolved_value",
  "consistency_level": "quorum_resolved",
  "conflict_resolution": {
    "strategy": "last_write_wins",
    "resolved_timestamp": 1234567890.123
  }
}
```

### Causal Read
```json
{
  "value": "data",
  "vector_clock": {"node-1": 6, "node-2": 3},
  "causal_operation": true
}
```

## Business Scenarios

### Social Media (Use Causal)
```python
# 1. Update profile
PUT /causal/kv/user:123:profile {"value": "new_pic.jpg"}

# 2. Create post (depends on profile)
PUT /causal/kv/user:123:post:456 {"value": "Check out my new pic!"}

# 3. Read (guarantees consistency)
GET /causal/kv/user:123:post:456
```

### Logging (Use Quorum)
```python
# Fast writes for logs
PUT /kv/logs:2024:01:01 {"value": "user_login_event"}

# Eventual consistency is fine
GET /kv/logs:2024:01:01
```

## Testing Commands

```bash
# Test timestamp-based conflict resolution
python -m pytest distributed/node.py::TestRobustSimpleGossip::test_quorum_read_timestamp_conflict_resolution -v -s

# Run all tests
python -m pytest distributed/node.py -v

# Start cluster
python distributed/node.py --node-id node-1 --port 8080
```

## Key Implementation Details

### Timestamp Collection
```python
# Enhanced quorum read collects timestamps
def _collect_responses_from_nodes(self, key: str):
    responses = {}
    timestamps = {}  # For LWW conflict resolution
    # ... collect from all nodes
    return {"responses": responses, "timestamps": timestamps}
```

### LWW Conflict Resolution
```python
# When conflicts detected
latest_timestamp = max(timestamps.values())
resolved_value = responses[node_with_latest_timestamp]
```

### Vector Clock Management
```python
# Causal write increments vector clock
self.vector_clock.increment(self.node_id)
if external_clock:
    self.vector_clock.merge(external_clock)
```

## Configuration

### Quorum Settings (config.yaml)
```yaml
quorum:
  read_quorum: 2
  write_quorum: 2
  replication_factor: 3
```

### Node Configuration
```bash
# Environment variables
CONFIG_FILE=config.yaml
NODE_ID=node-1
PORT=8080
```

## Monitoring & Debugging

### Health Check
```bash
curl http://localhost:8080/health
```

### Node Info
```bash
curl http://localhost:8080/info
```

### Causal Stats
```bash
curl http://localhost:8080/causal/stats
```

### Vector Clock
```bash
curl http://localhost:8080/causal/vector-clock
```

## Best Practices

### ✅ Do's
- Use **quorum** for time-sensitive, high-availability data
- Use **causal** for data with dependencies
- Always implement **read repair** (anti-entropy)
- Monitor **conflict resolution** metrics
- Test with **network partitions**

### ❌ Don'ts
- Don't use quorum for data dependencies
- Don't use causal for simple key-value operations
- Don't ignore conflict resolution metadata
- Don't skip read repair implementation

## Performance Characteristics

| Operation | Latency | Consistency | Availability |
|-----------|---------|-------------|--------------|
| Quorum Read | Low | Eventual | High |
| Quorum Write | Low | Eventual | High |
| Causal Read | Medium | Causal | Medium |
| Causal Write | Medium | Causal | Medium |

## Error Handling

### Quorum Not Reached
```json
{
  "error": "Quorum not reached",
  "responses_received": 1,
  "quorum_required": 2
}
```

### Causal Put Failed
```json
{
  "error": "Causal put failed"
}
```

## Migration Guide

### From Simple KV to Quorum
1. Change endpoints: `/kv/{key}` instead of direct storage
2. Handle quorum responses
3. Implement conflict resolution

### From Quorum to Causal
1. Change endpoints: `/causal/kv/{key}`
2. Include vector clocks in requests
3. Handle causal ordering

## Troubleshooting

### Common Issues
1. **Nodes not joining**: Check network connectivity
2. **Quorum failures**: Verify replication factor
3. **Causal conflicts**: Check vector clock implementation
4. **Performance issues**: Monitor anti-entropy intervals

### Debug Commands
```bash
# Check cluster status
curl http://localhost:8080/peers

# Verify hash ring
curl http://localhost:8080/ring

# Check quorum info
curl http://localhost:8080/quorum/{key}
``` 