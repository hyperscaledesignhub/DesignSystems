import os
import json
import uuid
import httpx
import redis
import time
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
from status_tracker import NotificationStatusTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Server", version="1.0.0")

# Add CORS for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 7847))
USER_DB_URL = os.getenv("USER_DB_URL", "http://localhost:7846")

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
                socket_timeout=5,
                retry_on_timeout=True
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

redis_client = None
status_tracker = None

class NotificationRequest(BaseModel):
    user_id: int
    type: str
    subject: Optional[str] = None
    message: str
    metadata: Optional[dict] = {}

class NotificationTask(BaseModel):
    notification_id: str
    user_id: int
    type: str
    payload: dict
    created_at: str

@app.on_event("startup")
async def startup_event():
    global redis_client, status_tracker
    try:
        redis_client = get_redis_client()
        status_tracker = NotificationStatusTracker(redis_client)
        logger.info("Notification server started successfully")
    except Exception as e:
        logger.error(f"Failed to start notification server: {e}")
        raise

@app.get("/health")
async def health_check():
    try:
        if redis_client is None:
            return {"status": "unhealthy", "service": "notification-server", "error": "Redis not initialized"}
        
        redis_client.ping()
        
        # Test user database connection
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{USER_DB_URL}/health", timeout=5.0)
            if response.status_code != 200:
                return {"status": "unhealthy", "service": "notification-server", "error": "User database unreachable"}
        
        return {
            "status": "healthy", 
            "service": "notification-server", 
            "redis": "connected",
            "user_db": "connected"
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "notification-server", "error": str(e)}

@app.post("/notifications/process")
async def process_notification(request: NotificationRequest):
    try:
        # Fetch user contact info from user database
        async with httpx.AsyncClient() as client:
            user_response = await client.get(f"{USER_DB_URL}/users/{request.user_id}")
            if user_response.status_code == 404:
                raise HTTPException(status_code=404, detail="User not found")
            user_response.raise_for_status()
            user_data = user_response.json()
            
            # Validate user has required contact info for notification type
            logger.info(f"Validating contact info for {request.type}: {user_data}")
            if request.type == "email" and not user_data.get("email"):
                logger.info("Missing email address")
                raise HTTPException(status_code=400, detail="User has no email address")
            elif request.type == "sms" and not user_data.get("phone_number"):
                logger.info(f"Missing phone number: {user_data.get('phone_number')}")
                raise HTTPException(status_code=400, detail="User has no phone number")
            elif request.type == "push":
                # Check for device tokens
                device_response = await client.get(f"{USER_DB_URL}/users/{request.user_id}/devices")
                if device_response.status_code == 200:
                    devices = device_response.json()
                    if not devices:
                        raise HTTPException(status_code=400, detail="User has no devices for push notifications")
                else:
                    raise HTTPException(status_code=400, detail="Could not fetch user devices")
        
        # Create notification task
        notification_id = str(uuid.uuid4())
        task = NotificationTask(
            notification_id=notification_id,
            user_id=request.user_id,
            type=request.type,
            payload={
                "subject": request.subject,
                "message": request.message,
                "metadata": request.metadata or {},
                "user_data": user_data
            },
            created_at=datetime.utcnow().isoformat()
        )
        
        # Add to appropriate queue
        queue_name = f"{request.type}_queue"
        task_json = task.model_dump_json()
        
        # Add to queue with expiration
        redis_client.lpush(queue_name, task_json)
        redis_client.expire(queue_name, 86400)  # 24 hours TTL
        
        logger.info(f"Notification {notification_id} queued to {queue_name}")
        
        # Track notification status
        status_tracker.track_notification(
            notification_id=notification_id,
            user_id=request.user_id,
            notification_type=request.type,
            status="queued"
        )
        
        return {
            "notification_id": notification_id,
            "status": "queued",
            "queue": queue_name,
            "user_id": request.user_id
        }
        
    except HTTPException:
        # Re-raise HTTPExceptions (400, 404, etc.) without modification
        raise
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"User database unavailable: {str(e)}")
    except redis.RedisError as e:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {str(e)}")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Unexpected error processing notification: {error_details}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/notifications/{notification_id}/status")
async def get_notification_status(notification_id: str):
    """Get notification status by ID"""
    try:
        status = status_tracker.get_status(notification_id)
        if status:
            return status
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {str(e)}")

@app.get("/users/{user_id}/notifications")
async def get_user_notifications(user_id: int, limit: int = 50):
    """Get recent notifications for a user"""
    try:
        notifications = status_tracker.get_user_notifications(user_id, limit)
        return {
            "user_id": user_id,
            "notifications": notifications,
            "count": len(notifications)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving notifications: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7842))
    uvicorn.run(app, host="0.0.0.0", port=port)