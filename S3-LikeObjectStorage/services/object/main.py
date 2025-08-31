#!/usr/bin/env python3
"""
Object Service - Object operations orchestration
Port: 7871
"""

import hashlib
import uuid
from datetime import datetime
from typing import Optional, List
import httpx
from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="S3 Object Service", version="1.0.0")

# CORS configuration for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service endpoints
BUCKET_SERVICE = "http://bucket-service:7861"
STORAGE_SERVICE = "http://storage-service:7881"  
METADATA_SERVICE = "http://metadata-service:7891"

class ObjectInfo(BaseModel):
    object_id: str
    bucket_name: str
    object_name: str
    size_bytes: int
    content_type: str
    etag: str
    created_at: datetime

def calculate_etag(content: bytes) -> str:
    """Calculate ETag (MD5 hash) for object content"""
    return hashlib.md5(content).hexdigest()

async def verify_bucket_access(bucket_name: str, user_id: str) -> dict:
    """Verify bucket exists and user has access"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BUCKET_SERVICE}/buckets/{bucket_name}/exists")
            bucket_info = response.json()
            
            if not bucket_info.get("exists"):
                raise HTTPException(status_code=404, detail="Bucket not found")
            
            # Simple ownership check
            if bucket_info.get("owner_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied to bucket")
            
            return bucket_info
            
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Bucket service unavailable")

@app.get("/health")
async def health_check():
    """Service health check"""
    return {"status": "healthy", "service": "object"}

@app.put("/buckets/{bucket_name}/objects/{object_key:path}")
async def upload_object(
    bucket_name: str,
    object_key: str,
    request: Request,
    x_user_id: str = Header(..., alias="X-User-ID"),
    content_type: str = Header("application/octet-stream", alias="Content-Type")
):
    """Upload object to bucket"""
    
    # Verify bucket access
    await verify_bucket_access(bucket_name, x_user_id)
    
    # Read request body
    content = await request.body()
    content_length = len(content)
    
    if content_length == 0:
        raise HTTPException(status_code=400, detail="Empty object not allowed")
    
    # Generate object ID and calculate ETag
    object_id = str(uuid.uuid4())
    etag = calculate_etag(content)
    
    # Store data in storage service
    async with httpx.AsyncClient() as client:
        storage_success = False
        try:
            # Upload to storage service
            storage_response = await client.post(
                f"{STORAGE_SERVICE}/data",
                content=content,
                headers={
                    "X-Object-ID": object_id,
                    "X-Content-Type": content_type
                },
                timeout=30.0
            )
            
            if storage_response.status_code != 201:
                raise HTTPException(status_code=500, detail="Failed to store object data")
            
            storage_success = True
            
            # Store metadata
            metadata_payload = {
                "object_id": object_id,
                "bucket_name": bucket_name,
                "object_name": object_key,
                "size_bytes": content_length,
                "content_type": content_type,
                "etag": etag
            }
            
            try:
                metadata_response = await client.post(
                    f"{METADATA_SERVICE}/metadata/objects",
                    json=metadata_payload,
                    timeout=10.0
                )
                
                if metadata_response.status_code != 201:
                    # Rollback storage if metadata creation fails
                    await client.delete(f"{STORAGE_SERVICE}/data/{object_id}")
                    raise HTTPException(status_code=500, detail="Failed to store object metadata")
                    
            except httpx.RequestError as metadata_error:
                # Metadata service unavailable - rollback storage
                if storage_success:
                    try:
                        await client.delete(f"{STORAGE_SERVICE}/data/{object_id}")
                    except:
                        pass  # Rollback failed, but we still need to report the original error
                raise HTTPException(status_code=503, detail=f"Metadata service unavailable: {str(metadata_error)}")
            
            return {
                "object_id": object_id,
                "bucket_name": bucket_name,
                "object_name": object_key,
                "size_bytes": content_length,
                "etag": etag,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except httpx.RequestError as e:
            # Storage service unavailable
            raise HTTPException(status_code=503, detail=f"Storage service unavailable: {str(e)}")

@app.get("/buckets/{bucket_name}/objects/{object_key:path}")
async def download_object(
    bucket_name: str,
    object_key: str,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Download object from bucket"""
    
    # Verify bucket access
    await verify_bucket_access(bucket_name, x_user_id)
    
    async with httpx.AsyncClient() as client:
        try:
            # Get object metadata
            metadata_response = await client.get(
                f"{METADATA_SERVICE}/metadata/buckets/{bucket_name}/objects",
                params={"object_name": object_key},
                timeout=10.0
            )
            
            if metadata_response.status_code == 404:
                raise HTTPException(status_code=404, detail="Object not found")
            
            metadata = metadata_response.json()
            if not metadata:
                raise HTTPException(status_code=404, detail="Object not found")
            
            object_info = metadata[0]  # Get first match
            object_id = object_info["object_id"]
            
            # Get object data from storage
            storage_response = await client.get(
                f"{STORAGE_SERVICE}/data/{object_id}",
                timeout=30.0
            )
            
            if storage_response.status_code == 404:
                raise HTTPException(status_code=404, detail="Object data not found")
            
            # Return streaming response
            return StreamingResponse(
                iter([storage_response.content]),
                media_type=object_info.get("content_type", "application/octet-stream"),
                headers={
                    "Content-Length": str(object_info.get("size_bytes", len(storage_response.content))),
                    "ETag": object_info.get("etag", ""),
                    "Last-Modified": object_info.get("created_at", "")
                }
            )
            
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Storage service unavailable")

@app.delete("/buckets/{bucket_name}/objects/{object_key:path}")
async def delete_object(
    bucket_name: str,
    object_key: str,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Delete object from bucket"""
    
    # Verify bucket access
    await verify_bucket_access(bucket_name, x_user_id)
    
    async with httpx.AsyncClient() as client:
        try:
            # Get object metadata first
            metadata_response = await client.get(
                f"{METADATA_SERVICE}/metadata/buckets/{bucket_name}/objects",
                params={"object_name": object_key},
                timeout=10.0
            )
            
            if metadata_response.status_code == 404:
                raise HTTPException(status_code=404, detail="Object not found")
            
            metadata = metadata_response.json()
            if not metadata:
                raise HTTPException(status_code=404, detail="Object not found")
            
            object_info = metadata[0]
            object_id = object_info["object_id"]
            
            # Delete from metadata service
            delete_metadata_response = await client.delete(
                f"{METADATA_SERVICE}/metadata/objects/{object_id}",
                timeout=10.0
            )
            
            # Delete from storage service (even if metadata deletion fails for cleanup)
            await client.delete(
                f"{STORAGE_SERVICE}/data/{object_id}",
                timeout=10.0
            )
            
            if delete_metadata_response.status_code not in [200, 204, 404]:
                raise HTTPException(status_code=500, detail="Failed to delete object metadata")
            
            return Response(status_code=204)
            
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/buckets/{bucket_name}/objects")
async def list_objects(
    bucket_name: str,
    prefix: Optional[str] = None,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """List objects in bucket"""
    
    # Verify bucket access
    await verify_bucket_access(bucket_name, x_user_id)
    
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if prefix:
                params["prefix"] = prefix
            
            response = await client.get(
                f"{METADATA_SERVICE}/metadata/buckets/{bucket_name}/objects",
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 200:
                objects = response.json()
                return {
                    "bucket_name": bucket_name,
                    "prefix": prefix,
                    "objects": objects,
                    "count": len(objects)
                }
            else:
                return {
                    "bucket_name": bucket_name, 
                    "prefix": prefix,
                    "objects": [],
                    "count": 0
                }
                
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Metadata service unavailable")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7871)