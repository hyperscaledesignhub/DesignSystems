FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY ../../shared /app/shared
COPY . .

EXPOSE 23458

CMD ["python", "main.py"]