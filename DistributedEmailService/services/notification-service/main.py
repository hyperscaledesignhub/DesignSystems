from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime
import os
import sys
import uuid
import json
from typing import Dict, List
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import NotificationCreate, NotificationResponse, NotificationType
from shared.database import db_pool, init_database
from shared.tracing import setup_tracing, instrument_fastapi, create_span_attributes

tracer = setup_tracing("notification-service")

app = FastAPI(title="Notification Service", version="1.0.0")
instrument_fastapi(app)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    await init_database()
    print("Notification Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    await db_pool.disconnect()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app.post("/notifications", response_model=NotificationResponse)
async def create_notification(notification: NotificationCreate):
    with tracer.start_as_current_span("create_notification", attributes=create_span_attributes(
        user_id=notification.user_id,
        type=notification.type,
        priority=notification.priority
    )):
        result = await db_pool.fetchrow(
            """
            INSERT INTO notifications (user_id, type, title, message, data)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            uuid.UUID(notification.user_id),
            notification.type,
            notification.title,
            notification.message,
            json.dumps(notification.data or {})
        )
        
        response = NotificationResponse(
            id=str(result['id']),
            user_id=str(result['user_id']),
            type=result['type'],
            title=result['title'],
            message=result['message'],
            data=json.loads(result['data']) if isinstance(result['data'], str) else result['data'],
            is_read=result['is_read'],
            created_at=result['created_at']
        )
        
        await manager.send_to_user(notification.user_id, {
            "type": "notification",
            "data": {
                "id": response.id,
                "type": response.type,
                "title": response.title,
                "message": response.message,
                "created_at": response.created_at.isoformat()
            }
        })
        
        return response

@app.get("/notifications/{user_id}", response_model=List[NotificationResponse])
async def get_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0
):
    with tracer.start_as_current_span("get_notifications", attributes=create_span_attributes(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit
    )):
        query = """
            SELECT * FROM notifications 
            WHERE user_id = $1
        """
        params = [uuid.UUID(user_id)]
        
        if unread_only:
            query += " AND is_read = false"
        
        query += " ORDER BY created_at DESC LIMIT $2 OFFSET $3"
        params.extend([limit, offset])
        
        notifications = await db_pool.fetch(query, *params)
        
        return [
            NotificationResponse(
                id=str(n['id']),
                user_id=str(n['user_id']),
                type=n['type'],
                title=n['title'],
                message=n['message'],
                data=json.loads(n['data']) if isinstance(n['data'], str) else n['data'],
                is_read=n['is_read'],
                created_at=n['created_at']
            )
            for n in notifications
        ]

@app.patch("/notifications/{notification_id}/read")
async def mark_as_read(notification_id: str):
    with tracer.start_as_current_span("mark_notification_read", attributes=create_span_attributes(
        notification_id=notification_id
    )):
        result = await db_pool.execute(
            "UPDATE notifications SET is_read = true WHERE id = $1",
            uuid.UUID(notification_id)
        )
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"message": "Notification marked as read"}

@app.patch("/notifications/user/{user_id}/read-all")
async def mark_all_as_read(user_id: str):
    with tracer.start_as_current_span("mark_all_notifications_read", attributes=create_span_attributes(
        user_id=user_id
    )):
        result = await db_pool.execute(
            "UPDATE notifications SET is_read = true WHERE user_id = $1 AND is_read = false",
            uuid.UUID(user_id)
        )
        
        count = int(result.split()[-1])
        return {"message": f"{count} notifications marked as read"}

@app.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    with tracer.start_as_current_span("delete_notification", attributes=create_span_attributes(
        notification_id=notification_id
    )):
        result = await db_pool.execute(
            "DELETE FROM notifications WHERE id = $1",
            uuid.UUID(notification_id)
        )
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"message": "Notification deleted"}

@app.get("/notifications/user/{user_id}/unread-count")
async def get_unread_count(user_id: str):
    with tracer.start_as_current_span("get_unread_count", attributes=create_span_attributes(
        user_id=user_id
    )):
        count = await db_pool.fetchval(
            "SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND is_read = false",
            uuid.UUID(user_id)
        )
        
        return {"unread_count": count}

@app.post("/notifications/broadcast")
async def broadcast_notification(notification: NotificationCreate):
    with tracer.start_as_current_span("broadcast_notification", attributes=create_span_attributes(
        type=notification.type,
        title=notification.title
    )):
        users = await db_pool.fetch("SELECT id FROM users WHERE is_active = true")
        
        notifications_created = 0
        for user in users:
            await db_pool.execute(
                """
                INSERT INTO notifications (user_id, type, title, message, data)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user['id'],
                notification.type,
                notification.title,
                notification.message,
                json.dumps(notification.data or {})
            )
            notifications_created += 1
            
            await manager.send_to_user(str(user['id']), {
                "type": "notification",
                "data": {
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "created_at": datetime.utcnow().isoformat()
                }
            })
        
        return {"message": f"Broadcast sent to {notifications_created} users"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "notification-service",
        "timestamp": datetime.utcnow(),
        "active_connections": sum(len(conns) for conns in manager.active_connections.values())
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)