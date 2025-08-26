from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.models.base import User, UserRegistration, UserLogin
from shared.utils.auth import verify_password, get_password_hash, create_access_token, verify_token
from shared.utils.database import db_pool, get_database_url
from shared.utils.logger import setup_logger
from uuid import UUID
import asyncio

app = FastAPI(title="User Service", version="1.0.0")
logger = setup_logger("user-service")
security = HTTPBearer()

@app.on_event("startup")
async def startup():
    database_url = get_database_url("user-service")
    await db_pool.create_pool(database_url)
    await create_tables()
    logger.info("User Service started on port 9081")

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close_pool()

async def create_tables():
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(255) NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """
    await db_pool.execute(create_users_table)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = await get_user_by_id(UUID(token_data["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

async def get_user_by_email(email: str):
    query = "SELECT * FROM users WHERE email = $1"
    row = await db_pool.fetchrow(query, email)
    if row:
        return User(**dict(row))
    return None

async def get_user_by_id(user_id: UUID):
    query = "SELECT * FROM users WHERE id = $1"
    row = await db_pool.fetchrow(query, user_id)
    if row:
        return User(**dict(row))
    return None

@app.post("/v1/users/register")
async def register_user(user_data: UserRegistration):
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )
    
    query = """
    INSERT INTO users (id, email, password_hash, full_name, status, created_at, updated_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    """
    await db_pool.execute(
        query, user.id, user.email, user.password_hash, 
        user.full_name, user.status, user.created_at, user.updated_at
    )
    
    logger.info(f"User registered: {user.email}")
    return {"message": "User registered successfully", "user_id": str(user.id)}

@app.post("/v1/users/login")
async def login_user(login_data: UserLogin):
    user = await get_user_by_email(login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info(f"User logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id)
    }

@app.get("/v1/users/{user_id}/profile")
async def get_user_profile(user_id: UUID, current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "status": current_user.status,
        "created_at": current_user.created_at
    }

@app.put("/v1/users/{user_id}/status")
async def update_user_status(
    user_id: UUID, 
    status_data: dict,
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    new_status = status_data.get("status")
    if new_status not in ["active", "inactive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status"
        )
    
    query = "UPDATE users SET status = $1, updated_at = NOW() WHERE id = $2"
    await db_pool.execute(query, new_status, user_id)
    
    logger.info(f"User status updated: {user_id} -> {new_status}")
    return {"message": "Status updated successfully"}

@app.get("/v1/users/validate/{user_id}")
async def validate_user(user_id: UUID):
    user = await get_user_by_id(user_id)
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive"
        )
    
    return {"valid": True, "user_id": str(user.id)}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9081)