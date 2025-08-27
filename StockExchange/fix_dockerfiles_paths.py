#!/usr/bin/env python3

import os
import glob

# Service configurations
services = [
    "user-service", "wallet-service", "risk-manager", "order-manager", 
    "matching-engine", "client-gateway", "market-data-service", 
    "reporting-service", "notification-service"
]

# Template for each service Dockerfile
DOCKERFILE_TEMPLATE = """FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    libpq-dev \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY microservices/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and service code
COPY microservices/shared/ ./shared/
COPY microservices/services/{service_name}/ ./services/{service_name}/

# Set working directory to service
WORKDIR /app/services/{service_name}

# Set Python path
ENV PYTHONPATH=/app
ENV PORT={port}
ENV SERVICE_NAME={service_name}

# Expose port
EXPOSE {port}

# Run the service
CMD ["python", "main.py"]
"""

# Service port mappings
service_ports = {
    "user-service": "8975",
    "wallet-service": "8651", 
    "risk-manager": "8539",
    "order-manager": "8426",
    "matching-engine": "8792",
    "client-gateway": "8347",
    "market-data-service": "8864",
    "reporting-service": "9127", 
    "notification-service": "9243"
}

# Update each Dockerfile
for service in services:
    dockerfile_path = f"docker/Dockerfile.{service}"
    
    if os.path.exists(dockerfile_path):
        content = DOCKERFILE_TEMPLATE.format(
            service_name=service,
            port=service_ports[service]
        )
        
        with open(dockerfile_path, 'w') as f:
            f.write(content)
        
        print(f"Updated {dockerfile_path}")

print("All service Dockerfiles updated!")

# Update frontend Dockerfile
frontend_dockerfile = """# Use Node.js 18 as base image
FROM node:18-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY frontend/ .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/nginx.conf

# Copy built application
COPY --from=builder /app/build /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
"""

with open("docker/Dockerfile.frontend", 'w') as f:
    f.write(frontend_dockerfile)

print("Updated docker/Dockerfile.frontend")