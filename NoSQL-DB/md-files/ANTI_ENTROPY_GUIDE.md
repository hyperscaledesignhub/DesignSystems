# Anti-Entropy Demo Guide

## Quick Reference: How Inconsistencies Are Created

### The Key Difference

**Normal Write (with replication):**
```bash
curl -X PUT http://localhost:9999/kv/user:alice -d '{"value": "alice_data"}'
```
- ✅ Replicates to all nodes
- ✅ All nodes have same data
- ✅ No inconsistencies

**Direct Write (bypasses replication):**
```bash
curl -X PUT http://localhost:9999/kv/user:alice/direct -d '{"value": "alice_data"}'
```
- ❌ Writes to ONE node only
- ❌ Other nodes have different/missing data
- ❌ Creates real inconsistencies

### Demo Inconsistency Creation Process

1. **Write to Node 1 only:**
   ```python
   write_data_direct_to_node("localhost:9999", "user:alice", "alice_data_from_node1")
   ```
   - Node 1: `user:alice = "alice_data_from_node1"`
   - Node 2: `user:alice = NOT_FOUND`
   - Node 3: `user:alice = NOT_FOUND`

2. **Write conflicting data to Node 2 only:**
   ```python
   write_data_direct_to_node("localhost:10000", "user:alice", "alice_data_from_node2_DIFFERENT")
   ```
   - Node 1: `user:alice = "alice_data_from_node1"`
   - Node 2: `user:alice = "alice_data_from_node2_DIFFERENT"` ← CONFLICT!
   - Node 3: `user:alice = NOT_FOUND`

3. **Result: Real Data Inconsistency**
   - Same key has different values on different nodes
   - Anti-entropy will detect this via Merkle tree comparison
   - Anti-entropy will resolve conflicts based on timestamps

### Why This Simulates Real Problems

- **Network partitions**: Nodes can't communicate
- **Node failures**: Replication fails
- **Temporary outages**: Data gets out of sync
- **Split-brain scenarios**: Nodes operate independently

### Anti-Entropy Detection Process

1. **Merkle Tree Creation**: Each node creates hash of its data
2. **Hash Comparison**: Different data = different hashes
3. **Inconsistency Detection**: Anti-entropy sees hash differences
4. **Conflict Resolution**: Newer timestamps win
5. **Data Sync**: Missing data is propagated

### Key Endpoints

| Endpoint | Purpose | Creates Inconsistencies? |
|----------|---------|-------------------------|
| `PUT /kv/{key}` | Normal write with replication | ❌ No |
| `PUT /kv/{key}/direct` | Direct write (no replication) | ✅ Yes |
| `GET /merkle/snapshot` | Get data state hash | - |
| `POST /anti-entropy/trigger` | Manual anti-entropy | - |

### Running the Demo

```bash
cd final-product/level-2/deployment/stable-4
python anti_entropy_demo.py
```

The demo will:
1. Start 3 nodes
2. Create inconsistencies using direct writes
3. Show Merkle tree differences
4. Trigger anti-entropy
5. Show consistency restored

### Expected Output

**Before Anti-Entropy:**
```
Node 1: user:alice = "alice_data_from_node1"
Node 2: user:alice = "alice_data_from_node2_DIFFERENT"
Node 3: user:alice = NOT_FOUND
```

**After Anti-Entropy:**
```
Node 1: user:alice = "alice_data_from_node2_DIFFERENT" (newer wins)
Node 2: user:alice = "alice_data_from_node2_DIFFERENT"
Node 3: user:alice = "alice_data_from_node2_DIFFERENT" (synced)
```

### Key Takeaway

The `/direct` endpoints are the key to creating real inconsistencies in this demo. They bypass the normal replication mechanism, allowing us to simulate real-world scenarios where data gets out of sync between nodes. 