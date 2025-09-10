import os
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="User Database Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    country_code = Column(String(5), default="1")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    devices = relationship("Device", back_populates="user")

class Device(Base):
    __tablename__ = "devices"
    
    device_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    device_token = Column(String(512), nullable=False)
    device_type = Column(String(20), nullable=False)  # ios, android
    last_active = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="devices")

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    raise

# Pydantic Models
class UserCreate(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: str = "1"

class UserUpdate(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: Optional[str] = None

class UserResponse(BaseModel):
    user_id: int
    email: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class DeviceCreate(BaseModel):
    device_token: str
    device_type: str  # ios, android

class DeviceResponse(BaseModel):
    device_id: int
    user_id: int
    device_token: str
    device_type: str
    last_active: datetime
    
    class Config:
        from_attributes = True

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    try:
        # Test database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "status": "healthy", 
            "service": "user-database",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "service": "user-database", 
            "error": str(e)
        }

# User endpoints
@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if not user.email and not user.phone_number:
        raise HTTPException(status_code=400, detail="Either email or phone number is required")
    
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

# Device endpoints
@app.get("/users/{user_id}/devices", response_model=List[DeviceResponse])
async def get_user_devices(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    devices = db.query(Device).filter(Device.user_id == user_id).all()
    return devices

@app.post("/users/{user_id}/devices", response_model=DeviceResponse)
async def create_device(user_id: int, device: DeviceCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if device.device_type not in ["ios", "android"]:
        raise HTTPException(status_code=400, detail="Device type must be 'ios' or 'android'")
    
    # Check if device token already exists for this user
    existing_device = db.query(Device).filter(
        Device.user_id == user_id,
        Device.device_token == device.device_token
    ).first()
    
    if existing_device:
        # Update existing device
        existing_device.device_type = device.device_type
        existing_device.last_active = datetime.utcnow()
        db.commit()
        db.refresh(existing_device)
        return existing_device
    
    # Create new device
    db_device = Device(
        user_id=user_id,
        device_token=device.device_token,
        device_type=device.device_type
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7846))
    uvicorn.run(app, host="0.0.0.0", port=port)