FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn aiofiles

# Copy broker service
COPY broker/simple_server.py /app/server.py

# Create data directory
RUN mkdir -p /data/broker

# Expose port
EXPOSE 19001

# Run the service
CMD ["python", "server.py"]