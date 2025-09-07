from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
from typing import Optional
import uvicorn

from database import get_db, engine
from models import User, Base
from schemas import UserCreate, UserLogin, UserResponse, Token
from auth import get_password_hash, verify_password, create_access_token, verify_token

app = FastAPI(title="Auth Service", version="1.0.0")
security = HTTPBearer()

Base.metadata.create_all(bind=engine)

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        user_id=str(db_user.user_id),
        email=db_user.email,
        username=db_user.username,
        created_at=db_user.created_at
    )

@app.post("/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": str(db_user.user_id)})
    return Token(access_token=access_token, token_type="bearer")

@app.post("/logout")
async def logout():
    return {"message": "Successfully logged out"}

@app.get("/profile", response_model=UserResponse)
async def get_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        user_id=str(db_user.user_id),
        email=db_user.email,
        username=db_user.username,
        created_at=db_user.created_at
    )

@app.put("/profile", response_model=UserResponse)
async def update_profile(
    username: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.username = username
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        user_id=str(db_user.user_id),
        email=db_user.email,
        username=db_user.username,
        created_at=db_user.created_at
    )

@app.get("/lookup", response_model=UserResponse)
async def lookup_user(
    q: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if q is an email or user_id
    if '@' in q:
        db_user = db.query(User).filter(User.email == q).first()
    else:
        db_user = db.query(User).filter(User.user_id == q).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        user_id=str(db_user.user_id),
        email=db_user.email,
        username=db_user.username,
        created_at=db_user.created_at
    )

@app.get("/verify/{token}")
async def verify_user_token(token: str):
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user_id": user_id, "valid": True}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
