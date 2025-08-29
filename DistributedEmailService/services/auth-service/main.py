from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
import sys
import uuid
from typing import Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import UserCreate, UserLogin, UserResponse, TokenResponse
from shared.database import db_pool, init_database
from shared.tracing import setup_tracing, instrument_fastapi, create_span_attributes

tracer = setup_tracing("auth-service")

app = FastAPI(title="Authentication Service", version="1.0.0")
instrument_fastapi(app)

security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "demo-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

@app.on_event("startup")
async def startup_event():
    await init_database()
    print("Auth Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    await db_pool.disconnect()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.post("/auth/register", response_model=TokenResponse)
async def register(user: UserCreate):
    with tracer.start_as_current_span("register_user", attributes=create_span_attributes(
        email=user.email,
        role=user.role
    )):
        existing = await db_pool.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            user.email
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        password_hash = hash_password(user.password)
        
        new_user = await db_pool.fetchrow(
            """
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES ($1, $2, $3, $4)
            RETURNING id, email, full_name, role, created_at, is_active, storage_used, storage_limit
            """,
            user.email, password_hash, user.full_name, user.role
        )
        
        token = create_token(str(new_user['id']), new_user['email'])
        
        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=str(new_user['id']),
                email=new_user['email'],
                full_name=new_user['full_name'],
                role=new_user['role'],
                created_at=new_user['created_at'],
                is_active=new_user['is_active'],
                storage_used=new_user['storage_used'],
                storage_limit=new_user['storage_limit']
            )
        )

@app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    with tracer.start_as_current_span("login_user", attributes=create_span_attributes(
        email=credentials.email
    )):
        user = await db_pool.fetchrow(
            """
            SELECT id, email, password_hash, full_name, role, created_at, 
                   is_active, storage_used, storage_limit
            FROM users WHERE email = $1 AND is_active = true
            """,
            credentials.email
        )
        
        if not user or not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        token = create_token(str(user['id']), user['email'])
        
        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=str(user['id']),
                email=user['email'],
                full_name=user['full_name'],
                role=user['role'],
                created_at=user['created_at'],
                is_active=user['is_active'],
                storage_used=user['storage_used'],
                storage_limit=user['storage_limit']
            )
        )

@app.get("/auth/validate")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    with tracer.start_as_current_span("validate_token"):
        payload = verify_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user = await db_pool.fetchrow(
            """
            SELECT id, email, full_name, role, created_at, 
                   is_active, storage_used, storage_limit
            FROM users WHERE id = $1::uuid AND is_active = true
            """,
            payload['user_id']
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return {
            "user_id": str(user['id']),
            "email": user['email'],
            "full_name": user['full_name'],
            "role": user['role']
        }

@app.post("/auth/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    with tracer.start_as_current_span("refresh_token"):
        payload = verify_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        new_token = create_token(payload['user_id'], payload['email'])
        
        return {"access_token": new_token}

@app.get("/auth/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    with tracer.start_as_current_span("get_user", attributes=create_span_attributes(
        user_id=user_id
    )):
        payload = verify_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = await db_pool.fetchrow(
            """
            SELECT id, email, full_name, role, created_at, 
                   is_active, storage_used, storage_limit
            FROM users WHERE id = $1::uuid
            """,
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=str(user['id']),
            email=user['email'],
            full_name=user['full_name'],
            role=user['role'],
            created_at=user['created_at'],
            is_active=user['is_active'],
            storage_used=user['storage_used'],
            storage_limit=user['storage_limit']
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth-service", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)