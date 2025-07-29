# Asynchronous Write Requests with Different Quorum Values

This document explains how the asynchronous write mechanism works with different quorum configurations.

## 🔧 Core Code Components

### 1. Main Quorum Write Method
```python
def _execute_quorum_write(self, key: str, value: str) -> dict:
    """Execute a quorum-based write operation with optimistic replication"""
    
    # Get responsible nodes (e.g., 3 nodes for replication_factor=3)
    responsible_nodes = self.state.get_responsible_nodes(key)
    
    # Get write quorum from config (e.g., 2 for write_quorum=2)
    write_quorum = quorum_config.get('write_quorum', 2)
    
    success_count = 0
    successful_nodes = []
    remaining_nodes = []
    
    # Step 1: Write to local storage first (fastest)
    self.local_data[key] = str(value)
    success_count += 1
    successful_nodes.append(self.address)
    
    # Step 2: Write to remote nodes until quorum is achieved
    for node in responsible_nodes:
        if node == self.address:
            continue  # Already handled local write
        
        if success_count >= write_quorum:
            # 🎯 QUORUM ACHIEVED! Mark remaining nodes for async replication
            remaining_nodes.append(node)
            continue
        
        # Try to write to this remote node
        if write_successful:
            success_count += 1
            successful_nodes.append(node)
            
            if success_count >= write_quorum:
                print("🎯 Quorum achieved! Returning success immediately")
                # Mark all remaining nodes for async replication
                for remaining_node in responsible_nodes:
                    if remaining_node not in successful_nodes:
                        remaining_nodes.append(remaining_node)
                break  # Exit early - quorum achieved
    
    # Step 3: Start async replication for remaining nodes
    if success_count >= write_quorum:
        self._async_replicate_to_nodes(key, value, remaining_nodes)
        return {"successful_writes": success_count, "async_replication": remaining_nodes}
    else:
        return {"error": "Quorum not reached"}
```

### 2. Asynchronous Replication Method
```python
def _async_replicate_to_nodes(self, key: str, value: str, nodes: List[str]):
    """Asynchronously replicate data to remaining nodes"""
    
    def replicate_worker():
        print(f"🔄 Starting async replication for key '{key}' to {len(nodes)} nodes")
        
        for node in nodes:
            try:
                # Send write request to remaining nodes
                response = requests.put(
                    f"http://{node_address}/kv/{key}/direct",
                    json={"value": value, "timestamp": time.time()},
                    timeout=5  # Longer timeout for async operations
                )
                
                if response.status_code == 200:
                    print(f"✅ Successfully replicated to {node}")
                else:
                    print(f"❌ Failed to replicate to {node}: status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error replicating to {node}: {e}")
        
        print(f"🔄 Completed async replication for key '{key}'")
    
    # Start async replication in background thread
    replication_thread = threading.Thread(target=replicate_worker, daemon=True)
    replication_thread.start()
    print(f"🔄 Started background replication thread for key '{key}'")
```

## 📊 Examples with Different Quorum Values

### Example 1: write_quorum = 2 (Current Config)

**Scenario**: 3-node cluster, write_quorum=2, replication_factor=3

```
Responsible Nodes: [Node1, Node2, Node3]
Write Quorum: 2
```

**Execution Flow**:

```python
# Step 1: Write to local storage (Node1)
success_count = 1
successful_nodes = ["Node1"]

# Step 2: Write to Node2 (succeeds)
success_count = 2
successful_nodes = ["Node1", "Node2"]

# 🎯 QUORUM ACHIEVED! (2 >= 2)
# Return success immediately

# Step 3: Async replication to Node3
remaining_nodes = ["Node3"]
async_replicate_to_nodes(key, value, ["Node3"])
```

**Timeline**:
```
Time 0ms:   Write to Node1 (local) - SUCCESS
Time 5ms:   Write to Node2 - SUCCESS  
Time 5ms:   🎯 QUORUM ACHIEVED! Return success to client
Time 5ms:   Start async replication to Node3
Time 50ms:  Async replication to Node3 - SUCCESS
```

**API Response**:
```json
{
  "key": "my-key",
  "value": "my-value",
  "successful_writes": 2,
  "write_quorum": 2,
  "successful_nodes": ["Node1", "Node2"],
  "async_replication": ["Node3"],
  "optimistic": true
}
```

### Example 2: write_quorum = 3 (Stronger Consistency)

**Scenario**: 3-node cluster, write_quorum=3, replication_factor=3

```
Responsible Nodes: [Node1, Node2, Node3]
Write Quorum: 3
```

**Execution Flow**:

```python
# Step 1: Write to local storage (Node1)
success_count = 1
successful_nodes = ["Node1"]

# Step 2: Write to Node2 (succeeds)
success_count = 2
successful_nodes = ["Node1", "Node2"]

# Step 3: Write to Node3 (succeeds)
success_count = 3
successful_nodes = ["Node1", "Node2", "Node3"]

# 🎯 QUORUM ACHIEVED! (3 >= 3)
# No remaining nodes for async replication

# Step 4: No async replication needed
remaining_nodes = []
```

**Timeline**:
```
Time 0ms:   Write to Node1 (local) - SUCCESS
Time 5ms:   Write to Node2 - SUCCESS  
Time 10ms:  Write to Node3 - SUCCESS
Time 10ms:  🎯 QUORUM ACHIEVED! Return success to client
Time 10ms:  No async replication needed
```

**API Response**:
```json
{
  "key": "my-key",
  "value": "my-value",
  "successful_writes": 3,
  "write_quorum": 3,
  "successful_nodes": ["Node1", "Node2", "Node3"],
  "async_replication": [],
  "optimistic": true
}
```

### Example 3: write_quorum = 1 (Weak Consistency)

**Scenario**: 3-node cluster, write_quorum=1, replication_factor=3

```
Responsible Nodes: [Node1, Node2, Node3]
Write Quorum: 1
```

**Execution Flow**:

```python
# Step 1: Write to local storage (Node1)
success_count = 1
successful_nodes = ["Node1"]

# 🎯 QUORUM ACHIEVED! (1 >= 1)
# Return success immediately

# Step 2: Async replication to Node2 and Node3
remaining_nodes = ["Node2", "Node3"]
async_replicate_to_nodes(key, value, ["Node2", "Node3"])
```

**Timeline**:
```
Time 0ms:   Write to Node1 (local) - SUCCESS
Time 0ms:   🎯 QUORUM ACHIEVED! Return success to client
Time 0ms:   Start async replication to Node2, Node3
Time 45ms:  Async replication to Node2 - SUCCESS
Time 50ms:  Async replication to Node3 - SUCCESS
```

**API Response**:
```json
{
  "key": "my-key",
  "value": "my-value",
  "successful_writes": 1,
  "write_quorum": 1,
  "successful_nodes": ["Node1"],
  "async_replication": ["Node2", "Node3"],
  "optimistic": true
}
```

## 🔄 Async Replication Details

### How Async Replication Works

```python
def _async_replicate_to_nodes(self, key: str, value: str, nodes: List[str]):
    def replicate_worker():
        for node in nodes:
            try:
                # Send direct write request (bypasses quorum)
                response = requests.put(
                    f"http://{node_address}/kv/{key}/direct",
                    json={"value": value, "timestamp": time.time()},
                    timeout=5  # Longer timeout for async operations
                )
                
                if response.status_code == 200:
                    print(f"✅ Successfully replicated to {node}")
                else:
                    print(f"❌ Failed to replicate to {node}")
                    
            except Exception as e:
                print(f"❌ Error replicating to {node}: {e}")
    
    # Start in background thread (non-blocking)
    replication_thread = threading.Thread(target=replicate_worker, daemon=True)
    replication_thread.start()
```

### Key Characteristics

1. **Non-blocking**: Client gets response immediately after quorum
2. **Background thread**: Async replication doesn't block main operations
3. **Longer timeout**: 5 seconds vs 2 seconds for quorum writes
4. **Direct endpoint**: Uses `/kv/<key>/direct` to avoid circular quorum calls
5. **Best effort**: Async replication failures don't affect client response

## 📈 Performance Comparison

| write_quorum | Latency | Consistency | Async Replication |
|-------------|---------|-------------|-------------------|
| 1 | Fastest | Weak | 2 nodes |
| 2 | Fast | Medium | 1 node |
| 3 | Slowest | Strong | 0 nodes |

### Latency Analysis

**write_quorum = 1**:
- Client response: ~0ms (local write only)
- Async replication: ~50ms (2 remote nodes)

**write_quorum = 2**:
- Client response: ~5ms (local + 1 remote)
- Async replication: ~50ms (1 remote node)

**write_quorum = 3**:
- Client response: ~10ms (local + 2 remote)
- Async replication: 0ms (no remaining nodes)

## 🛡️ Failure Scenarios

### Scenario 1: Node Failure During Quorum Write

```
Responsible Nodes: [Node1, Node2, Node3]
Write Quorum: 2

Time 0ms:   Write to Node1 (local) - SUCCESS
Time 5ms:   Write to Node2 - FAILURE (node down)
Time 10ms:  Write to Node3 - SUCCESS
Time 10ms:  🎯 QUORUM ACHIEVED! (Node1 + Node3 = 2)
Time 10ms:  Return success to client
Time 10ms:  Start async replication to Node2 (will fail)
```

### Scenario 2: Insufficient Quorum

```
Responsible Nodes: [Node1, Node2, Node3]
Write Quorum: 2

Time 0ms:   Write to Node1 (local) - SUCCESS
Time 5ms:   Write to Node2 - FAILURE
Time 10ms:  Write to Node3 - FAILURE
Time 10ms:  ❌ QUORUM NOT REACHED (only 1 success, need 2)
Time 10ms:  Return error to client
```

## 🔧 Configuration Examples

### High Availability (Fast Writes)
```yaml
quorum:
  write_quorum: 1  # Fastest response
  read_quorum: 1
```

### Balanced Consistency
```yaml
quorum:
  write_quorum: 2  # Current setting
  read_quorum: 1
```

### Strong Consistency
```yaml
quorum:
  write_quorum: 3  # Strongest consistency
  read_quorum: 2
```

## 🎯 Key Benefits

1. **Optimistic Replication**: Returns success immediately after quorum
2. **Background Processing**: Async replication doesn't block clients
3. **Configurable Consistency**: Adjust quorum levels based on needs
4. **Fault Tolerance**: Handles node failures gracefully
5. **Performance**: Faster response times with async replication

The asynchronous write mechanism provides the best of both worlds: fast client responses and eventual consistency across all nodes! 🚀 