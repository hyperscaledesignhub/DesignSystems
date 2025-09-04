from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
import redis
import httpx
import os
import json

app = FastAPI(title="Post Service", version="1.0.0")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/postdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8371")
FANOUT_SERVICE_URL = os.getenv("FANOUT_SERVICE_URL", "http://localhost:8374")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
redis_client = redis.from_url(REDIS_URL)
security = HTTPBearer()

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class PostCreate(BaseModel):
    content: str

class PostResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime
    updated_at: datetime

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

@app.post("/api/v1/posts", response_model=PostResponse)
async def create_post(post: PostCreate, user_data: dict = Depends(validate_token), db: Session = Depends(get_db)):
    db_post = Post(user_id=user_data["user_id"], content=post.content)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    redis_client.setex(f"post:{db_post.id}", 3600, json.dumps({
        "id": db_post.id,
        "user_id": db_post.user_id,
        "content": db_post.content,
        "created_at": db_post.created_at.isoformat(),
        "updated_at": db_post.updated_at.isoformat()
    }))
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{FANOUT_SERVICE_URL}/api/v1/fanout/distribute",
                json={"post_id": db_post.id, "user_id": db_post.user_id}
            )
        except httpx.RequestError:
            pass
    
    return db_post

@app.get("/api/v1/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    cached_post = redis_client.get(f"post:{post_id}")
    if cached_post:
        post_data = json.loads(cached_post)
        return PostResponse(**post_data)
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    redis_client.setex(f"post:{post_id}", 3600, json.dumps({
        "id": post.id,
        "user_id": post.user_id,
        "content": post.content,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat()
    }))
    
    return post

@app.get("/api/v1/users/{user_id}/posts")
def get_user_posts(user_id: int, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.user_id == user_id).order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
    return [PostResponse(
        id=post.id,
        user_id=post.user_id,
        content=post.content,
        created_at=post.created_at,
        updated_at=post.updated_at
    ) for post in posts]

@app.delete("/api/v1/posts/{post_id}")
async def delete_post(post_id: int, user_data: dict = Depends(validate_token), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(post)
    db.commit()
    redis_client.delete(f"post:{post_id}")
    return {"message": "Post deleted successfully"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8372)