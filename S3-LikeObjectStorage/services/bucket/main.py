#!/usr/bin/env python3
"""
Bucket Service - Bucket lifecycle management
Port: 7861
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional
import asyncpg
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/s3_buckets")

# Global connection pool
pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    # Initialize database connection pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    await init_database()
    yield
    await pool.close()

app = FastAPI(title="S3 Bucket Service", version="1.0.0", lifespan=lifespan)

# CORS configuration for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BucketCreate(BaseModel):
    bucket_name: str

class BucketResponse(BaseModel):
    bucket_id: str
    bucket_name: str
    owner_id: str
    created_at: datetime

async def init_database():
    """Initialize database schema"""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS buckets (
                bucket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                bucket_name VARCHAR(255) UNIQUE NOT NULL,
                owner_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_buckets_owner ON buckets(owner_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_buckets_name ON buckets(bucket_name)
        """)

def validate_bucket_name(bucket_name: str) -> bool:
    """Validate bucket name according to S3 rules (simplified)"""
    if not bucket_name or len(bucket_name) < 3 or len(bucket_name) > 63:
        return False
    
    # Must start and end with letter or number
    if not (bucket_name[0].isalnum() and bucket_name[-1].isalnum()):
        return False
    
    # Only lowercase letters, numbers, and hyphens
    for char in bucket_name:
        if not (char.islower() or char.isdigit() or char == '-'):
            return False
    
    return True

@app.get("/health")
async def health_check():
    """Service health check"""
    return {"status": "healthy", "service": "bucket"}

@app.post("/buckets", response_model=BucketResponse)
async def create_bucket(
    bucket_data: BucketCreate,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Create new bucket"""
    if not validate_bucket_name(bucket_data.bucket_name):
        raise HTTPException(
            status_code=400, 
            detail="Invalid bucket name. Must be 3-63 chars, lowercase, start/end with alphanumeric"
        )
    
    async with pool.acquire() as conn:
        try:
            # Check if bucket already exists
            existing = await conn.fetchrow(
                "SELECT bucket_id FROM buckets WHERE bucket_name = $1",
                bucket_data.bucket_name
            )
            
            if existing:
                raise HTTPException(status_code=409, detail="Bucket already exists")
            
            # Create bucket
            bucket_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            await conn.execute("""
                INSERT INTO buckets (bucket_id, bucket_name, owner_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
            """, bucket_id, bucket_data.bucket_name, x_user_id, now, now)
            
            return BucketResponse(
                bucket_id=bucket_id,
                bucket_name=bucket_data.bucket_name,
                owner_id=x_user_id,
                created_at=now
            )
            
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=409, detail="Bucket already exists")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/buckets", response_model=List[BucketResponse])
async def list_buckets(x_user_id: str = Header(..., alias="X-User-ID")):
    """List user's buckets"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT bucket_id, bucket_name, owner_id, created_at 
            FROM buckets 
            WHERE owner_id = $1 
            ORDER BY created_at DESC
        """, x_user_id)
        
        return [
            BucketResponse(
                bucket_id=str(row['bucket_id']),
                bucket_name=row['bucket_name'],
                owner_id=row['owner_id'],
                created_at=row['created_at']
            )
            for row in rows
        ]

@app.get("/buckets/{bucket_name}", response_model=BucketResponse)
async def get_bucket(
    bucket_name: str,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Get bucket info"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT bucket_id, bucket_name, owner_id, created_at 
            FROM buckets 
            WHERE bucket_name = $1 AND owner_id = $2
        """, bucket_name, x_user_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Bucket not found")
        
        return BucketResponse(
            bucket_id=str(row['bucket_id']),
            bucket_name=row['bucket_name'],
            owner_id=row['owner_id'],
            created_at=row['created_at']
        )

@app.delete("/buckets/{bucket_name}")
async def delete_bucket(
    bucket_name: str,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Delete empty bucket"""
    async with pool.acquire() as conn:
        # Check if bucket exists and belongs to user
        bucket = await conn.fetchrow("""
            SELECT bucket_id FROM buckets 
            WHERE bucket_name = $1 AND owner_id = $2
        """, bucket_name, x_user_id)
        
        if not bucket:
            raise HTTPException(status_code=404, detail="Bucket not found")
        
        # TODO: Check if bucket is empty by calling metadata service
        # For now, we'll allow deletion (should be enhanced in production)
        
        result = await conn.execute("""
            DELETE FROM buckets 
            WHERE bucket_name = $1 AND owner_id = $2
        """, bucket_name, x_user_id)
        
        return {"message": f"Bucket {bucket_name} deleted successfully"}

@app.get("/buckets/{bucket_name}/exists")
async def check_bucket_exists(bucket_name: str):
    """Check if bucket exists (internal API for other services)"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT bucket_id, owner_id FROM buckets WHERE bucket_name = $1",
            bucket_name
        )
        
        if row:
            return {
                "exists": True,
                "bucket_id": str(row['bucket_id']),
                "owner_id": row['owner_id']
            }
        else:
            return {"exists": False}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861)