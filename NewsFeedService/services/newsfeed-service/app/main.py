from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List
import redis
import httpx
import os
import json
from datetime import datetime

app = FastAPI(title="News Feed Service", version="1.0.0")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
POST_SERVICE_URL = os.getenv("POST_SERVICE_URL", "http://localhost:8372")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8371")

redis_client = redis.from_url(REDIS_URL)
security = HTTPBearer()

class PostResponse(BaseModel):
    id: int
    user_id: int
    username: str
    content: str
    created_at: datetime

class FeedResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    has_more: bool

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

async def fetch_post_details(post_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{POST_SERVICE_URL}/api/v1/posts/{post_id}")
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError:
            pass
    return None

async def fetch_user_details(user_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{USER_SERVICE_URL}/api/v1/users/{user_id}")
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError:
            pass
    return {"username": f"User{user_id}"}

@app.get("/api/v1/feed/{user_id}", response_model=FeedResponse)
async def get_user_feed(user_id: int, limit: int = 20, offset: int = 0, user_data: dict = Depends(validate_token)):
    if user_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    feed_key = f"feed:{user_id}"
    post_ids = redis_client.lrange(feed_key, offset, offset + limit - 1)
    
    if not post_ids:
        return FeedResponse(posts=[], total=0, has_more=False)
    
    posts = []
    for post_id in post_ids:
        post_id = int(post_id.decode())
        post_data = await fetch_post_details(post_id)
        
        if post_data:
            user_details = await fetch_user_details(post_data["user_id"])
            
            posts.append(PostResponse(
                id=post_data["id"],
                user_id=post_data["user_id"],
                username=user_details.get("username", f"User{post_data['user_id']}"),
                content=post_data["content"],
                created_at=datetime.fromisoformat(post_data["created_at"].replace("Z", "+00:00"))
            ))
    
    total_count = redis_client.llen(feed_key)
    has_more = offset + len(posts) < total_count
    
    return FeedResponse(posts=posts, total=total_count, has_more=has_more)

@app.get("/api/v1/feed/{user_id}/refresh")
async def refresh_feed(user_id: int, user_data: dict = Depends(validate_token)):
    if user_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    feed_key = f"feed:{user_id}"
    redis_client.delete(feed_key)
    
    async with httpx.AsyncClient() as client:
        try:
            graph_response = await client.get(f"http://localhost:8373/api/v1/graph/users/{user_id}/friends")
            if graph_response.status_code == 200:
                friend_ids = graph_response.json()
                
                all_posts = []
                for friend_id in friend_ids[:10]:
                    posts_response = await client.get(f"{POST_SERVICE_URL}/api/v1/users/{friend_id}/posts?limit=5")
                    if posts_response.status_code == 200:
                        friend_posts = posts_response.json()
                        all_posts.extend([(post["id"], post["created_at"]) for post in friend_posts])
                
                all_posts.sort(key=lambda x: x[1], reverse=True)
                
                for post_id, _ in all_posts[:100]:
                    redis_client.lpush(feed_key, post_id)
                
                redis_client.expire(feed_key, 3600)
        
        except httpx.RequestError:
            pass
    
    return {"message": "Feed refreshed successfully"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8375)