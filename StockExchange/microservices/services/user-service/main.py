import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
import uvicorn

from shared.models.base import User
from shared.utils.database import DatabaseManager, get_database_url
from shared.utils.auth import (
    verify_password, get_password_hash, create_access_token, verify_token
)
from models import UserDB
from shared.tracing import setup_tracing, instrument_fastapi, TracingMiddleware

tracer = setup_tracing("user-service")
app = FastAPI(title="User Service", version="1.0.0")
instrument_fastapi(app)
app.add_middleware(TracingMiddleware, service_name="user-service")
security = HTTPBearer()

# Database setup
db_manager = DatabaseManager(get_database_url("user"))

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

async def get_db():
    async for session in db_manager.get_session():
        yield session

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token_data = verify_token(credentials.credentials)
    user_id = token_data["user_id"]
    
    result = await db.execute(select(UserDB).where(UserDB.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@app.post("/register", response_model=User)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(
        select(UserDB).where(
            (UserDB.email == user_data.email) | 
            (UserDB.username == user_data.username)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = UserDB(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return User(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        is_active=db_user.is_active,
        created_at=db_user.created_at
    )

@app.post("/login", response_model=Token)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserDB).where(UserDB.username == user_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=User)
async def read_users_me(current_user: UserDB = Depends(get_current_user)):
    return User(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8975)