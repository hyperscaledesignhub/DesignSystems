# Monitoring Service - Minimal Features

## Core Features
- Metrics collection (Prometheus)
- Basic dashboards (Grafana)
- Health checks
- Alert rules for critical services

## Metrics to Track
- Request rate and latency
- Service availability
- Database connection pool
- Cache hit ratio
- CPU and memory usage

## Alert Rules
- Service down > 1 minute
- Response time > 1 second
- Error rate > 5%
- Database connections > 80%

## Port Configuration
- Prometheus: 9290
- Grafana: 3200
- Alert Manager: 9293

## Technologies
- Prometheus
- Grafana
- Python prometheus_client

## Resource Requirements
- CPU: 500m
- Memory: 1Gi
- Storage: 50Gi