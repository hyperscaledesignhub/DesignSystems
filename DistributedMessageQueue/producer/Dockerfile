FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn aiohttp

# Copy producer service
COPY producer/local_server.py /app/server.py

# Expose port
EXPOSE 19002

# Run the service
CMD ["python", "server.py"]