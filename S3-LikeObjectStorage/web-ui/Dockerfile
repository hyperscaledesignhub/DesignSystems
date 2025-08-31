FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9347

ENV S3_API_URL=http://api-gateway:7841

CMD ["python", "app.py"]