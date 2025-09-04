from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import redis
import os
import time
import json
from typing import Optional

app = FastAPI(title="API Gateway", version="1.0.0")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)
security = HTTPBearer(auto_error=False)

SERVICE_URLS = {
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:8371"),
    "post": os.getenv("POST_SERVICE_URL", "http://localhost:8372"),
    "graph": os.getenv("GRAPH_SERVICE_URL", "http://localhost:8373"),
    "fanout": os.getenv("FANOUT_SERVICE_URL", "http://localhost:8374"),
    "newsfeed": os.getenv("NEWSFEED_SERVICE_URL", "http://localhost:8375"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8376")
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_service_url(path: str) -> str:
    if path.startswith("/api/v1/auth") or path.startswith("/api/v1/users"):
        return SERVICE_URLS["user"]
    elif path.startswith("/api/v1/posts"):
        return SERVICE_URLS["post"]
    elif path.startswith("/api/v1/graph"):
        return SERVICE_URLS["graph"]
    elif path.startswith("/api/v1/fanout"):
        return SERVICE_URLS["fanout"]
    elif path.startswith("/api/v1/feed"):
        return SERVICE_URLS["newsfeed"]
    elif path.startswith("/api/v1/notifications"):
        return SERVICE_URLS["notification"]
    else:
        raise HTTPException(status_code=404, detail="Service not found")

def rate_limit_check(client_ip: str, limit: int = 100, window: int = 60) -> bool:
    key = f"rate_limit:{client_ip}"
    current = redis_client.get(key)
    
    if current is None:
        redis_client.setex(key, window, 1)
        return True
    
    if int(current) >= limit:
        return False
    
    redis_client.incr(key)
    return True

async def proxy_request(request: Request, target_url: str):
    client_ip = request.client.host
    
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    headers = dict(request.headers)
    headers.pop("host", None)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if request.method == "GET":
                response = await client.get(
                    f"{target_url}{request.url.path}",
                    params=request.query_params,
                    headers=headers
                )
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(
                    f"{target_url}{request.url.path}",
                    content=body,
                    headers=headers
                )
            elif request.method == "PUT":
                body = await request.body()
                response = await client.put(
                    f"{target_url}{request.url.path}",
                    content=body,
                    headers=headers
                )
            elif request.method == "DELETE":
                response = await client.delete(
                    f"{target_url}{request.url.path}",
                    headers=headers
                )
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            return {
                "status_code": response.status_code,
                "content": response.content,
                "headers": dict(response.headers)
            }
        
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Service unavailable")

@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_proxy(request: Request):
    service_url = get_service_url(request.url.path)
    result = await proxy_request(request, service_url)
    
    from fastapi.responses import Response
    return Response(
        content=result["content"],
        status_code=result["status_code"],
        headers=dict(result["headers"])
    )

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/services/status")
async def services_status():
    status = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICE_URLS.items():
            try:
                response = await client.get(f"{service_url}/health")
                status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": service_url
                }
            except httpx.RequestError:
                status[service_name] = {
                    "status": "unreachable",
                    "url": service_url
                }
    
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8370)