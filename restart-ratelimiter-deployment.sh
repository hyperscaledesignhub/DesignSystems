#!/bin/bash

kubectl delete deployment -n rate-limiter rate-limiter
kubectl apply -f local/deployment-local.yaml
sleep 5
kubectl get pods -n rate-limiter
