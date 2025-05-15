#!/bin/bash

# Apply the test files ConfigMap
echo "Applying test files ConfigMap..."
kubectl apply -f test-files.yaml

# Apply the test pod
echo "Applying test pod..."
kubectl apply -f test-pod.yaml

# Wait for the pod to be ready
echo "Waiting for test pod to be ready..."
kubectl wait --for=condition=Ready pod/test-pod -n rate-limiter --timeout=60s

# Get the pod logs
echo "Getting test pod logs..."
kubectl logs -f test-pod -n rate-limiter

# Clean up
#echo "Cleaning up..."
kubectl delete pod test-pod -n rate-limiter
kubectl delete configmap test-files -n rate-limiter 