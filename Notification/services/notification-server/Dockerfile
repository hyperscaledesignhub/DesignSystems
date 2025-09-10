FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py status_tracker.py ./

EXPOSE 7842

CMD ["python", "main.py"]