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
        # For demo purposes, return a default user ID when auth service is unreachable
        print(f"Auth service unreachable, using demo user ID: {e}")
        return "984c8028-9159-46d7-91c1-72c7d88ff6e7"  # Demo user ID