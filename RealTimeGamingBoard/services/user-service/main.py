import os
import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.hash import bcrypt
from jose import jwt, JWTError
import uuid
from datetime import datetime, timedelta
import json

# Import local tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing first
tracer = setup_tracing("user-service")

app = FastAPI(title="User Service")

# Instrument FastAPI app for tracing
instrument_fastapi(app)
security = HTTPBearer()

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/gaming")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "23451"))

# Database connection
db_pool = None
redis_client = None

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenValidate(BaseModel):
    token: str

class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    created_at: datetime

class TokenResponse(BaseModel):
    user_id: str
    auth_token: str

# Database functions
async def init_db():
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    redis_client = redis.Redis.from_url(REDIS_URL)
    
    # Create tables
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            
            CREATE TABLE IF NOT EXISTS users (
                user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_email ON users(email);
        ''')

def create_jwt_token(user_id: str) -> str:
    expires = datetime.utcnow() + timedelta(hours=24)
    payload = {
        "user_id": user_id,
        "exp": expires
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user_id")
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id = verify_jwt_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user_id

# Routes
@app.post("/api/v1/users/register", response_model=TokenResponse)
async def register_user(user_data: UserRegister):
    with tracer.start_as_current_span("register_user", attributes=create_span_attributes(
        operation="user_registration",
        username=user_data.username,
        email=user_data.email
    )) as span:
        try:
            hashed_password = bcrypt.hash(user_data.password)
            display_name = user_data.username
            
            async with db_pool.acquire() as conn:
                user_id = await conn.fetchval('''
                    INSERT INTO users (username, email, password_hash, display_name)
                    VALUES ($1, $2, $3, $4)
                    RETURNING user_id::text
                ''', user_data.username, user_data.email, hashed_password, display_name)
                
            span.set_attributes(create_span_attributes(
                user_id=user_id,
                registration_success=True
            ))
            
            token = create_jwt_token(user_id)
            return TokenResponse(user_id=user_id, auth_token=token)
            
        except asyncpg.UniqueViolationError:
            span.set_attributes(create_span_attributes(
                registration_success=False,
                error="duplicate_user"
            ))
            raise HTTPException(status_code=400, detail="Username or email already exists")

@app.post("/api/v1/users/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    with tracer.start_as_current_span("login_user", attributes=create_span_attributes(
        operation="user_login",
        username=login_data.username
    )) as span:
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow('''
                SELECT user_id::text, password_hash
                FROM users
                WHERE username = $1
            ''', login_data.username)
            
        if not user or not bcrypt.verify(login_data.password, user['password_hash']):
            span.set_attributes(create_span_attributes(
                login_success=False,
                error="invalid_credentials"
            ))
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        span.set_attributes(create_span_attributes(
            user_id=user['user_id'],
            login_success=True
        ))
        
        token = create_jwt_token(user['user_id'])
        return TokenResponse(user_id=user['user_id'], auth_token=token)

@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user_profile(user_id: str):
    with tracer.start_as_current_span("get_user_profile", attributes=create_span_attributes(
        operation="user_profile_fetch",
        user_id=user_id
    )) as span:
        # Check Redis cache first
        cached_user = await redis_client.get(f"user:profile:{user_id}")
        if cached_user:
            span.set_attributes(create_span_attributes(
                cache_hit=True
            ))
            return UserResponse(**json.loads(cached_user))
        
        span.set_attributes(create_span_attributes(
            cache_hit=False
        ))
        
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow('''
                SELECT user_id::text, username, display_name, created_at
                FROM users
                WHERE user_id = $1::uuid
            ''', user_id)
            
        if not user:
            span.set_attributes(create_span_attributes(
                user_found=False
            ))
            raise HTTPException(status_code=404, detail="User not found")
        
        span.set_attributes(create_span_attributes(
            user_found=True,
            username=user['username']
        ))
        
        user_data = {
            "user_id": user['user_id'],
            "username": user['username'],
            "display_name": user['display_name'],
            "created_at": user['created_at'].isoformat()
        }
        
        # Cache for 5 minutes
        await redis_client.setex(f"user:profile:{user_id}", 300, json.dumps(user_data, default=str))
        
        return UserResponse(**user_data)

@app.post("/api/v1/users/validate")
async def validate_token(token_data: TokenValidate):
    with tracer.start_as_current_span("validate_token", attributes=create_span_attributes(
        operation="token_validation"
    )) as span:
        user_id = verify_jwt_token(token_data.token)
        if not user_id:
            span.set_attributes(create_span_attributes(
                token_valid=False
            ))
            raise HTTPException(status_code=401, detail="Invalid token")
        
        span.set_attributes(create_span_attributes(
            token_valid=True,
            user_id=user_id
        ))
        return {"user_id": user_id}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-service"}

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)