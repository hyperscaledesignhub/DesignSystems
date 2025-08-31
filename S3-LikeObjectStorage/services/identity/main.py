#!/usr/bin/env python3
"""
Identity Service - Authentication and authorization
Port: 7851
"""

import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Database setup
DB_PATH = os.getenv("DB_PATH", "/data/identity.db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    init_database()
    yield

app = FastAPI(title="S3 Identity Service", version="1.0.0", lifespan=lifespan)

# CORS configuration for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    user_id: str
    permissions: dict = {"buckets": ["READ", "WRITE"], "objects": ["READ", "WRITE"]}

class AuthRequest(BaseModel):
    api_key: str
    resource: str
    action: str

def init_database():
    """Initialize SQLite database with users table"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            api_key TEXT UNIQUE NOT NULL,
            permissions TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create default admin user if not exists
    admin_api_key = generate_api_key()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, api_key, permissions) 
        VALUES (?, ?, ?)
    """, ("admin", admin_api_key, '{"buckets": ["READ", "WRITE"], "objects": ["READ", "WRITE"]}'))
    
    conn.commit()
    conn.close()
    
    print(f"Admin API Key: {admin_api_key}")

def generate_api_key() -> str:
    """Generate secure API key"""
    return f"s3_key_{secrets.token_urlsafe(32)}"

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

@app.get("/health")
async def health_check():
    """Service health check"""
    return {"status": "healthy", "service": "identity"}

@app.post("/users")
async def create_user(user_data: UserCreate, db = Depends(get_db)):
    """Create new user with API key"""
    try:
        api_key = generate_api_key()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO users (user_id, api_key, permissions) 
            VALUES (?, ?, ?)
        """, (user_data.user_id, api_key, str(user_data.permissions)))
        
        db.commit()
        
        return {
            "user_id": user_data.user_id,
            "api_key": api_key,
            "permissions": user_data.permissions
        }
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="User already exists")

@app.get("/users/{user_id}")
async def get_user(user_id: str, db = Depends(get_db)):
    """Get user information (without API key)"""
    cursor = db.cursor()
    cursor.execute("SELECT user_id, permissions, created_at FROM users WHERE user_id = ?", (user_id,))
    
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    
    return dict(row)

@app.delete("/users/{user_id}")
async def delete_user(user_id: str, db = Depends(get_db)):
    """Delete user"""
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.commit()
    return {"message": "User deleted successfully"}

@app.post("/auth/validate")
async def validate_auth(authorization: str = Header(...), db = Depends(get_db)):
    """Validate API key and return user info"""
    try:
        # Extract API key from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        api_key = authorization.replace("Bearer ", "")
        
        cursor = db.cursor()
        cursor.execute("""
            SELECT user_id, permissions FROM users WHERE api_key = ?
        """, (api_key,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        user_data = dict(row)
        # Parse permissions JSON string back to dict
        import json
        user_data["permissions"] = json.loads(user_data["permissions"])
        
        return user_data
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.post("/auth/check-permission")
async def check_permission(
    resource: str,
    action: str,
    authorization: str = Header(...),
    db = Depends(get_db)
):
    """Check if user has permission for specific action"""
    # First validate the user
    user_data = await validate_auth(authorization, db)
    
    # Check permissions
    permissions = user_data.get("permissions", {})
    
    # Simple permission check - in production this would be more sophisticated
    if resource in permissions:
        allowed_actions = permissions[resource]
        if action in allowed_actions:
            return {"allowed": True, "user_id": user_data["user_id"]}
    
    return {"allowed": False, "user_id": user_data["user_id"]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7851)