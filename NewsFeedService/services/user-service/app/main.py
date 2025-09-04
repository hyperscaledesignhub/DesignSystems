from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import redis
import httpx
import os

app = FastAPI(title="User Service", version="1.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/userdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8373")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
redis_client = redis.from_url(REDIS_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Friendship(Base):
    __tablename__ = "friendships"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    friend_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    # Convert sub to string as JWT standard expects
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        # Convert back to integer for database lookup
        user_id = int(user_id_str)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def notify_graph_service_friendship(user_id: int, friend_id: int, action: str, token: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            data = {"user_id": user_id, "friend_id": friend_id}
            
            if action == "add":
                response = await client.post(
                    f"{GRAPH_SERVICE_URL}/api/v1/graph/friends",
                    json=data,
                    headers=headers
                )
            elif action == "remove":
                response = await client.delete(
                    f"{GRAPH_SERVICE_URL}/api/v1/graph/friends",
                    json=data,
                    headers=headers
                )
            
            if response.status_code not in [200, 201]:
                print(f"Graph service error: {response.status_code} - {response.text}")
    except httpx.RequestError as e:
        print(f"Failed to notify graph service: {e}")

@app.post("/api/v1/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = hash_password(user.password)
    db_user = User(username=user.username, email=user.email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    token = create_access_token(data={"sub": db_user.id})
    return {"access_token": token, "token_type": "bearer", "user_id": db_user.id}

@app.post("/api/v1/auth/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": db_user.id})
    return {"access_token": token, "token_type": "bearer", "user_id": db_user.id}

@app.get("/api/v1/auth/validate")
def validate_token(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "username": current_user.username}

@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/v1/users/{user_id}/friends/{friend_id}")
async def add_friend(user_id: int, friend_id: int, credentials: HTTPAuthorizationCredentials = Depends(security), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    existing = db.query(Friendship).filter(Friendship.user_id == user_id, Friendship.friend_id == friend_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already friends")
    
    friendship = Friendship(user_id=user_id, friend_id=friend_id)
    reverse_friendship = Friendship(user_id=friend_id, friend_id=user_id)
    db.add(friendship)
    db.add(reverse_friendship)
    db.commit()
    
    # Notify graph service about the new friendship
    await notify_graph_service_friendship(user_id, friend_id, "add", credentials.credentials)
    
    return {"message": "Friend added successfully"}

@app.delete("/api/v1/users/{user_id}/friends/{friend_id}")
async def remove_friend(user_id: int, friend_id: int, credentials: HTTPAuthorizationCredentials = Depends(security), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    friendship = db.query(Friendship).filter(Friendship.user_id == user_id, Friendship.friend_id == friend_id).first()
    reverse_friendship = db.query(Friendship).filter(Friendship.user_id == friend_id, Friendship.friend_id == user_id).first()
    
    if friendship:
        db.delete(friendship)
    if reverse_friendship:
        db.delete(reverse_friendship)
    db.commit()
    
    # Notify graph service about the friendship removal
    await notify_graph_service_friendship(user_id, friend_id, "remove", credentials.credentials)
    
    return {"message": "Friend removed successfully"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8371)