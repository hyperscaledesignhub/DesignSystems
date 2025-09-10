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

app = FastAPI(title="Push Notification Worker", version="1.0.0")

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
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")
FCM_API_URL = os.getenv("FCM_API_URL", "https://fcm.googleapis.com/fcm/send")
USER_DB_URL = os.getenv("USER_DB_URL", "http://localhost:7846")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
worker_running = False

@app.get("/health")
async def health_check():
    try:
        redis_client.ping()
        return {"status": "healthy", "service": "push-worker", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "service": "push-worker", "error": str(e)}

async def send_push_notification(device_token: str, title: str, message: str) -> bool:
    """Send push notification via FCM"""
    try:
        headers = {
            "Authorization": f"key={FCM_SERVER_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "to": device_token,
            "notification": {
                "title": title,
                "body": message
            },
            "data": {
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                FCM_API_URL,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", 0) > 0:
                    logger.info(f"Push notification sent successfully to device {device_token[:20]}...")
                    return True
                else:
                    logger.error(f"FCM failed to send notification: {result}")
                    return False
            else:
                logger.error(f"Failed to send push notification: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to send push notification: {str(e)}")
        return False

async def get_user_devices(user_id: int) -> list:
    """Get user devices from user database"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{USER_DB_URL}/users/{user_id}/devices")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user devices: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"Error fetching user devices: {str(e)}")
        return []

def process_push_queue():
    """Process push notifications from Redis queue"""
    global worker_running
    worker_running = True
    
    logger.info("Push notification worker started")
    
    while worker_running:
        try:
            # Block for 1 second waiting for tasks
            task_data = redis_client.brpop("push_queue", timeout=1)
            
            if task_data:
                _, task_json = task_data
                task = json.loads(task_json)
                
                logger.info(f"Processing push notification task: {task['notification_id']}")
                
                payload = task['payload']
                user_id = task['user_id']
                
                # Get user devices
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                devices = loop.run_until_complete(get_user_devices(user_id))
                
                if not devices:
                    logger.warning(f"No devices found for user {user_id}")
                    continue
                
                # Send to all user devices
                success_count = 0
                for device in devices:
                    device_token = device.get('device_token')
                    if device_token:
                        success = loop.run_until_complete(send_push_notification(
                            device_token=device_token,
                            title=payload.get('subject', 'Notification'),
                            message=payload['message']
                        ))
                        if success:
                            success_count += 1
                
                loop.close()
                
                if success_count > 0:
                    logger.info(f"Push notification {task['notification_id']} sent to {success_count}/{len(devices)} devices")
                else:
                    # Retry logic - add back to queue for retry (max 3 times)
                    retry_count = task.get('retry_count', 0)
                    if retry_count < 3:
                        task['retry_count'] = retry_count + 1
                        redis_client.lpush("push_queue", json.dumps(task))
                        logger.info(f"Push notification {task['notification_id']} queued for retry {retry_count + 1}")
                    else:
                        logger.error(f"Push notification {task['notification_id']} failed after 3 retries")
                        
        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            asyncio.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    # Start the queue processor in a background thread
    thread = threading.Thread(target=process_push_queue, daemon=True)
    thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    global worker_running
    worker_running = False

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7845))
    uvicorn.run(app, host="0.0.0.0", port=port)