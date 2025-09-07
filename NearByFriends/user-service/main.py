from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
import asyncpg
import redis
import os
from contextlib import asynccontextmanager

app = FastAPI(title="User Service", version="1.0.0")
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost/nearbyfriendsdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = None
db_pool = None

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    username: str
    location_sharing_enabled: bool
    created_at: datetime

class LocationSharingUpdate(BaseModel):
    enabled: bool

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(POSTGRES_URL)
    redis_client = redis.from_url(REDIS_URL)
    
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                location_sharing_enabled BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    yield
    
    await db_pool.close()

app = FastAPI(title="User Service", version="1.0.0", lifespan=lifespan)

def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/register")
async def register(user: UserRegister):
    password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    async with db_pool.acquire() as conn:
        try:
            result = await conn.fetchrow('''
                INSERT INTO users (username, password_hash)
                VALUES ($1, $2)
                RETURNING user_id, username, location_sharing_enabled, created_at
            ''', user.username, password_hash)
            
            token = create_token(result['user_id'], result['username'])
            
            return {
                "token": token,
                "user": dict(result)
            }
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Username already exists")

@app.post("/auth/login")
async def login(user: UserLogin):
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('''
            SELECT user_id, username, password_hash, location_sharing_enabled, created_at
            FROM users
            WHERE username = $1
        ''', user.username)
        
        if not result:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not bcrypt.checkpw(user.password.encode('utf-8'), result['password_hash'].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token(result['user_id'], result['username'])
        
        await redis_client.setex(
            f"session:{result['user_id']}", 
            TOKEN_EXPIRE_HOURS * 3600,
            token
        )
        
        return {
            "token": token,
            "user": {
                "user_id": result['user_id'],
                "username": result['username'],
                "location_sharing_enabled": result['location_sharing_enabled'],
                "created_at": result['created_at']
            }
        }

@app.get("/users/{user_id}")
async def get_user(user_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    verify_token(credentials)
    
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('''
            SELECT user_id, username, location_sharing_enabled, created_at
            FROM users
            WHERE user_id = $1
        ''', user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        return dict(result)

@app.put("/users/{user_id}/location-sharing")
async def update_location_sharing(
    user_id: int,
    update: LocationSharingUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    payload = verify_token(credentials)
    
    if payload['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Can only update own settings")
    
    async with db_pool.acquire() as conn:
        await conn.execute('''
            UPDATE users
            SET location_sharing_enabled = $1
            WHERE user_id = $2
        ''', update.enabled, user_id)
        
        return {"message": "Location sharing updated successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8901)