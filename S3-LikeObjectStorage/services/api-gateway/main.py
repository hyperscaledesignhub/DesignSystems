#!/usr/bin/env python3
"""
API Gateway Service - Routes requests to appropriate microservices
Port: 7841
"""

import asyncio
import time
from typing import Dict, List, Optional
from collections import defaultdict
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI(title="S3 API Gateway", version="1.0.0")

# CORS configuration for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service discovery - in production use service mesh or k8s DNS
SERVICES = {
    "identity": "http://identity-service:7851",
    "bucket": "http://bucket-service:7861", 
    "object": "http://object-service:7871",
    "storage": "http://storage-service:7881",
    "metadata": "http://metadata-service:7891"
}

# Rate limiting storage
rate_limits: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

class RateLimiter:
    @staticmethod
    def is_rate_limited(client_ip: str) -> bool:
        now = time.time()
        # Clean old requests
        rate_limits[client_ip] = [
            req_time for req_time in rate_limits[client_ip] 
            if now - req_time < RATE_LIMIT_WINDOW
        ]
        
        if len(rate_limits[client_ip]) >= RATE_LIMIT_REQUESTS:
            return True
            
        rate_limits[client_ip].append(now)
        return False

async def verify_auth(request: Request) -> dict:
    """Verify authentication with identity service"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SERVICES['identity']}/auth/validate",
                headers={"Authorization": auth_header},
                timeout=5.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid authentication")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Authentication service unavailable")

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    if RateLimiter.is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    """Gateway health check"""
    return {"status": "healthy", "service": "api-gateway"}

@app.get("/buckets")
async def list_buckets(request: Request, user: dict = Depends(verify_auth)):
    """List user's buckets"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['bucket']}/buckets",
                headers={"X-User-ID": user["user_id"]},
                timeout=10.0
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Bucket service unavailable")

@app.post("/buckets")
async def create_bucket(request: Request, user: dict = Depends(verify_auth)):
    """Create new bucket"""
    body = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SERVICES['bucket']}/buckets",
                json=body,
                headers={"X-User-ID": user["user_id"]},
                timeout=10.0
            )
            if response.status_code == 201:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Bucket service unavailable")

@app.delete("/buckets/{bucket_name}")
async def delete_bucket(bucket_name: str, user: dict = Depends(verify_auth)):
    """Delete bucket"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{SERVICES['bucket']}/buckets/{bucket_name}",
                headers={"X-User-ID": user["user_id"]},
                timeout=10.0
            )
            if response.status_code == 204:
                return {"message": "Bucket deleted successfully"}
            raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Bucket service unavailable")

@app.put("/buckets/{bucket_name}/objects/{object_key:path}")
async def upload_object(
    bucket_name: str, 
    object_key: str, 
    request: Request,
    user: dict = Depends(verify_auth)
):
    """Upload object to bucket"""
    # Stream the request body to object service
    async with httpx.AsyncClient() as client:
        try:
            content = await request.body()
            response = await client.put(
                f"{SERVICES['object']}/buckets/{bucket_name}/objects/{object_key}",
                content=content,
                headers={
                    "X-User-ID": user["user_id"],
                    "Content-Type": request.headers.get("Content-Type", "application/octet-stream")
                },
                timeout=30.0
            )
            if response.status_code == 201:
                return response.json()
            raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Object service unavailable")

@app.get("/buckets/{bucket_name}/objects/{object_key:path}")
async def download_object(
    bucket_name: str,
    object_key: str, 
    user: dict = Depends(verify_auth)
):
    """Download object from bucket"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['object']}/buckets/{bucket_name}/objects/{object_key}",
                headers={"X-User-ID": user["user_id"]},
                timeout=30.0
            )
            if response.status_code == 200:
                return StreamingResponse(
                    iter([response.content]),
                    media_type=response.headers.get("content-type", "application/octet-stream"),
                    headers={
                        "Content-Length": response.headers.get("content-length", "0"),
                        "ETag": response.headers.get("etag", "")
                    }
                )
            raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Object service unavailable")

@app.delete("/buckets/{bucket_name}/objects/{object_key:path}")
async def delete_object(
    bucket_name: str,
    object_key: str,
    user: dict = Depends(verify_auth)
):
    """Delete object from bucket"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{SERVICES['object']}/buckets/{bucket_name}/objects/{object_key}",
                headers={"X-User-ID": user["user_id"]},
                timeout=10.0
            )
            if response.status_code == 204:
                return {"message": "Object deleted successfully"}
            raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Object service unavailable")

@app.get("/buckets/{bucket_name}/objects")
async def list_objects(
    bucket_name: str,
    prefix: Optional[str] = None,
    user: dict = Depends(verify_auth)
):
    """List objects in bucket"""
    params = {}
    if prefix:
        params["prefix"] = prefix
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SERVICES['object']}/buckets/{bucket_name}/objects",
                params=params,
                headers={"X-User-ID": user["user_id"]},
                timeout=10.0
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Object service unavailable")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7841)