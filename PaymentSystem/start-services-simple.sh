#!/bin/bash

echo "Starting all services except UI using individual Docker commands..."

# Create network if it doesn't exist
echo "Creating payment-network if not exists..."
docker network create payment-network 2>/dev/null || echo "Network already exists"

# Start Observability
echo "Starting Jaeger..."
docker run -d \
  --name demo-jaeger-1 \
  --network payment-network \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 14250:14250 \
  -e COLLECTOR_OTLP_ENABLED=true \
  -e LOG_LEVEL=debug \
  jaegertracing/all-in-one:latest

# Start PostgreSQL databases
echo "Starting PostgreSQL databases..."
docker run -d \
  --name demo-postgres-payment-1 \
  --network payment-network \
  -p 5439:5432 \
  -e POSTGRES_DB=payment_db \
  -e POSTGRES_USER=payment_user \
  -e POSTGRES_PASSWORD=payment_pass \
  -v postgres_payment_data:/var/lib/postgresql/data \
  postgres:15

docker run -d \
  --name demo-postgres-ledger-1 \
  --network payment-network \
  -p 5440:5432 \
  -e POSTGRES_DB=ledger_db \
  -e POSTGRES_USER=ledger_user \
  -e POSTGRES_PASSWORD=ledger_pass \
  -v postgres_ledger_data:/var/lib/postgresql/data \
  postgres:15

docker run -d \
  --name demo-postgres-wallet-1 \
  --network payment-network \
  -p 5441:5432 \
  -e POSTGRES_DB=wallet_db \
  -e POSTGRES_USER=wallet_user \
  -e POSTGRES_PASSWORD=wallet_pass \
  -v postgres_wallet_data:/var/lib/postgresql/data \
  postgres:15

docker run -d \
  --name demo-postgres-fraud-1 \
  --network payment-network \
  -p 5442:5432 \
  -e POSTGRES_DB=fraud_db \
  -e POSTGRES_USER=fraud_user \
  -e POSTGRES_PASSWORD=fraud_pass \
  -v postgres_fraud_data:/var/lib/postgresql/data \
  postgres:15

docker run -d \
  --name demo-postgres-reconciliation-1 \
  --network payment-network \
  -p 5443:5432 \
  -e POSTGRES_DB=reconciliation_db \
  -e POSTGRES_USER=reconciliation_user \
  -e POSTGRES_PASSWORD=reconciliation_pass \
  -v postgres_reconciliation_data:/var/lib/postgresql/data \
  postgres:15

docker run -d \
  --name demo-postgres-notification-1 \
  --network payment-network \
  -p 5444:5432 \
  -e POSTGRES_DB=notification_db \
  -e POSTGRES_USER=notification_user \
  -e POSTGRES_PASSWORD=notification_pass \
  -v postgres_notification_data:/var/lib/postgresql/data \
  postgres:15

# Start Redis instances
echo "Starting Redis instances..."
docker run -d \
  --name demo-redis-payment-1 \
  --network payment-network \
  -p 6385:6379 \
  -v redis_payment_data:/data \
  redis:7-alpine

docker run -d \
  --name demo-redis-wallet-1 \
  --network payment-network \
  -p 6386:6379 \
  -v redis_wallet_data:/data \
  redis:7-alpine

docker run -d \
  --name demo-redis-fraud-1 \
  --network payment-network \
  -p 6387:6379 \
  -v redis_fraud_data:/data \
  redis:7-alpine

# Start RabbitMQ
echo "Starting RabbitMQ..."
docker run -d \
  --name demo-rabbitmq-1 \
  --network payment-network \
  -p 5678:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  -v rabbitmq_data:/var/lib/rabbitmq \
  rabbitmq:3-management

# Wait for infrastructure services to be ready
echo "Waiting for infrastructure services to be ready..."
sleep 10

# Build and start application services that work (skip the ones with build issues)
echo "Building and starting working application services..."

echo "Building wallet-service..."
docker build -t wallet-service:latest -f ./services/wallet-service/Dockerfile ./services/wallet-service

echo "Starting wallet-service..."
docker run -d \
  --name demo-wallet-service-1 \
  --network payment-network \
  -p 8740:8740 \
  -e DATABASE_URL=postgresql://wallet_user:wallet_pass@demo-postgres-wallet-1:5432/wallet_db \
  -e REDIS_URL=redis://demo-redis-wallet-1:6379 \
  -e JAEGER_HOST=demo-jaeger-1 \
  -v $(pwd)/tracing.py:/app/tracing.py \
  wallet-service:latest

echo "Building fraud-detection-service..."
docker build -t fraud-detection-service:latest -f ./services/fraud-detection-service/Dockerfile ./services/fraud-detection-service

echo "Starting fraud-detection-service..."
docker run -d \
  --name demo-fraud-detection-service-1 \
  --network payment-network \
  -p 8742:8742 \
  -e DATABASE_URL=postgresql://fraud_user:fraud_pass@demo-postgres-fraud-1:5432/fraud_db \
  -e REDIS_URL=redis://demo-redis-fraud-1:6379 \
  -e PAYMENT_SERVICE_URL=http://payment-service:8734 \
  -e NOTIFICATION_SERVICE_URL=http://notification-service:8743 \
  -e JAEGER_HOST=demo-jaeger-1 \
  -v $(pwd)/tracing.py:/app/tracing.py \
  fraud-detection-service:latest

echo "Building reconciliation-service..."
docker build -t reconciliation-service:latest -f ./services/reconciliation-service/Dockerfile ./services/reconciliation-service

echo "Starting reconciliation-service..."
docker run -d \
  --name demo-reconciliation-service-1 \
  --network payment-network \
  -p 8741:8741 \
  -e DATABASE_URL=postgresql://reconciliation_user:reconciliation_pass@demo-postgres-reconciliation-1:5432/reconciliation_db \
  -e PAYMENT_SERVICE_URL=http://payment-service:8734 \
  -e LEDGER_SERVICE_URL=http://ledger-service:8736 \
  -e PSP_GATEWAY_URL=http://psp-gateway:8738 \
  -e WALLET_SERVICE_URL=http://demo-wallet-service-1:8740 \
  -e JAEGER_HOST=demo-jaeger-1 \
  -v $(pwd)/tracing.py:/app/tracing.py \
  reconciliation-service:latest

echo "Building notification-service..."
docker build -t notification-service:latest -f ./services/notification-service/Dockerfile ./services/notification-service

echo "Starting notification-service..."
docker run -d \
  --name demo-notification-service-1 \
  --network payment-network \
  -p 8743:8004 \
  -e DATABASE_URL=postgresql://notification_user:notification_pass@demo-postgres-notification-1:5432/notification_db \
  -e RABBITMQ_URL=amqp://guest:guest@demo-rabbitmq-1:5672/ \
  -e JAEGER_HOST=demo-jaeger-1 \
  -v $(pwd)/tracing.py:/app/tracing.py \
  notification-service:latest

echo ""
echo "Checking running containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep demo

echo ""
echo "Services are available at:"
echo "  - Wallet Service: http://localhost:8740"
echo "  - Reconciliation Service: http://localhost:8741"
echo "  - Fraud Detection Service: http://localhost:8742"
echo "  - Notification Service: http://localhost:8743"
echo "  - Jaeger UI: http://localhost:16686"
echo "  - RabbitMQ Management: http://localhost:15672"
echo ""
echo "Note: Some services (payment-service, ledger-service, psp-gateway, api-gateway) were skipped due to build issues with missing source files."