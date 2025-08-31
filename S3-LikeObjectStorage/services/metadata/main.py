#!/usr/bin/env python3
"""
Metadata Service - Object and bucket metadata management
Port: 7891
"""

import os
from datetime import datetime
from typing import List, Optional
import asyncpg
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/s3_metadata")

# Global connection pool
pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    # Initialize database connection pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=20)
    await init_database()
    yield
    await pool.close()

app = FastAPI(title="S3 Metadata Service", version="1.0.0", lifespan=lifespan)

# CORS configuration for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ObjectMetadata(BaseModel):
    object_id: str
    bucket_name: str
    object_name: str
    content_type: str = "application/octet-stream"
    size_bytes: int
    etag: str

class ObjectMetadataResponse(BaseModel):
    object_id: str
    bucket_name: str
    object_name: str
    content_type: str
    size_bytes: int
    etag: str
    created_at: datetime
    updated_at: datetime

async def init_database():
    """Initialize database schema"""
    async with pool.acquire() as conn:
        # Create object metadata table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS object_metadata (
                object_id UUID PRIMARY KEY,
                bucket_name VARCHAR(255) NOT NULL,
                object_name TEXT NOT NULL,
                content_type VARCHAR(255) DEFAULT 'application/octet-stream',
                size_bytes BIGINT NOT NULL,
                etag VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bucket_name, object_name)
            )
        """)
        
        # Create indexes for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_object_metadata_bucket ON object_metadata(bucket_name)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_object_metadata_bucket_object ON object_metadata(bucket_name, object_name)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_object_metadata_object_name ON object_metadata(object_name)
        """)
        
        # Add trigger to update updated_at timestamp
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)
        
        await conn.execute("""
            DROP TRIGGER IF EXISTS update_object_metadata_updated_at ON object_metadata
        """)
        
        await conn.execute("""
            CREATE TRIGGER update_object_metadata_updated_at 
            BEFORE UPDATE ON object_metadata 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "service": "metadata"}
    except:
        return {"status": "unhealthy", "service": "metadata"}

@app.post("/metadata/objects", response_model=ObjectMetadataResponse, status_code=201)
async def create_object_metadata(metadata: ObjectMetadata):
    """Create object metadata"""
    async with pool.acquire() as conn:
        try:
            now = datetime.utcnow()
            
            row = await conn.fetchrow("""
                INSERT INTO object_metadata 
                (object_id, bucket_name, object_name, content_type, size_bytes, etag, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """, 
            metadata.object_id, metadata.bucket_name, metadata.object_name,
            metadata.content_type, metadata.size_bytes, metadata.etag, now, now)
            
            return ObjectMetadataResponse(
                object_id=str(row['object_id']),
                bucket_name=row['bucket_name'],
                object_name=row['object_name'],
                content_type=row['content_type'],
                size_bytes=row['size_bytes'],
                etag=row['etag'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=409, detail="Object already exists")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/metadata/objects/{object_id}", response_model=ObjectMetadataResponse)
async def get_object_metadata(object_id: str):
    """Get object metadata by object ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM object_metadata WHERE object_id = $1
        """, object_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Object metadata not found")
        
        return ObjectMetadataResponse(
            object_id=str(row['object_id']),
            bucket_name=row['bucket_name'],
            object_name=row['object_name'],
            content_type=row['content_type'],
            size_bytes=row['size_bytes'],
            etag=row['etag'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

@app.delete("/metadata/objects/{object_id}")
async def delete_object_metadata(object_id: str):
    """Delete object metadata"""
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM object_metadata WHERE object_id = $1
        """, object_id)
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Object metadata not found")
        
        return {"message": "Object metadata deleted successfully"}

@app.get("/metadata/buckets/{bucket_name}/objects", response_model=List[ObjectMetadataResponse])
async def list_objects_in_bucket(
    bucket_name: str,
    prefix: Optional[str] = Query(None),
    object_name: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    """List objects in bucket with optional prefix filtering"""
    async with pool.acquire() as conn:
        
        # Build query based on parameters
        if object_name:
            # Exact object name match
            query = """
                SELECT * FROM object_metadata 
                WHERE bucket_name = $1 AND object_name = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            params = [bucket_name, object_name, limit, offset]
        elif prefix:
            # Prefix filtering
            query = """
                SELECT * FROM object_metadata 
                WHERE bucket_name = $1 AND object_name LIKE $2
                ORDER BY object_name
                LIMIT $3 OFFSET $4
            """
            params = [bucket_name, f"{prefix}%", limit, offset]
        else:
            # All objects in bucket
            query = """
                SELECT * FROM object_metadata 
                WHERE bucket_name = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            params = [bucket_name, limit, offset]
        
        rows = await conn.fetch(query, *params)
        
        return [
            ObjectMetadataResponse(
                object_id=str(row['object_id']),
                bucket_name=row['bucket_name'],
                object_name=row['object_name'],
                content_type=row['content_type'],
                size_bytes=row['size_bytes'],
                etag=row['etag'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]

@app.get("/metadata/buckets/{bucket_name}/stats")
async def get_bucket_stats(bucket_name: str):
    """Get bucket statistics"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                COUNT(*) as object_count,
                SUM(size_bytes) as total_size_bytes,
                MIN(created_at) as oldest_object,
                MAX(created_at) as newest_object
            FROM object_metadata 
            WHERE bucket_name = $1
        """, bucket_name)
        
        return {
            "bucket_name": bucket_name,
            "object_count": row['object_count'] or 0,
            "total_size_bytes": row['total_size_bytes'] or 0,
            "oldest_object": row['oldest_object'],
            "newest_object": row['newest_object']
        }

@app.get("/metadata/stats")
async def get_global_stats():
    """Get global metadata statistics"""
    async with pool.acquire() as conn:
        # Get overall stats
        row = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_objects,
                SUM(size_bytes) as total_size_bytes,
                COUNT(DISTINCT bucket_name) as bucket_count
            FROM object_metadata
        """)
        
        # Get bucket breakdown
        bucket_stats = await conn.fetch("""
            SELECT 
                bucket_name,
                COUNT(*) as object_count,
                SUM(size_bytes) as size_bytes
            FROM object_metadata
            GROUP BY bucket_name
            ORDER BY object_count DESC
            LIMIT 10
        """)
        
        return {
            "total_objects": row['total_objects'] or 0,
            "total_size_bytes": row['total_size_bytes'] or 0,
            "bucket_count": row['bucket_count'] or 0,
            "top_buckets": [
                {
                    "bucket_name": bucket['bucket_name'],
                    "object_count": bucket['object_count'],
                    "size_bytes": bucket['size_bytes']
                }
                for bucket in bucket_stats
            ]
        }

@app.put("/metadata/objects/{object_id}")
async def update_object_metadata(object_id: str, metadata: ObjectMetadata):
    """Update object metadata"""
    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE object_metadata 
            SET bucket_name = $2, object_name = $3, content_type = $4, 
                size_bytes = $5, etag = $6
            WHERE object_id = $1
        """, 
        object_id, metadata.bucket_name, metadata.object_name,
        metadata.content_type, metadata.size_bytes, metadata.etag)
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Object metadata not found")
        
        return {"message": "Object metadata updated successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7891)