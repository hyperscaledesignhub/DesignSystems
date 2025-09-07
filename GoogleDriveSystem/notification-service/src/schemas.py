from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class NotificationCreate(BaseModel):
    user_id: str
    type: str
    message: str
    data: Optional[Dict[str, Any]] = None

class NotificationResponse(BaseModel):
    notification_id: uuid.UUID
    user_id: str
    type: str
    message: str
    data: Optional[Dict[str, Any]]
    read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationHistory(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int

class UserStatusUpdate(BaseModel):
    status: str  # online, offline

class UserStatusResponse(BaseModel):
    user_id: str
    status: str
    last_seen: datetime
    connection_id: Optional[str]
    
    class Config:
        from_attributes = True

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]