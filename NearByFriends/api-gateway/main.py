from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
import httpx
import os
import time
import redis
from typing import Optional

app = FastAPI(title="API Gateway", version="1.0.0")
security = HTTPBearer()

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8901")
FRIEND_SERVICE_URL = os.getenv("FRIEND_SERVICE_URL", "http://friend-service:8902")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://location-service:8903")
WEBSOCKET_GATEWAY_URL = os.getenv("WEBSOCKET_GATEWAY_URL", "http://websocket-gateway:8904")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = redis.from_url(REDIS_URL)

RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60

class RateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
    
    def is_allowed(self, key: str) -> bool:
        current_time = int(time.time())
        window_start = current_time - self.window
        
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, self.window)
        
        results = pipe.execute()
        request_count = results[1]
        
        return request_count < self.requests

rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host

async def proxy_request(
    url: str,
    method: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None
):
    headers = dict(request.headers)
    if credentials:
        headers["Authorization"] = f"Bearer {credentials.credentials}"
    
    if hasattr(request, "_body"):
        body = request._body
    else:
        body = await request.body()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
        return response

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = get_client_ip(request)
    rate_limit_key = f"rate_limit:{client_ip}"
    
    if not rate_limiter.is_allowed(rate_limit_key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )
    
    response = await call_next(request)
    return response

@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(path: str, request: Request):
    url = f"{USER_SERVICE_URL}/auth/{path}"
    response = await proxy_request(url, request.method, request)
    return response.json()

@app.api_route("/api/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def users_proxy(
    path: str, 
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    url = f"{USER_SERVICE_URL}/users/{path}"
    response = await proxy_request(url, request.method, request, credentials)
    return response.json()

@app.api_route("/api/friends/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def friends_proxy(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    url = f"{FRIEND_SERVICE_URL}/friends/{path}"
    response = await proxy_request(url, request.method, request, credentials)
    return response.json()

@app.api_route("/api/location/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def location_proxy(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    url = f"{LOCATION_SERVICE_URL}/location/{path}"
    response = await proxy_request(url, request.method, request, credentials)
    return response.json()

@app.get("/")
async def root():
    return {"message": "Nearby Friends API Gateway", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    services = {
        "user-service": f"{USER_SERVICE_URL}/health",
        "friend-service": f"{FRIEND_SERVICE_URL}/health",
        "location-service": f"{LOCATION_SERVICE_URL}/health",
        "websocket-gateway": f"{WEBSOCKET_GATEWAY_URL}/health"
    }
    
    health_status = {"gateway": "healthy", "services": {}}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, health_url in services.items():
            try:
                response = await client.get(health_url)
                if response.status_code == 200:
                    health_status["services"][service_name] = "healthy"
                else:
                    health_status["services"][service_name] = "unhealthy"
            except Exception:
                health_status["services"][service_name] = "unreachable"
    
    all_healthy = all(status == "healthy" for status in health_status["services"].values())
    overall_status = "healthy" if all_healthy else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        **health_status
    }

@app.get("/metrics")
async def metrics():
    return {
        "active_connections": len(redis_client.keys("rate_limit:*")),
        "total_requests": "See individual service metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)