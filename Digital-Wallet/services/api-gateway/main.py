from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import sys
import os
import httpx
import time
import redis
from typing import Dict, Any
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.utils.logger import setup_logger

app = FastAPI(title="API Gateway", version="1.0.0")
logger = setup_logger("api-gateway")
security = HTTPBearer()

# Service URLs
SERVICES = {
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:9081"),
    "wallet": os.getenv("WALLET_SERVICE_URL", "http://localhost:9082"),
    "transaction": os.getenv("TRANSACTION_SERVICE_URL", "http://localhost:9083"),
    "state": os.getenv("STATE_SERVICE_URL", "http://localhost:9084"),
    "event": os.getenv("EVENT_SERVICE_URL", "http://localhost:9085"),
}

# Redis for rate limiting
redis_client = None
try:
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
except Exception as e:
    logger.warning(f"Redis not available for rate limiting: {e}")

# Rate limiting configuration
RATE_LIMITS = {
    "default": {"requests": 100, "window": 60},  # 100 requests per minute
    "auth": {"requests": 10, "window": 60},      # 10 auth requests per minute
    "transfers": {"requests": 10, "window": 60}, # 10 transfers per minute
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

async def check_rate_limit(request: Request, limit_type: str = "default") -> bool:
    if not redis_client:
        return True  # Skip rate limiting if Redis is not available
    
    client_ip = get_client_ip(request)
    limit_config = RATE_LIMITS.get(limit_type, RATE_LIMITS["default"])
    
    key = f"rate_limit:{limit_type}:{client_ip}"
    current_time = int(time.time())
    window_start = current_time - limit_config["window"]
    
    try:
        # Clean old entries
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        current_requests = redis_client.zcard(key)
        
        if current_requests >= limit_config["requests"]:
            return False
        
        # Add current request
        redis_client.zadd(key, {str(current_time): current_time})
        redis_client.expire(key, limit_config["window"])
        
        return True
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        return True  # Allow request if rate limiting fails

async def proxy_request(
    service_name: str, 
    path: str, 
    method: str, 
    request: Request,
    **kwargs
) -> Dict[str, Any]:
    service_url = SERVICES.get(service_name)
    if not service_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Service {service_name} not available"
        )
    
    url = f"{service_url}{path}"
    headers = dict(request.headers)
    
    # Remove host header to avoid conflicts
    headers.pop("host", None)
    
    # Debug logging
    logger.info(f"Proxying {method} request to {url}")
    logger.info(f"Headers: {headers}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=request.query_params)
            elif method == "POST":
                body = await request.body()
                logger.info(f"POST Body: {body[:200]}")  # Log first 200 chars of body
                response = await client.post(url, headers=headers, content=body)
            elif method == "PUT":
                body = await request.body()
                logger.info(f"PUT Body: {body[:200]}")  # Log first 200 chars of body
                response = await client.put(url, headers=headers, content=body)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                    detail="Method not allowed"
                )
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text
            }
    
    except httpx.RequestError as e:
        logger.error(f"Request to {service_name} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Service {service_name} unavailable"
        )
    except httpx.TimeoutException:
        logger.error(f"Request to {service_name} timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Service {service_name} timeout"
        )

# Authentication endpoints
@app.post("/api/v1/auth/register")
async def register_user(request: Request):
    if not await check_rate_limit(request, "auth"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("user", "/v1/users/register", "POST", request)
    if result["status_code"] >= 400:
        raise HTTPException(status_code=result["status_code"], detail=result["content"])
    return json.loads(result["content"]) if result["content"] else {}

@app.post("/api/v1/auth/login")
async def login_user(request: Request):
    if not await check_rate_limit(request, "auth"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("user", "/v1/users/login", "POST", request)
    if result["status_code"] >= 400:
        raise HTTPException(status_code=result["status_code"], detail=result["content"])
    return json.loads(result["content"]) if result["content"] else {}

# User endpoints
@app.get("/api/v1/users/{user_id}/profile")
async def get_user_profile(user_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("user", f"/v1/users/{user_id}/profile", "GET", request)
    return json.loads(result["content"])

@app.put("/api/v1/users/{user_id}/status")
async def update_user_status(user_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("user", f"/v1/users/{user_id}/status", "PUT", request)
    return json.loads(result["content"])

# Wallet endpoints
@app.post("/api/v1/wallets")
async def create_wallet(request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("wallet", "/v1/wallets/create", "POST", request)
    return json.loads(result["content"])

@app.get("/api/v1/wallets/{wallet_id}/balance")
async def get_wallet_balance(wallet_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("wallet", f"/v1/wallets/{wallet_id}/balance", "GET", request)
    return json.loads(result["content"])

@app.get("/api/v1/wallets/user/{user_id}")
async def get_user_wallets(user_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("wallet", f"/v1/wallets/user/{user_id}", "GET", request)
    return json.loads(result["content"])

@app.put("/api/v1/wallets/{wallet_id}/status")
async def update_wallet_status(wallet_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("wallet", f"/v1/wallets/{wallet_id}/status", "PUT", request)
    return json.loads(result["content"])

# Transaction endpoints
@app.post("/api/v1/transfers")
async def create_transfer(request: Request):
    if not await check_rate_limit(request, "transfers"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Transfer rate limit exceeded"
        )
    
    result = await proxy_request("transaction", "/v1/transactions/transfer", "POST", request)
    if result["status_code"] >= 400:
        raise HTTPException(status_code=result["status_code"], detail=result["content"])
    return json.loads(result["content"]) if result["content"] else {}

@app.post("/api/v1/deposits")
async def create_deposit(request: Request):
    if not await check_rate_limit(request, "transfers"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Transfer rate limit exceeded"
        )
    
    result = await proxy_request("transaction", "/v1/transactions/deposit", "POST", request)
    if result["status_code"] >= 400:
        raise HTTPException(status_code=result["status_code"], detail=result["content"])
    return json.loads(result["content"]) if result["content"] else {}

@app.post("/api/v1/withdrawals")
async def create_withdrawal(request: Request):
    if not await check_rate_limit(request, "transfers"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Transfer rate limit exceeded"
        )
    
    result = await proxy_request("transaction", "/v1/transactions/withdraw", "POST", request)
    if result["status_code"] >= 400:
        raise HTTPException(status_code=result["status_code"], detail=result["content"])
    return json.loads(result["content"]) if result["content"] else {}

@app.get("/api/v1/transfers/{transaction_id}")
async def get_transaction(transaction_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("transaction", f"/v1/transactions/{transaction_id}", "GET", request)
    return json.loads(result["content"])

@app.get("/api/v1/transfers/wallet/{wallet_id}")
async def get_wallet_transactions(wallet_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("transaction", f"/v1/transactions/wallet/{wallet_id}", "GET", request)
    return json.loads(result["content"])

# State endpoints (internal/admin)
@app.get("/api/v1/state/wallet/{wallet_id}/balance")
async def get_state_balance(wallet_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("state", f"/v1/state/wallet/{wallet_id}/balance", "GET", request)
    return json.loads(result["content"])

@app.get("/api/v1/state/stats")
async def get_state_stats(request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("state", "/v1/state/stats", "GET", request)
    return json.loads(result["content"])

# Event endpoints (internal/admin)
@app.get("/api/v1/events/wallet/{wallet_id}")
async def get_wallet_events(wallet_id: str, request: Request):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    result = await proxy_request("event", f"/v1/events/wallet/{wallet_id}", "GET", request)
    return json.loads(result["content"])

# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}

@app.get("/api/v1/health/services")
async def services_health_check():
    health_status = {"gateway": "healthy"}
    
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service_url}/health")
                if response.status_code == 200:
                    health_status[service_name] = "healthy"
                else:
                    health_status[service_name] = "unhealthy"
        except Exception as e:
            health_status[service_name] = "unavailable"
            logger.error(f"Health check failed for {service_name}: {e}")
    
    # Determine overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in health_status.values()
    ) else "degraded"
    
    return {
        "status": overall_status,
        "services": health_status,
        "timestamp": time.time()
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint was not found",
            "path": str(request.url.path)
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    logger.info("API Gateway starting on port 9080")
    uvicorn.run(app, host="0.0.0.0", port=9080)