# Deployment Guide - Proximity Service

## 🚀 Deployment Options

### 1. Local Development (Docker Compose)
### 2. Kubernetes (Production)
### 3. Cloud Platforms (AWS/GCP/Azure)

---

## 🐳 Local Development with Docker Compose

### Prerequisites
- Docker 20.10+ and Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 5GB free disk space

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd proximity-service

# Start all services
docker-compose up -d

# Wait for initialization (60 seconds)
sleep 60

# Verify health
curl http://localhost:7891/health
```

### Service URLs
- **API Gateway**: http://localhost:7891
- **Location Service**: http://localhost:8921
- **Business Service**: http://localhost:9823
- **PostgreSQL**: localhost:5832
- **Redis**: localhost:6739

### Production Tuning
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api-gateway:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
  
  location-service:
    deploy:
      replicas: 5
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
```

---

## ☸️ Kubernetes Deployment

### Prerequisites
- Kubernetes 1.20+
- kubectl configured
- 16GB+ cluster capacity
- LoadBalancer or Ingress controller

### 1. Deploy Infrastructure
```bash
# Create namespace
kubectl apply -f deployments/namespace.yaml

# Deploy database and cache
kubectl apply -f deployments/postgres.yaml
kubectl apply -f deployments/redis.yaml

# Wait for database ready
kubectl wait --for=condition=ready pod -l app=postgres-primary -n proximity-service --timeout=300s
```

### 2. Deploy Application Services
```bash
# Deploy business and location services
kubectl apply -f deployments/business-service.yaml
kubectl apply -f deployments/location-service.yaml

# Deploy API gateway
kubectl apply -f deployments/api-gateway.yaml

# Deploy cache warmer
kubectl apply -f deployments/cache-warmer.yaml
```

### 3. Verify Deployment
```bash
# Check all pods
kubectl get pods -n proximity-service

# Check services
kubectl get svc -n proximity-service

# Get external IP
kubectl get svc api-gateway -n proximity-service
```

### 4. Scale Services
```bash
# Scale location service for high load
kubectl scale deployment location-service --replicas=10 -n proximity-service

# Scale API gateway
kubectl scale deployment api-gateway --replicas=5 -n proximity-service
```

### Production Kubernetes Manifests

#### High Availability PostgreSQL
```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
  namespace: proximity-service
spec:
  instances: 3
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      work_mem: "4MB"
  
  bootstrap:
    initdb:
      database: proximity_db
      owner: proximity_user
  
  storage:
    size: 100Gi
    storageClass: fast-ssd
```

#### Redis Cluster
```yaml
apiVersion: redis.redis.opstreelabs.in/v1beta1
kind: RedisCluster
metadata:
  name: redis-cluster
  namespace: proximity-service
spec:
  clusterSize: 6
  persistenceEnabled: true
  redisConfig:
    maxmemory: "2gb"
    maxmemory-policy: "allkeys-lru"
```

### Monitoring Setup
```bash
# Deploy monitoring
kubectl apply -f deployments/monitoring.yaml

# Access Prometheus
kubectl port-forward svc/prometheus 9290:9290 -n proximity-service

# Access Grafana  
kubectl port-forward svc/grafana 3000:3000 -n proximity-service
```

---

## ☁️ Cloud Platform Deployment

### AWS EKS
```bash
# Create EKS cluster
eksctl create cluster --name proximity-service --region us-west-2 --nodes 5

# Configure kubectl
aws eks update-kubeconfig --region us-west-2 --name proximity-service

# Deploy load balancer controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"

# Deploy services
kubectl apply -f deployments/
```

### Google GKE
```bash
# Create GKE cluster
gcloud container clusters create proximity-service \
  --num-nodes=5 \
  --machine-type=e2-standard-4 \
  --region=us-central1

# Get credentials
gcloud container clusters get-credentials proximity-service --region=us-central1

# Deploy services
kubectl apply -f deployments/
```

### Azure AKS
```bash
# Create resource group
az group create --name proximity-service --location eastus

# Create AKS cluster
az aks create --resource-group proximity-service --name proximity-service --node-count 5

# Get credentials
az aks get-credentials --resource-group proximity-service --name proximity-service

# Deploy services
kubectl apply -f deployments/
```

---

## 🔧 Environment Configuration

### Development Environment
```bash
# .env.dev
DATABASE_URL=postgresql://postgres:password@localhost:5832/proximity_db
REDIS_URL=redis://localhost:6739
API_GATEWAY_PORT=7891
LOCATION_SERVICE_PORT=8921
BUSINESS_SERVICE_PORT=9823
LOG_LEVEL=DEBUG
RATE_LIMIT=1000
CACHE_TTL=3600
```

### Production Environment
```bash
# .env.prod
DATABASE_URL=postgresql://proximity_user:secure_password@postgres-cluster:5432/proximity_db
REDIS_URL=redis://redis-cluster:6379
API_GATEWAY_PORT=80
LOCATION_SERVICE_PORT=8921
BUSINESS_SERVICE_PORT=9823
LOG_LEVEL=INFO
RATE_LIMIT=10000
CACHE_TTL=86400
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### Kubernetes ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: proximity-config
  namespace: proximity-service
data:
  DATABASE_URL: "postgresql://proximity_user:password@postgres-cluster:5432/proximity_db"
  REDIS_URL: "redis://redis-cluster:6379"
  LOG_LEVEL: "INFO"
  RATE_LIMIT: "10000"
  CACHE_TTL: "86400"
```

---

## 📊 Performance Tuning

### Database Optimization
```sql
-- PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
SELECT pg_reload_conf();
```

### Redis Optimization
```bash
# Redis configuration
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
tcp-keepalive 300
timeout 300
```

### Application Tuning
```python
# Connection pooling
DATABASE_POOL_MIN_SIZE = 10
DATABASE_POOL_MAX_SIZE = 50
REDIS_POOL_MAX_CONNECTIONS = 100

# Caching
GEOHASH_CACHE_TTL = 86400  # 24 hours
BUSINESS_CACHE_TTL = 3600  # 1 hour
NEIGHBOR_CACHE_SIZE = 1000

# Rate limiting
RATE_LIMIT_PER_MINUTE = 10000
BURST_LIMIT = 100
```

---

## 🔐 Security Configuration

### Network Security
```yaml
# Network policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: proximity-network-policy
spec:
  podSelector:
    matchLabels:
      app: proximity-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: api-gateway
    ports:
    - protocol: TCP
      port: 8921
```

### Database Security
```sql
-- Create restricted user
CREATE USER proximity_user WITH PASSWORD 'secure_random_password';
GRANT CONNECT ON DATABASE proximity_db TO proximity_user;
GRANT USAGE ON SCHEMA public TO proximity_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO proximity_user;

-- Enable SSL
ALTER SYSTEM SET ssl = on;
```

### Redis Security
```bash
# Redis ACL
requirepass your_redis_password
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
```

---

## 📈 Scaling Guidelines

### Horizontal Scaling
| Component | Min Replicas | Max Replicas | CPU Trigger | Memory Trigger |
|-----------|--------------|--------------|-------------|----------------|
| API Gateway | 3 | 10 | 70% | 80% |
| Location Service | 5 | 20 | 70% | 80% |
| Business Service | 3 | 10 | 70% | 80% |
| PostgreSQL | 1 | 3 | - | - |
| Redis | 3 | 6 | 70% | 80% |

### Vertical Scaling
```yaml
# Resource requests and limits
resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi
```

### Auto-scaling Configuration
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: location-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: location-service
  minReplicas: 5
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 🔍 Monitoring and Observability

### Metrics Collection
```yaml
# Prometheus configuration
scrape_configs:
  - job_name: 'proximity-services'
    static_configs:
      - targets: 
        - 'api-gateway:7892'
        - 'location-service:8922'
        - 'business-service:9824'
```

### Health Checks
```yaml
# Kubernetes health checks
livenessProbe:
  httpGet:
    path: /health
    port: 8921
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8921
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Log Aggregation
```yaml
# Fluent Bit configuration
[OUTPUT]
    Name es
    Match *
    Host elasticsearch.logging.svc.cluster.local
    Port 9200
    Index proximity-logs
```

---

## 🚨 Disaster Recovery

### Database Backup
```bash
# PostgreSQL backup
pg_dump -h postgres-primary -U postgres proximity_db > backup_$(date +%Y%m%d).sql

# Automated backup script
*/15 * * * * /usr/local/bin/backup-postgres.sh
```

### Redis Persistence
```bash
# Redis backup
redis-cli --rdb dump.rdb
save 900 1
save 300 10
save 60 10000
```

### Cluster Backup
```bash
# Kubernetes backup with Velero
velero backup create proximity-backup --include-namespaces proximity-service
```

---

## 📋 Deployment Checklist

### Pre-deployment
- [ ] Resource requirements met
- [ ] Environment variables configured
- [ ] SSL certificates ready
- [ ] Database migration scripts prepared
- [ ] Monitoring systems in place

### Deployment
- [ ] Infrastructure deployed
- [ ] Database initialized
- [ ] Cache warmed
- [ ] Services healthy
- [ ] Load balancer configured

### Post-deployment
- [ ] Health checks passing
- [ ] Performance tests completed
- [ ] Monitoring alerts configured
- [ ] Backup systems verified
- [ ] Documentation updated

### Production Readiness
- [ ] Security scan passed
- [ ] Load testing completed
- [ ] Disaster recovery tested
- [ ] Team training completed
- [ ] Support procedures documented