import os
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
from datetime import datetime, timedelta
from jose import jwt, JWTError
import hashlib

app = FastAPI(title="API Gateway")
security = HTTPBearer(auto_error=False)

# Environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "23450"))
ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "30"))

# Service registry
SERVICES = {
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:23451"),
    "game": os.getenv("GAME_SERVICE_URL", "http://localhost:23452"),
    "leaderboard": os.getenv("LEADERBOARD_SERVICE_URL", "http://localhost:23453"),
    "score": os.getenv("SCORE_SERVICE_URL", "http://localhost:23454")
}

# Rate limit configuration
RATE_LIMITS = {
    "default": {"requests": 100, "window": 60},
    "leaderboard_top": {"requests": 300, "window": 60},
    "game_end": {"requests": 50, "window": 60}
}

redis_client = None

# Pydantic models
class ErrorResponse(BaseModel):
    error: dict

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
async def check_rate_limit(request: Request, user_id: str = None, endpoint: str = "default"):
    if not ENABLE_RATE_LIMIT:
        return True
    
    # Get rate limit config
    config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    limit = config["requests"]
    window = config["window"]
    
    # Create key for rate limiting
    client_ip = request.client.host
    if user_id:
        key = f"rate:user:{user_id}:{int(datetime.utcnow().timestamp() / window)}"
    else:
        key = f"rate:ip:{client_ip}:{int(datetime.utcnow().timestamp() / window)}"
    
    # Check current count
    current = await redis_client.get(key)
    if current and int(current) >= limit:
        return False
    
    # Increment counter
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    await pipe.execute()
    
    return True

def verify_jwt_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user_id")
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    
    token = credentials.credentials
    user_id = verify_jwt_token(token)
    return user_id

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = credentials.credentials
    user_id = verify_jwt_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    return user_id

async def proxy_request(service: str, path: str, method: str, headers: dict = None, json_data=None, params=None):
    service_url = SERVICES.get(service)
    if not service_url:
        raise HTTPException(status_code=404, detail="Service not found")
    
    url = f"{service_url}{path}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=json_data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=json_data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            return response.json(), response.status_code
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

# Routes

# Public routes (no auth required)
@app.post("/api/v1/auth/register")
async def register(request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    body = await request.json()
    data, status_code = await proxy_request("user", "/api/v1/users/register", "POST", json_data=body)
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

@app.post("/api/v1/auth/login")
async def login(request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    body = await request.json()
    data, status_code = await proxy_request("user", "/api/v1/users/login", "POST", json_data=body)
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

# Protected routes (auth required)
@app.get("/api/v1/profile/{user_id}")
async def get_profile(user_id: str, request: Request, current_user: str = Depends(require_auth)):
    if not await check_rate_limit(request, current_user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Check cache first
    cache_key = f"profile:{user_id}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    data, status_code = await proxy_request("user", f"/api/v1/users/{user_id}", "GET")
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    # Cache for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps(data))
    
    return data

@app.post("/api/v1/game/start")
async def start_game(request: Request, current_user: str = Depends(require_auth)):
    if not await check_rate_limit(request, current_user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    body = await request.json()
    body["user_id"] = current_user  # Ensure user_id matches auth
    
    # Forward auth token
    auth_header = {"Authorization": request.headers.get("Authorization")}
    data, status_code = await proxy_request("game", "/api/v1/games/match/start", "POST", headers=auth_header, json_data=body)
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

@app.post("/api/v1/game/end")
async def end_game(request: Request, current_user: str = Depends(require_auth)):
    if not await check_rate_limit(request, current_user, "game_end"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    body = await request.json()
    body["user_id"] = current_user  # Ensure user_id matches auth
    
    # Forward auth token
    auth_header = {"Authorization": request.headers.get("Authorization")}
    data, status_code = await proxy_request("game", "/api/v1/games/match/end", "POST", headers=auth_header, json_data=body)
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

@app.get("/api/v1/leaderboard/top")
async def get_leaderboard(request: Request, current_user: str = Depends(get_current_user)):
    if not await check_rate_limit(request, current_user, "leaderboard_top"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Check cache first
    cache_key = "leaderboard:top10"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    data, status_code = await proxy_request("leaderboard", "/api/v1/leaderboard/top", "GET")
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    # Cache for 30 seconds
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
    
    return data

@app.get("/api/v1/leaderboard/rank/{user_id}")
async def get_user_rank(user_id: str, request: Request, current_user: str = Depends(require_auth)):
    if not await check_rate_limit(request, current_user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    data, status_code = await proxy_request("leaderboard", f"/api/v1/leaderboard/rank/{user_id}", "GET")
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

@app.get("/api/v1/leaderboard/around/{user_id}")
async def get_relative_leaderboard(user_id: str, request: Request, current_user: str = Depends(require_auth)):
    if not await check_rate_limit(request, current_user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    data, status_code = await proxy_request("leaderboard", f"/api/v1/leaderboard/around/{user_id}", "GET")
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

@app.get("/api/v1/scores/{user_id}")
async def get_user_scores(user_id: str, request: Request, current_user: str = Depends(require_auth)):
    if not await check_rate_limit(request, current_user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    data, status_code = await proxy_request("score", f"/api/v1/scores/{user_id}", "GET")
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

@app.get("/api/v1/scores/{user_id}/history")
async def get_score_history(user_id: str, request: Request, current_user: str = Depends(require_auth)):
    if not await check_rate_limit(request, current_user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    data, status_code = await proxy_request("score", f"/api/v1/scores/{user_id}/history", "GET")
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data)
    
    return data

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}

@app.on_event("startup")
async def startup_event():
    global redis_client
    redis_client = redis.Redis.from_url(REDIS_URL)

@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)