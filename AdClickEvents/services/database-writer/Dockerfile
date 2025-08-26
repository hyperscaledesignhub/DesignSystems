FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask==2.3.3 \
    kafka-python==2.0.2 \
    influxdb-client==1.36.1 \
    watchdog==3.0.0 \
    requests==2.31.0

# Copy application code
COPY . .

# Expose port for health check
EXPOSE 8907

# Run the database writer
CMD ["python", "app.py"]