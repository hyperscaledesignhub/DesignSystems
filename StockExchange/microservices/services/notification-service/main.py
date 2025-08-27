import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
import uvicorn
import asyncio
import json
import redis.asyncio as redis
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
import httpx

from shared.models.base import OrderSide
from shared.utils.auth import verify_token
from shared.utils.database import get_redis_url

app = FastAPI(title="Notification Service", version="1.0.0")
security = HTTPBearer()

# Redis for pub/sub
redis_client = None

# WebSocket connections by user_id
websocket_connections: Dict[int, List[WebSocket]] = defaultdict(list)

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@stockexchange.com")

# Service URLs
USER_SERVICE_URL = "http://localhost:8975"

class NotificationCreate(BaseModel):
    user_id: int
    type: str  # email, websocket, sms
    subject: str
    message: str
    data: Optional[dict] = None

class EmailNotification(BaseModel):
    to_email: EmailStr
    subject: str
    body: str

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(get_redis_url())
    return redis_client

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)

async def get_user_email(user_id: int, token: str) -> Optional[str]:
    """Get user email from user service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{USER_SERVICE_URL}/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("email")
    except:
        pass
    return None

async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email notification"""
    try:
        message = MIMEMultipart()
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "html"))
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            use_tls=True
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

async def send_websocket_notification(user_id: int, notification_data: dict):
    """Send WebSocket notification to user"""
    if user_id in websocket_connections:
        message = json.dumps(notification_data)
        disconnected = []
        
        for websocket in websocket_connections[user_id]:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            websocket_connections[user_id].remove(ws)

async def process_execution_notification(execution_data: dict):
    """Process execution and send notifications to users"""
    try:
        buyer_id = execution_data["buyer_id"]
        seller_id = execution_data["seller_id"]
        symbol = execution_data["symbol"]
        quantity = execution_data["quantity"]
        price = execution_data["price"]
        
        # Create notifications for both buyer and seller
        notifications = [
            {
                "user_id": buyer_id,
                "type": "order_filled",
                "title": "Order Filled",
                "message": f"Your BUY order for {quantity} {symbol} at ${price} has been filled",
                "data": execution_data,
                "timestamp": datetime.now().isoformat()
            },
            {
                "user_id": seller_id,
                "type": "order_filled",
                "title": "Order Filled", 
                "message": f"Your SELL order for {quantity} {symbol} at ${price} has been filled",
                "data": execution_data,
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # Send WebSocket notifications
        for notification in notifications:
            await send_websocket_notification(notification["user_id"], notification)
        
        # TODO: Send email notifications if user has email preferences enabled
        
    except Exception as e:
        print(f"Error processing execution notification: {e}")

async def subscribe_to_executions():
    """Subscribe to execution stream for notifications"""
    redis_conn = await get_redis()
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe("executions")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                execution_data = json.loads(message["data"])
                await process_execution_notification(execution_data)
            except Exception as e:
                print(f"Error processing execution notification: {e}")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time notifications"""
    await websocket.accept()
    websocket_connections[user_id].append(websocket)
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected to notification service",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text(json.dumps({
                "type": "pong", 
                "data": data,
                "timestamp": datetime.now().isoformat()
            }))
            
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in websocket_connections[user_id]:
            websocket_connections[user_id].remove(websocket)

@app.post("/send-notification")
async def send_notification(
    notification: NotificationCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Send a notification to a user"""
    
    user_data = verify_token(credentials.credentials)
    
    # Send WebSocket notification
    websocket_data = {
        "type": notification.type,
        "title": notification.subject,
        "message": notification.message,
        "data": notification.data,
        "timestamp": datetime.now().isoformat()
    }
    
    await send_websocket_notification(notification.user_id, websocket_data)
    
    return {"message": "Notification sent successfully"}

@app.post("/send-email")
async def send_email_notification(
    email_notification: EmailNotification,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Send email notification"""
    
    user_data = verify_token(credentials.credentials)
    
    success = await send_email(
        email_notification.to_email,
        email_notification.subject,
        email_notification.body
    )
    
    if success:
        return {"message": "Email sent successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )

@app.post("/order-status-update")
async def notify_order_status_update(
    order_id: str,
    user_id: int,
    status: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Notify user of order status update"""
    
    user_data = verify_token(credentials.credentials)
    
    notification = {
        "type": "order_status",
        "title": "Order Status Update",
        "message": f"Your order {order_id} status has changed to {status}",
        "data": {
            "order_id": order_id,
            "status": status
        },
        "timestamp": datetime.now().isoformat()
    }
    
    await send_websocket_notification(user_id, notification)
    
    return {"message": "Order status notification sent"}

@app.get("/user-connections/{user_id}")
async def get_user_connections(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get number of active connections for a user"""
    
    user_data = verify_token(credentials.credentials)
    
    connection_count = len(websocket_connections.get(user_id, []))
    
    return {
        "user_id": user_id,
        "active_connections": connection_count
    }

@app.get("/system-notifications")
async def get_system_notifications():
    """Get system-wide notifications"""
    
    # This could be enhanced to return actual system notifications
    # from a database or Redis
    
    return {
        "notifications": [
            {
                "type": "system",
                "title": "System Status",
                "message": "All systems operational",
                "timestamp": datetime.now().isoformat()
            }
        ]
    }

@app.post("/broadcast")
async def broadcast_notification(
    message: str,
    title: str = "System Notification",
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Broadcast notification to all connected users"""
    
    user_data = verify_token(credentials.credentials)
    
    notification = {
        "type": "broadcast",
        "title": title,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    # Send to all connected users
    for user_id, connections in websocket_connections.items():
        if connections:  # Only if user has active connections
            await send_websocket_notification(user_id, notification)
    
    total_users = len([user_id for user_id, connections in websocket_connections.items() if connections])
    
    return {
        "message": "Broadcast sent successfully",
        "users_notified": total_users
    }

@app.get("/stats")
async def get_notification_stats():
    """Get notification service statistics"""
    
    total_connections = sum(len(connections) for connections in websocket_connections.values())
    active_users = len([user_id for user_id, connections in websocket_connections.items() if connections])
    
    return {
        "total_connections": total_connections,
        "active_users": active_users,
        "connected_users": list(websocket_connections.keys())
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_connections": sum(len(connections) for connections in websocket_connections.values())
    }

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    # Start Redis subscriber for executions
    asyncio.create_task(subscribe_to_executions())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9243)