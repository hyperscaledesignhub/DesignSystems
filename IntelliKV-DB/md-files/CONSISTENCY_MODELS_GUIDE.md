# Consistency Models and Conflict Resolution Guide

## Table of Contents
1. [Overview](#overview)
2. [Consistency Models](#consistency-models)
3. [Conflict Resolution Strategies](#conflict-resolution-strategies)
4. [Implementation Details](#implementation-details)
5. [Business Scenarios](#business-scenarios)
6. [Usage Guidelines](#usage-guidelines)
7. [API Reference](#api-reference)

## Overview

This guide covers the different consistency models implemented in our distributed key-value store, their use cases, and conflict resolution strategies.

## Consistency Models

### 1. Quorum Consistency (Eventual Consistency)

**Characteristics:**
- Fast reads and writes
- Eventual consistency across replicas
- Configurable read/write quorum values
- Timestamp-based conflict resolution (Last-Write-Wins)

**Use Cases:**
- Time-sensitive data (logs, metrics, analytics)
- High availability requirements
- Data where eventual consistency is acceptable

**Implementation:**
```python
# Quorum Write
PUT /kv/{key}
{
  "value": "data",
  "timestamp": 1234567890.123
}

# Quorum Read
GET /kv/{key}
```

### 2. Causal Consistency

**Characteristics:**
- Preserves cause-effect relationships
- Vector clock-based ordering
- Stronger than eventual consistency
- Handles data dependencies

**Use Cases:**
- Social media platforms (user profile → posts)
- E-commerce (order → order history)
- Any scenario with data dependencies

**Implementation:**
```python
# Causal Write
PUT /causal/kv/{key}
{
  "value": "data",
  "vector_clock": {"node-1": 5, "node-2": 3}
}

# Causal Read
GET /causal/kv/{key}
```

## Conflict Resolution Strategies

### 1. Last-Write-Wins (LWW) - Quorum Operations

**Strategy:** Resolve conflicts based on timestamps
- Higher timestamp wins
- Deterministic resolution
- Suitable for time-sensitive data

**Implementation:**
```python
def handle_get_key(self, key: str) -> dict:
    # Collect responses from all responsible nodes
    collection_result = self._collect_responses_from_nodes(key)
    responses = collection_result["responses"]
    timestamps = collection_result["timestamps"]
    
    if len(unique_values) > 1:
        # Conflict detected - use LWW
        latest_timestamp = max(timestamps.values())
        resolved_value = responses[node_with_latest_timestamp]
        
        return {
            "consistency_level": "quorum_resolved",
            "conflict_resolution": {
                "strategy": "last_write_wins",
                "resolved_value": resolved_value,
                "resolved_timestamp": latest_timestamp
            }
        }
```

### 2. Vector Clock Ordering - Causal Operations

**Strategy:** Resolve conflicts based on vector clock relationships
- Causal ordering preserved
- Handles concurrent writes
- Maintains data dependencies

**Implementation:**
```python
def put_causal(self, key: str, value: str, external_clock=None):
    # Increment local vector clock
    self.vector_clock.increment(self.node_id)
    
    # Merge with external clock if provided
    if external_clock:
        self.vector_clock.merge(external_clock)
    
    # Store with vector clock
    causal_value = CausalVersionedValue(
        value=value,
        vector_clock=self.vector_clock.copy(),
        node_id=self.node_id
    )
```

## Implementation Details

### Quorum Read with Timestamp-Based Conflict Resolution

**Enhanced Collection Process:**
```python
def _collect_responses_from_nodes(self, key: str) -> dict:
    responses = {}
    timestamps = {}  # Store timestamps for conflict resolution
    
    for node in responsible_nodes:
        if node == self.address:
            # Local read with timestamp
            local_value = self.local_data.get(key)
            if local_value is not None:
                responses[node] = local_value
                timestamps[node] = self.persistence.get_timestamp(key)
        else:
            # Remote read with timestamp
            response = requests.get(f"http://{node}/kv/{key}/direct")
            if response.status_code == 200:
                data = response.json()
                responses[node] = data['value']
                timestamps[node] = data.get('timestamp', time.time())
    
    return {"responses": responses, "timestamps": timestamps}
```

**Conflict Resolution Logic:**
```python
def handle_get_key(self, key: str) -> dict:
    # Check quorum
    if len(responses) >= required:
        unique_values = set(responses.values())
        
        if len(unique_values) == 1:
            # Consistent values
            return {"consistency_level": "quorum_consistent"}
        else:
            # Inconsistent values - resolve using LWW
            latest_timestamp = max(timestamps.values())
            resolved_value = None
            resolved_node = None
            
            for node, timestamp in timestamps.items():
                if timestamp == latest_timestamp:
                    resolved_value = responses[node]
                    resolved_node = node
                    break
            
            return {
                "consistency_level": "quorum_resolved",
                "conflict_resolution": {
                    "strategy": "last_write_wins",
                    "resolved_value": resolved_value,
                    "resolved_node": resolved_node,
                    "resolved_timestamp": latest_timestamp,
                    "all_responses": responses,
                    "all_timestamps": timestamps
                }
            }
```

### Causal Consistency Implementation

**Vector Clock Management:**
```python
class VectorClock:
    def __init__(self, clocks=None):
        self.clocks = clocks or {}
    
    def increment(self, node_id):
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1
    
    def merge(self, other_clock):
        for node_id, counter in other_clock.clocks.items():
            self.clocks[node_id] = max(
                self.clocks.get(node_id, 0), 
                counter
            )
```

**Causal Write Process:**
```python
def put_causal(self, key: str, value: str, external_clock=None):
    # Increment local vector clock
    self.vector_clock.increment(self.node_id)
    
    # Merge with external clock if provided
    if external_clock:
        self.vector_clock.merge(external_clock)
    
    # Store causal value
    causal_value = CausalVersionedValue(
        value=value,
        vector_clock=self.vector_clock.copy(),
        node_id=self.node_id,
        creation_time=time.time()
    )
    
    self.causal_data[key] = causal_value
    return True
```

## Business Scenarios

### Scenario 1: Social Media Platform

**Problem:** User updates profile picture → Creates post about it

**Without Causal Consistency:**
```
Timeline:
1. User updates profile picture (quorum write)
2. User creates post "Check out my new profile pic!" (quorum write)
3. Another user reads the post → might see OLD profile picture
```

**With Causal Consistency:**
```python
# 1. Profile Update (Causal Write)
PUT /causal/kv/user:123:profile
{
  "value": "new_pic_url.jpg",
  "vector_clock": {"node-1": 5, "node-2": 3}
}

# 2. Post Creation (Causal Write with Dependency)
PUT /causal/kv/user:123:post:456
{
  "value": "Check out my new profile pic!",
  "vector_clock": {"node-1": 6, "node-2": 3}  # Incremented from profile update
}

# 3. Causal Read (Guarantees Order)
GET /causal/kv/user:123:post:456
# System ensures: if you read the post, you MUST see the updated profile
```

**Result:** User always sees consistent state - post + updated profile picture together.

### Scenario 2: E-commerce Order Processing

**Problem:** Order placement → Order history update

**Without Causal Consistency:**
```
Timeline:
1. User places order (quorum write)
2. Order history updated (quorum write)
3. User checks order status → might see order but not in history
```

**With Causal Consistency:**
```python
# 1. Order Placement (Causal Write)
PUT /causal/kv/order:456
{
  "value": "{\"status\": \"placed\", \"items\": [...]}",
  "vector_clock": {"node-1": 10, "node-2": 5}
}

# 2. Order History Update (Causal Write)
PUT /causal/kv/user:123:orders
{
  "value": "{\"orders\": [..., {\"id\": 456, \"status\": \"placed\"}]}",
  "vector_clock": {"node-1": 11, "node-2": 5}  # Incremented from order
}

# 3. Causal Read (Guarantees Consistency)
GET /causal/kv/user:123:orders
# System ensures: if you see the order in history, you MUST see the order details
```

## Usage Guidelines

### When to Use Quorum Consistency

**✅ Use for:**
- Time-sensitive data (logs, metrics, analytics)
- High availability requirements
- Data where eventual consistency is acceptable
- Simple key-value operations
- Performance-critical applications

**❌ Avoid for:**
- Data with dependencies
- Business-critical transactions
- Scenarios requiring strong consistency

### When to Use Causal Consistency

**✅ Use for:**
- Data with dependencies (user profile → posts)
- Social media applications
- E-commerce order processing
- Any scenario where cause-effect relationships matter
- Applications requiring stronger consistency than eventual

**❌ Avoid for:**
- Simple key-value operations
- Performance-critical applications
- Data without dependencies

### Read Repair Strategy

**Always implement read repair for:**
- Automatic background synchronization (anti-entropy)
- Asynchronous replication after quorum writes
- Conflict resolution during reads
- Data consistency maintenance

## API Reference

### Quorum Operations

#### PUT /kv/{key} - Quorum Write
```bash
curl -X PUT http://localhost:8080/kv/mykey \
  -H "Content-Type: application/json" \
  -d '{"value": "myvalue"}'
```

**Response:**
```json
{
  "key": "mykey",
  "value": "myvalue",
  "coordinator": "localhost:8080",
  "quorum_achieved": true,
  "replicas_written": 2,
  "total_replicas": 3
}
```

#### GET /kv/{key} - Quorum Read
```bash
curl http://localhost:8080/kv/mykey
```

**Response (Consistent):**
```json
{
  "key": "mykey",
  "value": "myvalue",
  "consistency_level": "quorum_consistent",
  "coordinator": "localhost:8080",
  "replicas_responded": 3,
  "total_replicas": 3
}
```

**Response (Conflict Resolved):**
```json
{
  "key": "mykey",
  "value": "resolved_value",
  "consistency_level": "quorum_resolved",
  "conflict_resolution": {
    "strategy": "last_write_wins",
    "resolved_value": "resolved_value",
    "resolved_node": "localhost:8081",
    "resolved_timestamp": 1234567890.123,
    "all_responses": {
      "localhost:8080": "value1",
      "localhost:8081": "resolved_value",
      "localhost:8082": "value2"
    },
    "all_timestamps": {
      "localhost:8080": 1234567890.100,
      "localhost:8081": 1234567890.123,
      "localhost:8082": 1234567890.110
    },
    "conflicts_detected": 3
  }
}
```

### Causal Operations

#### PUT /causal/kv/{key} - Causal Write
```bash
curl -X PUT http://localhost:8080/causal/kv/mykey \
  -H "Content-Type: application/json" \
  -d '{"value": "myvalue", "vector_clock": {"node-1": 5, "node-2": 3}}'
```

**Response:**
```json
{
  "key": "mykey",
  "value": "myvalue",
  "vector_clock": {"node-1": 6, "node-2": 3},
  "node_id": "node-1",
  "causal_operation": true
}
```

#### GET /causal/kv/{key} - Causal Read
```bash
curl http://localhost:8080/causal/kv/mykey
```

**Response:**
```json
{
  "key": "mykey",
  "value": "myvalue",
  "vector_clock": {"node-1": 6, "node-2": 3},
  "node_id": "node-1",
  "creation_time": 1234567890.123,
  "causal_operation": true
}
```

## Testing

### Running the Timestamp-Based Conflict Resolution Test

```bash
python -m pytest distributed/node.py::TestRobustSimpleGossip::test_quorum_read_timestamp_conflict_resolution -v -s
```

**Test Coverage:**
- ✅ Cluster formation with 3 nodes
- ✅ Writing different values with different timestamps
- ✅ Conflict detection during quorum read
- ✅ LWW conflict resolution
- ✅ Verification of resolved value and timestamp

### Expected Test Output

```
✅ Quorum read with conflict resolution test passed
   Response data: {...}
   Resolved value: value3
   Consistency level: quorum_resolved
   Conflict resolution: last_write_wins
   ✅ Conflict resolution verified: value3 from localhost:51050 (timestamp: 1752999508.041265)
```

## Conclusion

This implementation provides a robust distributed key-value store with:

1. **Quorum Consistency** with timestamp-based LWW conflict resolution
2. **Causal Consistency** with vector clock ordering
3. **Automatic read repair** through anti-entropy and async replication
4. **Comprehensive conflict resolution** strategies
5. **Production-ready** implementation with detailed metadata

Choose the appropriate consistency model based on your data characteristics and business requirements. 