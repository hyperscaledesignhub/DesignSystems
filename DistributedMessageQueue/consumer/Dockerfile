FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn aiohttp

# Copy consumer service
COPY consumer/local_server.py /app/server.py

# Expose port
EXPOSE 19003

# Run the service
CMD ["python", "server.py"]