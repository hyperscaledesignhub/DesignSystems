FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn aiohttp

# Copy UI application
COPY ui/enhanced_app.py /app/app.py

# Expose port
EXPOSE 8080

# Run the UI service
CMD ["python", "app.py"]