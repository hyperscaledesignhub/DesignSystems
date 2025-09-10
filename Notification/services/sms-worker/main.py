import os
import json
import redis
import httpx
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SMS Worker", version="1.0.0")

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
SMS_API_URL = os.getenv("SMS_API_URL", "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json")
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
worker_running = False

@app.get("/health")
async def health_check():
    try:
        redis_client.ping()
        return {"status": "healthy", "service": "sms-worker", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "service": "sms-worker", "error": str(e)}

async def send_sms(to_number: str, message: str) -> bool:
    """Send SMS via Twilio API"""
    try:
        url = SMS_API_URL.format(account_sid=TWILIO_ACCOUNT_SID)
        
        data = {
            'From': TWILIO_FROM_NUMBER,
            'To': to_number,
            'Body': message
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                timeout=30.0
            )
            
            if response.status_code == 201:
                logger.info(f"SMS sent successfully to {to_number}")
                return True
            else:
                logger.error(f"Failed to send SMS to {to_number}: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_number}: {str(e)}")
        return False

def process_sms_queue():
    """Process SMS notifications from Redis queue"""
    global worker_running
    worker_running = True
    
    logger.info("SMS worker started")
    
    while worker_running:
        try:
            # Block for 1 second waiting for tasks
            task_data = redis_client.brpop("sms_queue", timeout=1)
            
            if task_data:
                _, task_json = task_data
                task = json.loads(task_json)
                
                logger.info(f"Processing SMS task: {task['notification_id']}")
                
                payload = task['payload']
                user_data = payload['user_data']
                
                # Format phone number with country code
                phone_number = f"+{user_data.get('country_code', '1')}{user_data['phone_number']}"
                
                # Run async function in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(send_sms(phone_number, payload['message']))
                loop.close()
                
                if success:
                    logger.info(f"SMS notification {task['notification_id']} sent successfully")
                else:
                    # Retry logic - add back to queue for retry (max 3 times)
                    retry_count = task.get('retry_count', 0)
                    if retry_count < 3:
                        task['retry_count'] = retry_count + 1
                        redis_client.lpush("sms_queue", json.dumps(task))
                        logger.info(f"SMS notification {task['notification_id']} queued for retry {retry_count + 1}")
                    else:
                        logger.error(f"SMS notification {task['notification_id']} failed after 3 retries")
                        
        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            asyncio.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    # Start the queue processor in a background thread
    thread = threading.Thread(target=process_sms_queue, daemon=True)
    thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    global worker_running
    worker_running = False

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7844))
    uvicorn.run(app, host="0.0.0.0", port=port)