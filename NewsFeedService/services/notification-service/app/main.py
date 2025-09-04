from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List
import redis
import httpx
import os
import json
from datetime import datetime

app = FastAPI(title="Notification Service", version="1.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/notificationdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8371")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
redis_client = redis.from_url(REDIS_URL)
security = HTTPBearer()

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    type = Column(String)
    message = Column(String)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class NotificationCreate(BaseModel):
    user_id: int
    type: str
    message: str

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    message: str
    read: bool
    created_at: datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{USER_SERVICE_URL}/api/v1/auth/validate",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User service unavailable")

@app.post("/api/v1/notifications", response_model=NotificationResponse)
def create_notification(notification: NotificationCreate, db: Session = Depends(get_db)):
    db_notification = Notification(
        user_id=notification.user_id,
        type=notification.type,
        message=notification.message
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    
    redis_client.lpush(f"notifications:{notification.user_id}", json.dumps({
        "id": db_notification.id,
        "type": notification.type,
        "message": notification.message,
        "created_at": db_notification.created_at.isoformat()
    }))
    redis_client.ltrim(f"notifications:{notification.user_id}", 0, 99)
    
    return db_notification

@app.get("/api/v1/notifications/{user_id}", response_model=List[NotificationResponse])
async def get_notifications(user_id: int, limit: int = 20, user_data: dict = Depends(validate_token), db: Session = Depends(get_db)):
    if user_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    notifications = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()
    
    return notifications

@app.put("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, user_data: dict = Depends(validate_token), db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.user_id != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    notification.read = True
    db.commit()
    
    return {"message": "Notification marked as read"}

@app.get("/api/v1/notifications/{user_id}/unread/count")
async def get_unread_count(user_id: int, user_data: dict = Depends(validate_token), db: Session = Depends(get_db)):
    if user_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.read == False
    ).count()
    
    return {"unread_count": count}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8376)