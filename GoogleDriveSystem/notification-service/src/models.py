from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # file_upload, file_delete, file_share, etc
    message = Column(Text, nullable=False)
    data = Column(JSONB, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserStatus(Base):
    __tablename__ = "user_status"
    
    user_id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default="offline")  # online, offline
    last_seen = Column(DateTime, default=datetime.utcnow)
    connection_id = Column(String, nullable=True)