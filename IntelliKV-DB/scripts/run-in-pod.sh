#!/bin/bash

# Usage: ./run-in-pod.sh <script-to-run> [pod-name] [namespace]
# Example: ./run-in-pod.sh pod-verify.sh distributed-database-0 distributed-db

set -e

SCRIPT_PATH="$1"
POD_NAME="${2:-distributed-database-0}"
NAMESPACE="${3:-distributed-db}"

if [[ -z "$SCRIPT_PATH" || ! -f "$SCRIPT_PATH" ]]; then
  echo "Usage: $0 <script-to-run> [pod-name] [namespace]"
  echo "Script file '$SCRIPT_PATH' not found."
  exit 1
fi

SCRIPT_BASENAME=$(basename "$SCRIPT_PATH")

echo "Copying $SCRIPT_PATH to pod $POD_NAME in namespace $NAMESPACE..."
kubectl cp "$SCRIPT_PATH" "$NAMESPACE/$POD_NAME:/tmp/$SCRIPT_BASENAME"

echo "Making script executable and running it inside the pod..."
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- /bin/sh -c "chmod +x /tmp/$SCRIPT_BASENAME && /tmp/$SCRIPT_BASENAME"

echo "Done." 