import os
import json
import redis
import smtplib
import asyncio
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Email Worker", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 7847))
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

redis_client = None
worker_running = False

def get_redis_client():
    """Get Redis client with connection retry"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            client = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            client.ping()
            logger.info(f"Redis connected on attempt {attempt + 1}")
            return client
        except Exception as e:
            logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise Exception("Failed to connect to Redis after 5 attempts")

@app.get("/health")
async def health_check():
    try:
        if redis_client is None:
            return {"status": "unhealthy", "service": "email-worker", "error": "Redis not initialized"}
        
        redis_client.ping()
        
        # Check SMTP configuration
        smtp_configured = bool(SMTP_USERNAME and SMTP_PASSWORD)
        
        return {
            "status": "healthy", 
            "service": "email-worker", 
            "redis": "connected",
            "smtp_configured": smtp_configured,
            "worker_running": worker_running
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "email-worker", "error": str(e)}

def send_email(to_email: str, subject: str, message: str, from_email: str = None) -> bool:
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email or SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False

async def process_email_queue():
    """Process email notifications from Redis queue"""
    global worker_running
    worker_running = True
    
    logger.info("Email worker started")
    
    while worker_running:
        try:
            # Block for 1 second waiting for tasks
            task_data = redis_client.brpop("email_queue", timeout=1)
            
            if task_data:
                _, task_json = task_data
                task = json.loads(task_json)
                
                logger.info(f"Processing email task: {task['notification_id']}")
                
                payload = task['payload']
                user_data = payload['user_data']
                
                if not user_data.get('email'):
                    logger.error(f"No email address for user in task {task['notification_id']}")
                    continue
                
                success = send_email(
                    to_email=user_data['email'],
                    subject=payload.get('subject', 'Notification'),
                    message=payload['message']
                )
                
                if success:
                    logger.info(f"Email notification {task['notification_id']} sent successfully")
                else:
                    # Retry logic - add back to queue for retry (max 3 times)
                    retry_count = task.get('retry_count', 0)
                    if retry_count < 3:
                        task['retry_count'] = retry_count + 1
                        redis_client.lpush("email_queue", json.dumps(task))
                        logger.info(f"Email notification {task['notification_id']} queued for retry {retry_count + 1}")
                    else:
                        logger.error(f"Email notification {task['notification_id']} failed after 3 retries")
                        
        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            await asyncio.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    global redis_client
    try:
        redis_client = get_redis_client()
        # Start the queue processor as background task
        asyncio.create_task(process_email_queue())
        logger.info("Email worker started successfully")
    except Exception as e:
        logger.error(f"Failed to start email worker: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global worker_running
    worker_running = False

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7843))
    uvicorn.run(app, host="0.0.0.0", port=port)