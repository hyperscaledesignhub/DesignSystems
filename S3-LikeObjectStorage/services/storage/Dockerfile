FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 7881

# Create data directories
RUN mkdir -p /data/storage

CMD ["python", "main.py"]