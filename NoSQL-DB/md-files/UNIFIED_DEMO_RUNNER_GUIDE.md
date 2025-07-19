# Unified Demo Runner Guide

This guide explains how to use the unified demo runner to execute cluster-based demos with both existing and new clusters.

## Overview

The `cluster_demo_runner.py` provides a unified interface to run demos on:
1. **Existing clusters** - Use nodes already running (specified in config)
2. **New clusters** - Create nodes as needed for the demo

## Quick Start

### Basic Usage

```bash
# Run demo with new cluster (default)
python cluster_demo_runner.py <demo_name> --config <config_file>

# Run demo with existing cluster
python cluster_demo_runner.py <demo_name> --config <config_file> --use-existing
```

### Examples

```bash
# Vector clock demo with new local cluster
python cluster_demo_runner.py vector_clock_db --config config-local.yaml

# Convergence test with existing cluster
python cluster_demo_runner.py convergence --config config-local.yaml --use-existing

# Anti-entropy demo with new cluster
python cluster_demo_runner.py anti_entropy --config config-local.yaml

# Kubernetes demo with existing cluster
python cluster_demo_runner.py consistent_hashing --config config.yaml --use-existing
```

## Available Demos

| Demo Name | Description | File |
|-----------|-------------|------|
| `vector_clock_db` | Vector clock behavior in distributed DB | `vector_clock_db_demo.py` |
| `convergence` | Multi-node convergence test | `convergence_test.py` |
| `anti_entropy` | Anti-entropy mechanism demo | `working_anti_entropy_demo.py` |
| `automated_anti_entropy` | Automated anti-entropy testing | `automated_anti_entropy_demo.py` |
| `consistent_hashing` | Consistent hashing demo | `consistent_hashing_demo.py` |
| `replication` | Data replication demo | `replication_demo.py` |
| `quick` | Quick cluster functionality demo | `quick_demo.py` |
| `persistence_anti_entropy` | Persistence + anti-entropy demo | `demo_persistence_anti_entropy.py` |

## Configuration Files

### Local Configuration (`config-local.yaml`)

```yaml
local:
  base_port: 9999
  node_count: 3
  data_dir: "./data"
  gossip_interval: 5.0
  anti_entropy_interval: 30.0

nodes:
  - id: "db-node-1"
    host: "localhost"
    port: 9999
  - id: "db-node-2"
    host: "localhost"
    port: 10000
  - id: "db-node-3"
    host: "localhost"
    port: 10001
```

### Kubernetes Configuration (`config.yaml`)

```yaml
kubernetes:
  service_name: "kvdb-service"
  namespace: "default"
  replicas: 3
  image: "kvdb:latest"
  ports:
    - containerPort: 9999
      name: "api"
    - containerPort: 10000
      name: "gossip"

nodes:
  - id: "kvdb-service-0"
    host: "kvdb-service-0.kvdb-service.default.svc.cluster.local"
    port: 9999
  - id: "kvdb-service-1"
    host: "kvdb-service-1.kvdb-service.default.svc.cluster.local"
    port: 9999
  - id: "kvdb-service-2"
    host: "kvdb-service-2.kvdb-service.default.svc.cluster.local"
    port: 9999
```

## Usage Modes

### 1. New Cluster Mode (Default)

Creates a fresh cluster for the demo:

```bash
python cluster_demo_runner.py vector_clock_db --config config-local.yaml
```

**What happens:**
1. Loads configuration from `config-local.yaml`
2. Starts new nodes based on config
3. Forms cluster by joining nodes
4. Runs the demo
5. Cleans up created nodes

### 2. Existing Cluster Mode

Uses nodes already running:

```bash
python cluster_demo_runner.py convergence --config config-local.yaml --use-existing
```

**What happens:**
1. Loads configuration from `config-local.yaml`
2. Discovers existing nodes from config
3. Verifies nodes are reachable
4. Runs the demo
5. Leaves existing nodes running

## Environment Variables

The runner sets these environment variables for demos:

- `CLUSTER_NODES`: Comma-separated list of node addresses
- `CLUSTER_CONFIG`: Path to the configuration file

## Demo Base Class

Demos can inherit from `ClusterDemoBase` to get unified cluster management:

```python
from demo_base import ClusterDemoBase

class MyDemo(ClusterDemoBase):
    def run_demo(self) -> bool:
        # Your demo logic here
        # Access self.nodes for cluster information
        return True

if __name__ == "__main__":
    demo = MyDemo()
    demo.run(use_existing=True)  # Use existing cluster
```

## Error Handling

The runner includes robust error handling:

- **Node startup failures**: Retries and graceful cleanup
- **Network issues**: Retry logic for API calls
- **Cluster formation**: Handles partial cluster scenarios
- **Demo failures**: Proper cleanup of created resources

## Troubleshooting

### Common Issues

1. **"No existing nodes found in config"**
   - Check your config file format
   - Ensure nodes are properly defined

2. **"Existing cluster verification failed"**
   - Verify nodes are actually running
   - Check network connectivity
   - Ensure correct ports are specified

3. **"Failed to start new cluster"**
   - Check if ports are already in use
   - Verify `node.py` exists
   - Check Python environment

### Debug Mode

Add debug output by setting environment variable:

```bash
DEBUG=1 python cluster_demo_runner.py vector_clock_db --config config-local.yaml
```

## Advanced Usage

### Custom Node Configuration

You can specify custom node configurations:

```yaml
nodes:
  - id: "custom-node-1"
    host: "192.168.1.100"
    port: 9999
  - id: "custom-node-2"
    host: "192.168.1.101"
    port: 9999
```

### Multiple Configurations

Use different configs for different environments:

```bash
# Local development
python cluster_demo_runner.py vector_clock_db --config config-local.yaml

# Kubernetes
python cluster_demo_runner.py vector_clock_db --config config-k8s.yaml

# Production
python cluster_demo_runner.py vector_clock_db --config config-prod.yaml
```

## Integration with CI/CD

The runner can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Demo Tests
  run: |
    python cluster_demo_runner.py convergence --config config-local.yaml
    python cluster_demo_runner.py anti_entropy --config config-local.yaml
```

## Best Practices

1. **Use existing clusters** for development to avoid startup overhead
2. **Use new clusters** for testing to ensure clean state
3. **Always specify config file** to avoid confusion
4. **Check node health** before running demos
5. **Clean up resources** after demo completion

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review configuration file format
3. Verify network connectivity
4. Check logs for detailed error messages 