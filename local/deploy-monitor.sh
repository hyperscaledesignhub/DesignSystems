#!/bin/bash

echo "Creating promotheus roles"
kubectl apply -f prometheus-rbac.yaml
sleep 2
echo "Creating promotheus and grafana pods"
kubectl apply -f monitoring.yaml 