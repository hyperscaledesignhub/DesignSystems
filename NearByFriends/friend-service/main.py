from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import jwt
import asyncpg
import os
from contextlib import asynccontextmanager

app = FastAPI(title="Friend Service", version="1.0.0")
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
ALGORITHM = "HS256"

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost/nearbyfriendsdb")

db_pool = None

class FriendRequest(BaseModel):
    friend_id: int

class FriendResponse(BaseModel):
    user_id: int
    friend_id: int
    created_at: datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = await asyncpg.create_pool(POSTGRES_URL)
    
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS friendships (
                user_id INTEGER NOT NULL,
                friend_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, friend_id)
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS friend_requests (
                requester_id INTEGER NOT NULL,
                requested_id INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (requester_id, requested_id)
            )
        ''')
    
    yield
    
    await db_pool.close()

app = FastAPI(title="Friend Service", version="1.0.0", lifespan=lifespan)

def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/friends/add")
async def add_friend(
    request: FriendRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    payload = verify_token(credentials)
    user_id = payload['user_id']
    
    if user_id == request.friend_id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as friend")
    
    async with db_pool.acquire() as conn:
        try:
            async with conn.transaction():
                await conn.execute('''
                    INSERT INTO friendships (user_id, friend_id)
                    VALUES ($1, $2), ($2, $1)
                ''', user_id, request.friend_id)
                
                await conn.execute('''
                    UPDATE friend_requests
                    SET status = 'accepted'
                    WHERE (requester_id = $1 AND requested_id = $2)
                       OR (requester_id = $2 AND requested_id = $1)
                ''', user_id, request.friend_id)
                
            return {"message": "Friend added successfully"}
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Already friends")

@app.delete("/friends/{friend_id}")
async def remove_friend(
    friend_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    payload = verify_token(credentials)
    user_id = payload['user_id']
    
    async with db_pool.acquire() as conn:
        result = await conn.execute('''
            DELETE FROM friendships
            WHERE (user_id = $1 AND friend_id = $2)
               OR (user_id = $2 AND friend_id = $1)
        ''', user_id, friend_id)
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Friend not found")
        
        return {"message": "Friend removed successfully"}

@app.get("/friends/{user_id}")
async def get_friends(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_token(credentials)
    
    async with db_pool.acquire() as conn:
        results = await conn.fetch('''
            SELECT friend_id, created_at
            FROM friendships
            WHERE user_id = $1
            ORDER BY created_at DESC
        ''', user_id)
        
        return [dict(row) for row in results]

@app.get("/friends/check/{user_id}/{friend_id}")
async def check_friendship(
    user_id: int,
    friend_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_token(credentials)
    
    async with db_pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT EXISTS(
                SELECT 1 FROM friendships
                WHERE user_id = $1 AND friend_id = $2
            )
        ''', user_id, friend_id)
        
        return {"are_friends": result}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "friend-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8902)