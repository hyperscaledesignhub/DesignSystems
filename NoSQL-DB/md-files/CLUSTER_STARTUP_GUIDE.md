# Cluster Startup Guide

This directory contains two different ways to start the distributed database cluster:

## 1. Local Development (start-cluster.sh)

**Use this for:**
- Local development and testing
- Running on your local machine
- Quick testing without Kubernetes

**How to use:**
```bash
./start-cluster.sh
```

**What it does:**
- Starts 3 Python processes locally
- Uses ports from `config.yaml`
- Creates local data directories
- Runs in foreground (Ctrl+C to stop)

## 2. Kubernetes Deployment (start-cluster-k8s.sh)

**Use this for:**
- Production-like deployment
- Kubernetes testing
- Containerized deployment

**How to use:**
```bash
# Full deployment (build + deploy)
./start-cluster-k8s.sh full

# Deploy existing image only
./start-cluster-k8s.sh deploy-only

# Check status
./start-cluster-k8s.sh status

# View logs
./start-cluster-k8s.sh logs

# Cleanup
./start-cluster-k8s.sh cleanup
```

**What it does:**
- Builds Docker image
- Creates Kind Kubernetes cluster
- Deploys to Kubernetes
- Manages pods, services, and StatefulSets

## Which One Should You Use?

### For Local Development:
```bash
./start-cluster.sh
```

### For Kubernetes Testing:
```bash
./start-cluster-k8s.sh full
```

### For Quick Kubernetes Status Check:
```bash
./start-cluster-k8s.sh status
```

## Troubleshooting

### If start-cluster.sh tries to start locally when you want Kubernetes:
- Use `start-cluster-k8s.sh` instead
- The original `start-cluster.sh` is designed for local development only

### If you get permission errors:
```bash
chmod +x start-cluster.sh start-cluster-k8s.sh
```

### If Kubernetes pods aren't starting:
```bash
./start-cluster-k8s.sh logs
```

## Additional Scripts

- `build-and-deploy.sh` - Raw Kubernetes deployment script
- `run-in-pod.sh` - Run scripts inside Kubernetes pods
- `pod-verify.sh` - Verify cluster functionality from inside a pod 