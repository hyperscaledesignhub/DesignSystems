FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn

# Copy coordinator service
COPY coordinator/simple_server.py /app/server.py

# Expose port
EXPOSE 19004

# Run the service
CMD ["python", "server.py"]