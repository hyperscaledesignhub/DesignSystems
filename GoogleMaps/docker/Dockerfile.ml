# ML Model Server Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    curl \\
    wget \\
    build-essential \\
    libgomp1 \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (ML-focused)
COPY requirements.txt .

# Install ML dependencies
RUN pip install --no-cache-dir \\
    scikit-learn==1.3.2 \\
    pandas==2.1.4 \\
    numpy==1.25.2 \\
    tensorflow==2.15.0 \\
    torch==2.1.2 \\
    ortools==9.8.3296 \\
    fastapi==0.104.1 \\
    uvicorn[standard]==0.24.0 \\
    redis==5.0.1 \\
    pydantic==2.5.0

# Copy source code
COPY src/ ./src/

# Create model directories
RUN mkdir -p models cache logs

# Copy pre-trained models (if any)
COPY models/ ./models/ 2>/dev/null || mkdir -p ./models

# Expose ML service port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8001/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_PATH=/app/models
ENV PYTHONUNBUFFERED=1

# Run the ML Model Server
CMD ["python", "-m", "src.ml_eta_service", "--host", "0.0.0.0", "--port", "8001"]