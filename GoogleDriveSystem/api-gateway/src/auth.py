from jose import JWTError, jwt
from fastapi import HTTPException, Header, Request
from typing import Optional
import os

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"

def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None

def get_token_from_request(request: Request) -> Optional[str]:
    """Extract token from request headers"""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    return None

async def authenticate_request(request: Request) -> Optional[str]:
    """Authenticate request and return user_id"""
    token = get_token_from_request(request)
    if not token:
        return None
    
    return verify_token(token)