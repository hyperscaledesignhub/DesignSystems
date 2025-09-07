from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import time
import json
import uvicorn
import os
from typing import Dict, Any

from auth import authenticate_request, get_token_from_request
from rate_limiter import rate_limiter
from load_balancer import load_balancer

app = FastAPI(title="API Gateway", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    print(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    print(f"Response: {response.status_code} in {process_time:.4f}s")
    
    return response

# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip auth for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Skip auth for health checks and public endpoints
    public_paths = ["/health", "/docs", "/openapi.json", "/auth/register", "/auth/login", "/gateway/services"]
    
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Check authentication
    user_id = await authenticate_request(request)
    if not user_id:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required"}
        )
    
    # Add user_id to request state
    request.state.user_id = user_id
    
    return await call_next(request)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Get identifier for rate limiting (user_id or IP)
    identifier = getattr(request.state, 'user_id', request.client.host)
    
    # Check rate limit
    if await rate_limiter.is_rate_limited(identifier):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"},
            headers={
                "X-RateLimit-Limit": str(rate_limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "60"
            }
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    rate_info = await rate_limiter.get_rate_limit_info(identifier)
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(rate_info["requests_remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["window_reset"])
    
    return response

async def proxy_request(
    request: Request,
    service_name: str,
    path_override: str = None,
    load_balance_strategy: str = "round_robin"
) -> StreamingResponse:
    """Proxy request to backend service"""
    
    # Get service URL with load balancing
    user_id = getattr(request.state, 'user_id', None)
    service_url = load_balancer.get_service_url(service_name, load_balance_strategy, user_id)
    
    # Build target URL
    target_path = path_override or request.url.path
    if target_path.startswith(f"/{service_name}/"):
        target_path = target_path[len(f"/{service_name}"):]
    
    target_url = f"{service_url}{target_path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    # Prepare headers (forward most headers, but clean up some)
    headers = dict(request.headers)
    headers.pop("host", None)
    
    try:
        async with httpx.AsyncClient() as client:
            # Handle different HTTP methods
            if request.method == "GET":
                response = await client.get(target_url, headers=headers)
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(target_url, headers=headers, content=body)
            elif request.method == "PUT":
                body = await request.body()
                response = await client.put(target_url, headers=headers, content=body)
            elif request.method == "DELETE":
                response = await client.delete(target_url, headers=headers)
            else:
                body = await request.body()
                response = await client.request(
                    request.method, target_url, headers=headers, content=body
                )
        
        # Return streaming response to handle large files
        return StreamingResponse(
            content=iter([response.content]),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )
        
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )

# Route: Auth Service
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(request: Request, path: str):
    return await proxy_request(request, "auth", f"/{path}")

# Route: File Service - List files
@app.api_route("/files", methods=["GET"])
async def file_list_proxy(request: Request):
    return await proxy_request(request, "file", "/files")

# Route: File Service - Upload (special case)
@app.api_route("/files/upload", methods=["POST"])
async def file_upload_proxy(request: Request):
    return await proxy_request(request, "file", "/upload", "hash")

# Route: File Service - Other operations  
@app.api_route("/files/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def file_proxy(request: Request, path: str):
    return await proxy_request(request, "file", f"/files/{path}", "hash")  # Use hash-based LB for file affinity

# Route: Metadata Service
@app.api_route("/metadata/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def metadata_proxy(request: Request, path: str):
    return await proxy_request(request, "metadata", f"/{path}")

# Route: Block Service
@app.api_route("/blocks/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def block_proxy(request: Request, path: str):
    return await proxy_request(request, "block", f"/{path}", "hash")  # Use hash-based LB

# Route: Notification Service
@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def notification_proxy(request: Request, path: str):
    return await proxy_request(request, "notification", f"/{path}")

# Gateway-specific endpoints
@app.get("/health")
async def health_check():
    """Gateway health check"""
    service_stats = load_balancer.get_service_stats()
    
    return {
        "status": "healthy",
        "service": "api-gateway",
        "services": service_stats,
        "rate_limiter": "enabled" if rate_limiter else "disabled"
    }

@app.get("/gateway/stats")
async def gateway_stats(request: Request):
    """Get gateway statistics"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    rate_info = await rate_limiter.get_rate_limit_info(user_id)
    
    return {
        "rate_limit": rate_info,
        "services": load_balancer.get_service_stats(),
        "load_balancer": "enabled",
        "authentication": "enabled"
    }

@app.get("/gateway/services")
async def service_status():
    """Get status of all backend services"""
    services_health = {}
    
    for service_name in load_balancer.services:
        services_health[service_name] = load_balancer.health_check(service_name)
    
    return services_health

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)