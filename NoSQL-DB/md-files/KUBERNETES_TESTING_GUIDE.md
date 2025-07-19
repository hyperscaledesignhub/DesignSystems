# Kubernetes Testing Guide for Distributed Database

This guide provides comprehensive instructions for testing the distributed database in Kubernetes using the `k8s-testing-commands.sh` script.

## Quick Start

```bash
# Make sure you're in the deployment directory
cd final-product/level-2/deployment/stable-4

# Deploy everything (cluster + test pod)
./k8s-testing-commands.sh deploy

# Check status
./k8s-testing-commands.sh status

# Run a demo
./k8s-testing-commands.sh automated-ae
```

## Available Commands

### Deployment Commands

| Command | Description |
|---------|-------------|
| `deploy` | Deploy the full cluster with test pod |
| `deploy-test` | Deploy only the test pod (rebuilds image) |
| `cleanup` | Clean up all resources |

### Status and Monitoring Commands

| Command | Description |
|---------|-------------|
| `status` | Show cluster and pod status |
| `logs` | Show logs from database pods |
| `test-logs` | Show logs from test pod |
| `exec-test` | Execute bash in test pod |

### Network Commands

| Command | Description |
|---------|-------------|
| `port-forward` | Start port-forward to cluster (port 8081) |
| `stop-port-forward` | Stop port-forward |

### Demo Commands

| Command | Description |
|---------|-------------|
| `vector-clock` | Run vector clock demo |
| `replication` | Run replication demo |
| `anti-entropy` | Run anti-entropy demo |
| `consistent-hashing` | Run consistent hashing demo |
| `persistence` | Run persistence with anti-entropy demo |
| `convergence` | Run convergence demo |
| `automated-ae` | Run automated anti-entropy demo |

### Testing Commands

| Command | Description |
|---------|-------------|
| `test-connectivity` | Test cluster connectivity |
| `test-merkle` | Test Merkle snapshots |
| `test-anti-entropy` | Test anti-entropy trigger |

## Step-by-Step Testing Workflow

### 1. Initial Setup

```bash
# Deploy the complete cluster
./k8s-testing-commands.sh deploy

# Verify deployment
./k8s-testing-commands.sh status
```

### 2. Verify Cluster Health

```bash
# Check all pods are running
./k8s-testing-commands.sh status

# Test connectivity between nodes
./k8s-testing-commands.sh test-connectivity

# Check database logs
./k8s-testing-commands.sh logs
```

### 3. Run Demos

```bash
# Run automated anti-entropy demo (recommended first)
./k8s-testing-commands.sh automated-ae

# Run other demos
./k8s-testing-commands.sh vector-clock
./k8s-testing-commands.sh replication
./k8s-testing-commands.sh anti-entropy
./k8s-testing-commands.sh consistent-hashing
./k8s-testing-commands.sh persistence
./k8s-testing-commands.sh convergence
```

### 4. Interactive Testing

```bash
# Get into the test pod for interactive testing
./k8s-testing-commands.sh exec-test

# Inside the pod, you can run:
# python cluster_demo_runner.py --help
# python automated_anti_entropy_demo.py
# curl http://distributed-database-0.db-headless-service.distributed-db.svc.cluster.local:8080/health
```

### 5. External Access (Optional)

```bash
# Start port-forward to access cluster from local machine
./k8s-testing-commands.sh port-forward

# Now you can access the cluster at http://localhost:8081
# Stop port-forward when done
./k8s-testing-commands.sh stop-port-forward
```

## Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   ./k8s-testing-commands.sh status
   ./k8s-testing-commands.sh logs
   ```

2. **Test pod not updated**
   ```bash
   ./k8s-testing-commands.sh deploy-test
   ```

3. **Network connectivity issues**
   ```bash
   ./k8s-testing-commands.sh test-connectivity
   ```

4. **Demo failures**
   ```bash
   ./k8s-testing-commands.sh test-logs
   ./k8s-testing-commands.sh exec-test
   ```

### Reset Everything

```bash
# Clean up all resources
./k8s-testing-commands.sh cleanup

# Redeploy from scratch
./k8s-testing-commands.sh deploy
```

## Demo Descriptions

### Automated Anti-Entropy Demo
- **Purpose**: Demonstrates automatic data synchronization between nodes
- **Features**: Creates data inconsistencies, triggers anti-entropy, shows Merkle snapshots
- **Expected Result**: 100% synchronization across all nodes

### Vector Clock Demo
- **Purpose**: Shows causal consistency using vector clocks
- **Features**: Concurrent writes, conflict resolution, causal ordering
- **Expected Result**: Proper causal ordering of events

### Replication Demo
- **Purpose**: Demonstrates data replication across nodes
- **Features**: Write replication, read consistency, failure handling
- **Expected Result**: Data replicated to all nodes

### Anti-Entropy Demo
- **Purpose**: Shows manual anti-entropy synchronization
- **Features**: Data inconsistency detection, manual sync triggers
- **Expected Result**: Data convergence after sync

### Consistent Hashing Demo
- **Purpose**: Demonstrates consistent hashing for data distribution
- **Features**: Hash ring visualization, data distribution, node addition/removal
- **Expected Result**: Balanced data distribution

### Persistence Demo
- **Purpose**: Shows data persistence and recovery
- **Features**: Data persistence, anti-entropy with persistence, recovery scenarios
- **Expected Result**: Data survives node restarts

### Convergence Demo
- **Purpose**: Demonstrates eventual consistency
- **Features**: Network partitions, eventual convergence, consistency levels
- **Expected Result**: Eventual data consistency

## Configuration

The cluster uses the following configuration:
- **Namespace**: `distributed-db`
- **Nodes**: 3 StatefulSet pods (`distributed-database-0`, `distributed-database-1`, `distributed-database-2`)
- **Port**: 8080 (internal), 8081 (external via port-forward)
- **Config**: `config.yaml` (loaded into ConfigMap)

## Logs and Debugging

### View Logs
```bash
# Database pod logs
./k8s-testing-commands.sh logs

# Test pod logs
./k8s-testing-commands.sh test-logs

# Specific pod logs
kubectl logs -n distributed-db distributed-database-0
```

### Debug Commands
```bash
# Test connectivity
./k8s-testing-commands.sh test-connectivity

# Test Merkle snapshots
./k8s-testing-commands.sh test-merkle

# Test anti-entropy
./k8s-testing-commands.sh test-anti-entropy
```

## Performance Testing

For performance testing, you can:
1. Use the test pod to run multiple demos
2. Monitor resource usage with `kubectl top pods -n distributed-db`
3. Scale the StatefulSet if needed
4. Use port-forward for external load testing

## Cleanup

When you're done testing:
```bash
# Stop port-forward if running
./k8s-testing-commands.sh stop-port-forward

# Clean up all resources
./k8s-testing-commands.sh cleanup
```

This will remove all pods, services, and the namespace, leaving you with a clean slate for the next testing session. 