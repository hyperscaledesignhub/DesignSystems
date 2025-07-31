# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for compilation and timeout
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    python3-dev \
    build-essential \
    pkg-config \
    coreutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY distributed/ ./distributed/
COPY config/ ./config/
COPY persistence/ ./persistence/
COPY yaml/config.yaml ./config.yaml

# Create data directory with proper permissions
RUN mkdir -p /data && chown -R 1000:1000 /data

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && chown -R 1000:1000 /app/logs

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 dbuser

# Switch to non-root user
USER dbuser

# Set environment variables
ENV DOCKER_ENV=true
ENV PYTHONPATH=/app

# Expose ports - HTTP API and health check ports
EXPOSE 8080 8081 9080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - use node.py
CMD ["python", "distributed/node.py"]