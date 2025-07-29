# Hash Ring APIs - Quick Reference

## 🚀 Quick Start

### Basic Usage Examples

```bash
# 1. Get virtual node details
curl http://localhost:8080/ring/virtual-nodes

# 2. Analyze key distribution (1000 sample keys)
curl http://localhost:8080/ring/key-distribution

# 3. Analyze key migration after cluster changes
curl http://localhost:8080/ring/migration-analysis

# 4. Reset migration tracking for new baseline
curl -X POST http://localhost:8080/ring/reset-migration-tracking
```

## 📊 API Reference

### Virtual Node Details
```bash
GET /ring/virtual-nodes
```
**Use case**: Understand how virtual nodes are distributed across physical nodes

### Key Distribution Analysis
```bash
GET /ring/key-distribution?keys=key1,key2,key3&sample_size=500
```
**Use case**: Check load balancing and key distribution across nodes

### Migration Analysis
```bash
GET /ring/migration-analysis?sample_size=1000
```
**Use case**: Track key movement when nodes are added/removed

### Reset Migration Tracking
```bash
POST /ring/reset-migration-tracking
```
**Use case**: Establish new baseline before cluster changes

## 🔄 Common Workflows

### 1. Cluster Expansion Planning
```bash
# Step 1: Get current state
curl http://localhost:8080/ring/key-distribution

# Step 2: Reset tracking
curl -X POST http://localhost:8080/ring/reset-migration-tracking

# Step 3: Add new node (via join API)
curl -X POST http://localhost:8080/join -d '{"peer_address": "127.0.0.1:8083"}'

# Step 4: Analyze impact
curl http://localhost:8080/ring/migration-analysis
```

### 2. Node Failure Impact Assessment
```bash
# Analyze migration after node removal
curl http://localhost:8080/ring/migration-analysis?sample_size=1000

# Check load on remaining nodes
curl http://localhost:8080/ring/key-distribution
```

### 3. Load Balancing Verification
```bash
# Check physical node distribution
curl http://localhost:8080/ring/key-distribution | jq '.physical_node_distribution'

# Check virtual node distribution
curl http://localhost:8080/ring/key-distribution | jq '.virtual_node_distribution'
```

## 📈 Expected Results

### Virtual Node Details
```json
{
  "virtual_nodes": 450,
  "virtual_nodes_per_physical": 150,
  "node_count": 3,
  "replication_factor": 3
}
```

### Key Distribution (Good Balance)
```json
{
  "physical_node_distribution": {
    "127.0.0.1:8080": 334,
    "127.0.0.1:8081": 333,
    "127.0.0.1:8082": 333
  }
}
```

### Migration Analysis (Typical)
```json
{
  "migration_summary": {
    "keys_migrated": 21,
    "migration_percentage": 21.0,
    "keys_unchanged": 79
  }
}
```

## ⚡ Performance Tips

### Sample Size Guidelines
- **Demo/Testing**: 100 keys (fast)
- **Production Analysis**: 1000 keys (balanced)
- **Deep Analysis**: 10000+ keys (accurate but slow)

### Caching Strategy
- Virtual node details are cached
- Key distribution is computed on-demand
- Migration analysis requires baseline

## 🚨 Troubleshooting

### Common Issues

1. **"Hash ring not initialized"**
   ```bash
   # Check if nodes are joined
   curl http://localhost:8080/peers
   ```

2. **No migration detected**
   ```bash
   # Reset tracking first
   curl -X POST http://localhost:8080/ring/reset-migration-tracking
   ```

3. **High migration percentage (>50%)**
   - Check for network partitions
   - Verify peer list consistency
   - Review cluster topology

### Debug Commands
```bash
# Check ring state
curl http://localhost:8080/ring

# Verify peers
curl http://localhost:8080/peers

# Check health
curl http://localhost:8080/health
```

## 📋 Best Practices

1. **Always reset migration tracking before cluster changes**
2. **Use appropriate sample sizes for your use case**
3. **Monitor migration percentages (should be <50%)**
4. **Verify even key distribution across nodes**
5. **Track migration patterns over time**

## 🔗 Related APIs

- `GET /ring` - Basic ring information
- `GET /peers` - Current peer list
- `GET /health` - Node health status
- `POST /join` - Add node to cluster
- `POST /remove_peer` - Remove node from cluster

## 📚 Full Documentation

For detailed information, see [Hash Ring APIs Guide](HASH_RING_APIS.md) 