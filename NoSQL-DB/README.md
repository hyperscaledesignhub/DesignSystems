# Distributed Key-Value Database

A production-ready distributed key-value database implementation with advanced features including replication, anti-entropy synchronization, causal consistency, and vector clocks.

## 🚀 Features

- **Distributed Architecture**: Multi-node cluster with gossip protocol
- **Replication**: Automatic data replication across nodes
- **Anti-Entropy**: Merkle tree-based synchronization
- **Causal Consistency**: Vector clock implementation
- **Persistence**: SSTable and commit log storage
- **Health Monitoring**: Built-in health checks and monitoring
- **Kubernetes Ready**: Full Kubernetes deployment support

## 📁 Project Structure

```
├── distributed/           # Core application code
│   ├── lib/              # Shared libraries
│   └── node.py           # Main node implementation
├── demo/                 # Testing and demonstration scripts
├── scripts/              # DevOps and deployment automation
├── yaml/                 # Kubernetes manifests
├── k8s/                  # Kubernetes-specific resources
├── docs/                 # Documentation
└── config/               # Configuration files
```

## 🛠️ Quick Start

### Local Development
```bash
# Start local cluster
./scripts/start-cluster-local.sh

# Run demos
python demo/cluster_demo_runner_local.py vector_clock_db --config config/config.yaml
```

### Kubernetes Deployment
```bash
# Deploy to Kind cluster
./scripts/build-and-deploy.sh full
```

## 📚 Documentation

- [Cluster Startup Guide](md-files/CLUSTER_STARTUP_GUIDE.md)
- [Demo Guide](md-files/DEMO_GUIDE.md)
- [Anti-Entropy Guide](md-files/ANTI_ENTROPY_GUIDE.md)
- [Causal Consistency Guide](md-files/CAUSAL_CONSISTENCY_GUIDE.md)

## 🔧 Development

### Prerequisites
- Python 3.8+
- Docker
- Kubernetes (Kind)

### Setup
```bash
pip install -r requirements.txt
```

### Testing
```bash
# Run all demos
python demo/cluster_demo_runner.py --all

# Test specific features
python demo/cluster_demo_runner.py vector_clock_db
python demo/cluster_demo_runner.py anti_entropy
python demo/cluster_demo_runner.py replication
```

## 📊 Monitoring

- Health endpoint: `http://localhost:8080/health`
- Cluster info: `http://localhost:8080/info`
- Dashboard: `http://localhost:8080/dashboard`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. 