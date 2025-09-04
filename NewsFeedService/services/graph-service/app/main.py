from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, create_engine, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import redis
import httpx
import os
import json

app = FastAPI(title="Graph Service", version="1.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/graphdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8371")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
redis_client = redis.from_url(REDIS_URL)
security = HTTPBearer()

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    friend_id = Column(Integer, index=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class FriendshipCreate(BaseModel):
    user_id: int
    friend_id: int

class FriendshipResponse(BaseModel):
    user_id: int
    friend_id: int
    status: str
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

@app.post("/api/v1/graph/friends")
async def create_friendship(friendship: FriendshipCreate, user_data: dict = Depends(validate_token), db: Session = Depends(get_db)):
    existing = db.query(Relationship).filter(
        and_(Relationship.user_id == friendship.user_id, Relationship.friend_id == friendship.friend_id)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Friendship already exists")
    
    relationship = Relationship(user_id=friendship.user_id, friend_id=friendship.friend_id)
    reverse_relationship = Relationship(user_id=friendship.friend_id, friend_id=friendship.user_id)
    
    db.add(relationship)
    db.add(reverse_relationship)
    db.commit()
    
    redis_client.delete(f"friends:{friendship.user_id}")
    redis_client.delete(f"friends:{friendship.friend_id}")
    
    return {"message": "Friendship created successfully"}

@app.delete("/api/v1/graph/friends")
async def delete_friendship(friendship: FriendshipCreate, user_data: dict = Depends(validate_token), db: Session = Depends(get_db)):
    relationship = db.query(Relationship).filter(
        and_(Relationship.user_id == friendship.user_id, Relationship.friend_id == friendship.friend_id)
    ).first()
    
    reverse_relationship = db.query(Relationship).filter(
        and_(Relationship.user_id == friendship.friend_id, Relationship.friend_id == friendship.user_id)
    ).first()
    
    if relationship:
        db.delete(relationship)
    if reverse_relationship:
        db.delete(reverse_relationship)
    
    db.commit()
    
    redis_client.delete(f"friends:{friendship.user_id}")
    redis_client.delete(f"friends:{friendship.friend_id}")
    
    return {"message": "Friendship deleted successfully"}

@app.get("/api/v1/graph/users/{user_id}/friends")
def get_friends(user_id: int, db: Session = Depends(get_db)):
    cached_friends = redis_client.get(f"friends:{user_id}")
    if cached_friends:
        return json.loads(cached_friends)
    
    relationships = db.query(Relationship).filter(Relationship.user_id == user_id).all()
    friend_ids = [rel.friend_id for rel in relationships]
    
    redis_client.setex(f"friends:{user_id}", 300, json.dumps(friend_ids))
    return friend_ids

@app.get("/api/v1/graph/users/{user_id}/friends/check/{friend_id}")
def check_friendship(user_id: int, friend_id: int, db: Session = Depends(get_db)):
    relationship = db.query(Relationship).filter(
        and_(Relationship.user_id == user_id, Relationship.friend_id == friend_id)
    ).first()
    
    return {"is_friend": relationship is not None}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8373)