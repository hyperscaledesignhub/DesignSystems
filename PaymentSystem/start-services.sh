#!/bin/bash

echo "Starting all services as separate Docker containers (excluding UI service)..."

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

# Build and start application services
echo "Building and starting application services..."

# Build services that need local context
echo "Building payment-service..."
docker build -t payment-service:latest -f ../services/payment-service/Dockerfile ../

echo "Building payment-executor..."
docker build -t payment-executor:latest -f ../services/payment-executor/Dockerfile ../

echo "Building ledger-service..."
docker build -t ledger-service:latest -f ../services/ledger-service/Dockerfile ../

echo "Building psp-gateway..."
docker build -t psp-gateway:latest -f ../services/psp-gateway/Dockerfile ../

echo "Building api-gateway..."
docker build -t api-gateway:latest -f ../services/api-gateway/Dockerfile ../

echo "Building wallet-service..."
docker build -t wallet-service:latest -f ./services/wallet-service/Dockerfile ./services/wallet-service

echo "Building reconciliation-service..."
docker build -t reconciliation-service:latest -f ./services/reconciliation-service/Dockerfile ./services/reconciliation-service

echo "Building fraud-detection-service..."
docker build -t fraud-detection-service:latest -f ./services/fraud-detection-service/Dockerfile ./services/fraud-detection-service

echo "Building notification-service..."
docker build -t notification-service:latest -f ./services/notification-service/Dockerfile ./services/notification-service

# Start application services
echo "Starting payment-service..."
docker run -d \
  --name demo-payment-service-1 \
  --network payment-network \
  -p 8734:8734 \
  -e DATABASE_URL=postgresql://payment_user:payment_pass@postgres-payment:5432/payment_db \
  -e REDIS_URL=redis://redis-payment:6379 \
  -e RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/ \
  -e LEDGER_SERVICE_URL=http://ledger-service:8736 \
  -e FRAUD_SERVICE_URL=http://fraud-detection-service:8742 \
  -e WALLET_SERVICE_URL=http://wallet-service:8740 \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/../services/payment-service:/app \
  payment-service:latest

echo "Starting payment-executor..."
docker run -d \
  --name demo-payment-executor-1 \
  --network payment-network \
  -e RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/ \
  -e PSP_GATEWAY_URL=http://psp-gateway:8738 \
  -e NOTIFICATION_SERVICE_URL=http://notification-service:8743 \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/../services/payment-executor:/app \
  payment-executor:latest

echo "Starting ledger-service..."
docker run -d \
  --name demo-ledger-service-1 \
  --network payment-network \
  -p 8736:8736 \
  -e DATABASE_URL=postgresql://ledger_user:ledger_pass@postgres-ledger:5432/ledger_db \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/../services/ledger-service:/app \
  ledger-service:latest

echo "Starting psp-gateway..."
docker run -d \
  --name demo-psp-gateway-1 \
  --network payment-network \
  -p 8738:8738 \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/../services/psp-gateway:/app \
  psp-gateway:latest

echo "Starting wallet-service..."
docker run -d \
  --name demo-wallet-service-1 \
  --network payment-network \
  -p 8740:8740 \
  -e DATABASE_URL=postgresql://wallet_user:wallet_pass@postgres-wallet:5432/wallet_db \
  -e REDIS_URL=redis://redis-wallet:6379 \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/tracing.py:/app/tracing.py \
  wallet-service:latest

echo "Starting reconciliation-service..."
docker run -d \
  --name demo-reconciliation-service-1 \
  --network payment-network \
  -p 8741:8741 \
  -e DATABASE_URL=postgresql://reconciliation_user:reconciliation_pass@postgres-reconciliation:5432/reconciliation_db \
  -e PAYMENT_SERVICE_URL=http://payment-service:8734 \
  -e LEDGER_SERVICE_URL=http://ledger-service:8736 \
  -e PSP_GATEWAY_URL=http://psp-gateway:8738 \
  -e WALLET_SERVICE_URL=http://wallet-service:8740 \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/tracing.py:/app/tracing.py \
  reconciliation-service:latest

echo "Starting fraud-detection-service..."
docker run -d \
  --name demo-fraud-detection-service-1 \
  --network payment-network \
  -p 8742:8742 \
  -e DATABASE_URL=postgresql://fraud_user:fraud_pass@postgres-fraud:5432/fraud_db \
  -e REDIS_URL=redis://redis-fraud:6379 \
  -e PAYMENT_SERVICE_URL=http://payment-service:8734 \
  -e NOTIFICATION_SERVICE_URL=http://notification-service:8743 \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/tracing.py:/app/tracing.py \
  fraud-detection-service:latest

echo "Starting notification-service..."
docker run -d \
  --name demo-notification-service-1 \
  --network payment-network \
  -p 8743:8004 \
  -e DATABASE_URL=postgresql://notification_user:notification_pass@postgres-notification:5432/notification_db \
  -e RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/ \
  -e JAEGER_HOST=jaeger \
  -v $(pwd)/tracing.py:/app/tracing.py \
  notification-service:latest

echo "Starting api-gateway..."
docker run -d \
  --name demo-api-gateway-1 \
  --network payment-network \
  -p 8733:8733 \
  -e PAYMENT_SERVICE_URL=http://payment-service:8734 \
  -e LEDGER_SERVICE_URL=http://ledger-service:8736 \
  -e WALLET_SERVICE_URL=http://wallet-service:8740 \
  -e FRAUD_SERVICE_URL=http://fraud-detection-service:8742 \
  -e RECONCILIATION_SERVICE_URL=http://reconciliation-service:8741 \
  -e NOTIFICATION_SERVICE_URL=http://notification-service:8743 \
  -e JAEGER_HOST=jaeger \
  api-gateway:latest

echo ""
echo "All services started as separate Docker containers!"
echo "Skipped: payment-dashboard (UI service) - run locally instead"
echo ""
echo "Checking running containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Services are available at:"
echo "  - API Gateway: http://localhost:8733"
echo "  - Payment Service: http://localhost:8734"
echo "  - Ledger Service: http://localhost:8736"
echo "  - PSP Gateway: http://localhost:8738"
echo "  - Wallet Service: http://localhost:8740"
echo "  - Reconciliation Service: http://localhost:8741"
echo "  - Fraud Detection Service: http://localhost:8742"
echo "  - Notification Service: http://localhost:8743"
echo "  - Jaeger UI: http://localhost:16686"
echo "  - RabbitMQ Management: http://localhost:15672"