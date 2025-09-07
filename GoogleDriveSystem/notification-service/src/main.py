from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime
import uvicorn

from database import get_db, engine
from models import Notification, UserStatus, Base
from schemas import (
    NotificationCreate, NotificationResponse, NotificationHistory,
    UserStatusUpdate, UserStatusResponse
)
from auth import verify_auth_token, verify_token_sync
from websocket_manager import manager

app = FastAPI(title="Notification Service", version="1.0.0")

Base.metadata.create_all(bind=engine)

# WebSocket endpoint for real-time notifications
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str):
    # Verify token for WebSocket connection
    verified_user_id = verify_token_sync(token)
    if not verified_user_id or verified_user_id != user_id:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Connect user
    await manager.connect(websocket, user_id)
    
    # Update user status to online
    db = next(get_db())
    user_status = db.query(UserStatus).filter(UserStatus.user_id == user_id).first()
    if user_status:
        user_status.status = "online"
        user_status.last_seen = datetime.utcnow()
        user_status.connection_id = str(id(websocket))
    else:
        user_status = UserStatus(
            user_id=user_id,
            status="online",
            connection_id=str(id(websocket))
        )
        db.add(user_status)
    db.commit()
    db.close()
    
    try:
        # Send welcome message
        await manager.send_personal_json({
            "type": "connection_established",
            "message": f"Connected to notification service",
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle ping/pong for connection health
            if message_data.get("type") == "ping":
                await manager.send_personal_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, user_id)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
        # Update user status to offline
        db = next(get_db())
        user_status = db.query(UserStatus).filter(UserStatus.user_id == user_id).first()
        if user_status:
            if not manager.is_user_online(user_id):  # Check if no other connections
                user_status.status = "offline"
                user_status.last_seen = datetime.utcnow()
                user_status.connection_id = None
        db.commit()
        db.close()

@app.post("/notify")
async def send_notification(
    notification: NotificationCreate,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Send a notification to a user"""
    
    # Store notification in database
    db_notification = Notification(
        user_id=notification.user_id,
        type=notification.type,
        message=notification.message,
        data=notification.data
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    
    # Send real-time notification if user is online
    if manager.is_user_online(notification.user_id):
        await manager.send_personal_json({
            "type": "notification",
            "data": {
                "notification_id": str(db_notification.notification_id),
                "type": notification.type,
                "message": notification.message,
                "data": notification.data,
                "created_at": db_notification.created_at.isoformat()
            }
        }, notification.user_id)
    
    return {"message": "Notification sent", "notification_id": str(db_notification.notification_id)}

@app.get("/notifications/{user_id}", response_model=NotificationHistory)
async def get_notifications(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Get notification history for a user"""
    
    # Users can only access their own notifications
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get notifications
    notifications = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    
    # Get total count and unread count
    total = db.query(Notification).filter(Notification.user_id == user_id).count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.read == False
    ).count()
    
    return NotificationHistory(
        notifications=[NotificationResponse.from_orm(n) for n in notifications],
        total=total,
        unread_count=unread_count
    )

@app.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    
    notification = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == user_id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.read = True
    db.commit()
    
    return {"message": "Notification marked as read"}

@app.put("/status/{user_id}")
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    current_user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Update user online/offline status"""
    
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_status = db.query(UserStatus).filter(UserStatus.user_id == user_id).first()
    if user_status:
        user_status.status = status_update.status
        user_status.last_seen = datetime.utcnow()
    else:
        user_status = UserStatus(
            user_id=user_id,
            status=status_update.status
        )
        db.add(user_status)
    
    db.commit()
    
    return {"message": "Status updated"}

@app.get("/status/{user_id}", response_model=UserStatusResponse)
async def get_user_status(
    user_id: str,
    current_user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Get user online/offline status"""
    
    user_status = db.query(UserStatus).filter(UserStatus.user_id == user_id).first()
    if not user_status:
        # Create default offline status
        user_status = UserStatus(user_id=user_id, status="offline")
        db.add(user_status)
        db.commit()
        db.refresh(user_status)
    
    # Update with real-time status from WebSocket connections
    if manager.is_user_online(user_id):
        user_status.status = "online"
    
    return user_status

@app.get("/online-users")
async def get_online_users(user_id: str = Depends(verify_auth_token)):
    """Get list of currently online users"""
    return {"online_users": manager.get_online_users()}

@app.post("/broadcast")
async def broadcast_notification(
    message: str,
    user_id: str = Depends(verify_auth_token)
):
    """Broadcast message to all connected users (admin only)"""
    await manager.broadcast_message(json.dumps({
        "type": "broadcast",
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    return {"message": "Broadcast sent"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "notification-service",
        "active_connections": len(manager.active_connections),
        "online_users": len(manager.get_online_users())
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)