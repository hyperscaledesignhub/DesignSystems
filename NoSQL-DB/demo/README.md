# NoSQL-DB Real-World Demos

This directory contains demonstrations of distributed database concepts mapped to real-world use cases. Each demo showcases specific features of the NoSQL-DB system with practical applications.

## 🎯 Quick Start

### Prerequisites
- Python 3.8+
- Running NoSQL-DB cluster (3 nodes recommended)
- Required Python packages: `requests`, `pyyaml`

### Running a Demo
```bash
# Start with existing cluster
export CLUSTER_NODES="localhost:8000,localhost:8001,localhost:8002"
python demo_name.py

# Or let the demo start a cluster for you
python demo_name.py
```

## 📚 Real-World Use Cases

### 1. 🐦 Twitter-like Social Media Platform
**Demo:** `twitter_counter_demo.py`  
**Original:** `replication_demo.py`

**Features Demonstrated:**
- Distributed counters for likes, retweets, followers
- High-traffic handling with eventual consistency
- Quorum-based reads for consistency
- Real-time replication status monitoring

**Real-World Application:**
- Social media engagement metrics
- View counts for videos/posts
- Follower/following counts
- Real-time trending calculations

**Run Demo:**
```bash
python twitter_counter_demo.py
```

### 2. 📝 Collaborative Document Editor
**Demo:** `collaborative_editor_demo.py`  
**Original:** `vector_clock_db_demo.py`

**Features Demonstrated:**
- Causal consistency with vector clocks
- Concurrent edit detection and resolution
- Node failure handling
- Edit history preservation

**Real-World Application:**
- Google Docs-style collaboration
- Multi-user code editors
- Shared whiteboards
- Collaborative spreadsheets

**Run Demo:**
```bash
python collaborative_editor_demo.py
```

### 3. 🌐 Content Delivery Network (CDN)
**Demo:** `consistent_hashing_demo.py`

**Features Demonstrated:**
- Consistent hashing for content distribution
- Load balancing across nodes
- Minimal redistribution on node changes
- Geographic content routing

**Real-World Application:**
- Video streaming services
- Static asset distribution
- Edge computing
- Distributed caching

**Run Demo:**
```bash
python consistent_hashing_demo.py
```

### 4. 📦 E-commerce Inventory Management
**Demo:** `automated_anti_entropy_demo.py`

**Features Demonstrated:**
- Anti-entropy synchronization
- Merkle tree-based inconsistency detection
- Automatic conflict resolution
- Multi-warehouse coordination

**Real-World Application:**
- Inventory tracking across warehouses
- Stock level synchronization
- Order fulfillment systems
- Supply chain management

**Run Demo:**
```bash
python automated_anti_entropy_demo.py
```

## 🎨 UI-Enabled Demos

The `REAL_WORLD_USE_CASES.md` file contains detailed UI mockups and implementation plans for web-based interfaces. These include:

- Real-time dashboards
- Interactive visualizations
- WebSocket-based live updates
- D3.js hash ring visualizations

## 🧪 Testing & Development

### Running All Demos
```bash
python professional_test_runner.py
```

### Creating New Demos

1. Import demo utilities:
```python
from demo_utils import DemoLogger, ensure_cluster_running
```

2. Structure your demo:
```python
class YourDemo:
    def __init__(self, cluster_nodes=None):
        self.logger = DemoLogger("your_demo")
        self.cluster_nodes = cluster_nodes or []
    
    def run_demo(self):
        # Your demo logic here
        pass
```

3. Map to real-world use case with clear scenarios

## 📊 Demo Features

| Demo | Replication | Consistency | Partitioning | Failure Handling | Anti-Entropy |
|------|-------------|-------------|--------------|------------------|--------------|
| Twitter Counter | ✅ | Eventual | ✅ | ✅ | ✅ |
| Collaborative Editor | ✅ | Causal | ✅ | ✅ | ✅ |
| CDN | ✅ | Eventual | ✅ | ✅ | ❌ |
| Inventory | ✅ | Eventual | ✅ | ✅ | ✅ |

## 🚀 Advanced Features

### Node Failure Simulation
Most demos include node failure scenarios to demonstrate:
- Data preservation during failures
- Automatic recovery mechanisms
- Consistency maintenance
- Client failover

### Performance Metrics
Demos can show:
- Replication lag
- Convergence time
- Throughput statistics
- Consistency violations

## 📝 Configuration

### Environment Variables
- `CLUSTER_NODES`: Comma-separated list of node addresses
- `REPLICATION_FACTOR`: Number of replicas (default: 3)
- `CONSISTENCY_LEVEL`: Read/write consistency level

### Cluster Configuration
Create `cluster_config.yaml`:
```yaml
cluster:
  seed_nodes:
    - id: node-1
      host: localhost
      http_port: 8000
    - id: node-2
      host: localhost
      http_port: 8001
    - id: node-3
      host: localhost
      http_port: 8002
```

## 🔍 Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure cluster nodes are running
   - Check firewall settings
   - Verify port availability

2. **Inconsistent Data**
   - Allow time for anti-entropy convergence
   - Check network connectivity between nodes
   - Verify replication factor settings

3. **Demo Hangs**
   - Check node health endpoints
   - Verify cluster formation
   - Review logs in `demo/logs/`

## 📚 Further Reading

- [Distributed Database Concepts](../docs/DISTRIBUTED_CONCEPTS.md)
- [API Documentation](../docs/API.md)
- [Cluster Setup Guide](../CLUSTER_STARTUP_GUIDE.md)

## 🤝 Contributing

To add new real-world demos:
1. Identify a practical use case
2. Map distributed concepts to business needs
3. Create engaging visualizations
4. Document thoroughly
5. Submit PR with tests

---

For questions or issues, please refer to the main project documentation or create an issue in the repository.