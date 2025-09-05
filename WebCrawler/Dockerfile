# Base Python image for all services
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared requirements
COPY shared/requirements.txt /app/shared/requirements.txt
COPY shared/models.py /app/shared/models.py

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

# Install service-specific dependencies based on build arg
ARG SERVICE_NAME
COPY services/${SERVICE_NAME}/requirements.txt* /app/
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

# Copy service code
COPY services/${SERVICE_NAME}/ /app/

# Expose port
EXPOSE 5000

# Run the service
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "app:app"]