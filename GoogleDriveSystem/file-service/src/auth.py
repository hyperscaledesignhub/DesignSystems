import httpx
import os
from fastapi import HTTPException, Header
from typing import Optional

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:9011")

async def verify_auth_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        token = authorization.replace("Bearer ", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AUTH_SERVICE_URL}/verify/{token}")
            if response.status_code == 200:
                data = response.json()
                return data["user_id"]
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token verification failed")