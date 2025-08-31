#!/bin/bash

# Cleanup S3 Storage System from Kubernetes
set -e

echo "🧹 Cleaning up S3 Storage System from Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed."
    exit 1
fi

echo "🗑️  Deleting all resources in s3-storage namespace..."
kubectl delete namespace s3-storage --ignore-not-found=true

echo "⏳ Waiting for namespace deletion..."
kubectl wait --for=delete namespace/s3-storage --timeout=120s || true

echo ""
echo "✅ S3 Storage System cleanup completed!"
echo ""
echo "🔍 Remaining resources (should be empty):"
kubectl get all -n s3-storage 2>/dev/null || echo "No resources found (expected)"