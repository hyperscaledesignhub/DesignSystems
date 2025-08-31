FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 7851

# Create data directory for SQLite
RUN mkdir -p /data

CMD ["python", "main.py"]