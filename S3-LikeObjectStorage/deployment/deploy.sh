#!/bin/bash

# Deploy S3 Storage System to Kubernetes
set -e

echo "Deploying S3 Storage System to Kubernetes..."

KUBE_DIR="$(dirname "$0")/kubernetes"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

echo "📦 Creating namespace..."
kubectl apply -f "$KUBE_DIR/namespace.yaml"

echo "🗄️  Deploying PostgreSQL database..."
kubectl apply -f "$KUBE_DIR/postgresql.yaml"

echo "⏳ Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgresql -n s3-storage --timeout=300s

echo "🚀 Deploying microservices..."

# Deploy services in dependency order
echo "  📡 Deploying Identity Service..."
kubectl apply -f "$KUBE_DIR/identity-service.yaml"

echo "  🪣 Deploying Bucket Service..."
kubectl apply -f "$KUBE_DIR/bucket-service.yaml"

echo "  💾 Deploying Storage Service..."
kubectl apply -f "$KUBE_DIR/storage-service.yaml"

echo "  📋 Deploying Metadata Service..."
kubectl apply -f "$KUBE_DIR/metadata-service.yaml"

echo "  📦 Deploying Object Service..."
kubectl apply -f "$KUBE_DIR/object-service.yaml"

echo "  🌐 Deploying API Gateway..."
kubectl apply -f "$KUBE_DIR/api-gateway.yaml"

echo "⏳ Waiting for all services to be ready..."
kubectl wait --for=condition=ready pod -l app=identity-service -n s3-storage --timeout=300s
kubectl wait --for=condition=ready pod -l app=bucket-service -n s3-storage --timeout=300s
kubectl wait --for=condition=ready pod -l app=storage-service -n s3-storage --timeout=300s
kubectl wait --for=condition=ready pod -l app=metadata-service -n s3-storage --timeout=300s
kubectl wait --for=condition=ready pod -l app=object-service -n s3-storage --timeout=300s
kubectl wait --for=condition=ready pod -l app=api-gateway -n s3-storage --timeout=300s

echo ""
echo "🎉 S3 Storage System deployed successfully!"
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n s3-storage
echo ""
echo "🔗 Services:"
kubectl get services -n s3-storage
echo ""
echo "📍 API Gateway External IP:"
kubectl get service api-gateway-service -n s3-storage -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
echo ""
echo ""
echo "🔑 To get the admin API key, run:"
echo "kubectl logs -n s3-storage -l app=identity-service | grep 'Admin API Key'"