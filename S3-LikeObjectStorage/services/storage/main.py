#!/usr/bin/env python3
"""
Storage Service - Raw data persistence with 3-copy replication
Port: 7881
"""

import os
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import aiofiles
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Storage configuration
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/data/storage")
DB_PATH = os.getenv("DB_PATH", "/data/storage.db")
REPLICA_NODES = os.getenv("REPLICA_NODES", "").split(",") if os.getenv("REPLICA_NODES") else []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize storage
    init_storage()
    yield

app = FastAPI(title="S3 Storage Service", version="1.0.0", lifespan=lifespan)

# CORS configuration for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StorageInfo(BaseModel):
    uuid: str
    file_path: str
    size_bytes: int
    checksum: str
    created_at: datetime

def init_storage():
    """Initialize storage directories and database"""
    # Create storage directory
    Path(STORAGE_ROOT).mkdir(parents=True, exist_ok=True)
    
    # Create database directory
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Initialize SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS objects (
            uuid TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            checksum TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_objects_uuid ON objects(uuid)
    """)
    
    conn.commit()
    conn.close()

def get_file_path(object_uuid: str) -> str:
    """Generate file path for object using UUID partitioning"""
    # Use first 4 chars for directory structure: /data/storage/ab/cd/abcd1234...
    prefix = object_uuid[:2]
    subdir = object_uuid[2:4]
    storage_path = Path(STORAGE_ROOT) / prefix / subdir
    storage_path.mkdir(parents=True, exist_ok=True)
    return str(storage_path / object_uuid)

def calculate_checksum(content: bytes) -> str:
    """Calculate MD5 checksum for content verification"""
    return hashlib.md5(content).hexdigest()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/health")
async def health_check():
    """Service health check"""
    # Check storage availability
    storage_available = Path(STORAGE_ROOT).exists() and os.access(STORAGE_ROOT, os.W_OK)
    
    # Check database connectivity
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        db_available = True
    except:
        db_available = False
    
    status = "healthy" if storage_available and db_available else "unhealthy"
    
    return {
        "status": status,
        "service": "storage",
        "storage_available": storage_available,
        "database_available": db_available,
        "storage_root": STORAGE_ROOT
    }

@app.post("/data")
async def store_object(
    request: Request,
    x_object_id: str = Header(..., alias="X-Object-ID"),
    x_content_type: str = Header("application/octet-stream", alias="X-Content-Type")
):
    """Store object data with replication"""
    
    # Read content
    content = await request.body()
    content_size = len(content)
    
    if content_size == 0:
        raise HTTPException(status_code=400, detail="Empty content not allowed")
    
    # Calculate checksum
    checksum = calculate_checksum(content)
    
    # Get file path
    file_path = get_file_path(x_object_id)
    
    try:
        # Write to primary storage
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Store metadata in database
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO objects (uuid, file_path, size_bytes, checksum, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (x_object_id, file_path, content_size, checksum, datetime.utcnow()))
        
        conn.commit()
        conn.close()
        
        # TODO: Implement replication to secondary nodes
        # For MVP, we'll skip complex replication logic
        
        return Response(
            status_code=201,
            headers={
                "X-Object-UUID": x_object_id,
                "X-Checksum": checksum,
                "X-Size-Bytes": str(content_size)
            }
        )
        
    except Exception as e:
        # Cleanup on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")

@app.get("/data/{object_uuid}")
async def retrieve_object(object_uuid: str):
    """Retrieve object data by UUID"""
    
    # Get object info from database
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT file_path, size_bytes, checksum FROM objects WHERE uuid = ?
    """, (object_uuid,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Object not found")
    
    file_path = row['file_path']
    expected_checksum = row['checksum']
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Object file not found on disk")
    
    # Verify checksum (data integrity check)
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        actual_checksum = calculate_checksum(content)
        if actual_checksum != expected_checksum:
            raise HTTPException(status_code=500, detail="Data corruption detected")
        
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            headers={
                "X-Object-UUID": object_uuid,
                "X-Checksum": expected_checksum,
                "X-Size-Bytes": str(row['size_bytes'])
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")

@app.delete("/data/{object_uuid}")
async def delete_object(object_uuid: str):
    """Delete object data"""
    
    # Get object info from database
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT file_path FROM objects WHERE uuid = ?
    """, (object_uuid,))
    
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return Response(status_code=204)  # Already deleted
    
    file_path = row['file_path']
    
    try:
        # Delete from database
        cursor.execute("DELETE FROM objects WHERE uuid = ?", (object_uuid,))
        conn.commit()
        conn.close()
        
        # Delete file from disk
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # TODO: Delete from replica nodes
        
        return Response(status_code=204)
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Deletion error: {str(e)}")

@app.get("/data/{object_uuid}/info")
async def get_object_info(object_uuid: str):
    """Get object metadata"""
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT uuid, file_path, size_bytes, checksum, created_at 
        FROM objects WHERE uuid = ?
    """, (object_uuid,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Object not found")
    
    return {
        "uuid": row['uuid'],
        "file_path": row['file_path'],
        "size_bytes": row['size_bytes'],
        "checksum": row['checksum'],
        "created_at": row['created_at'],
        "file_exists": os.path.exists(row['file_path'])
    }

@app.get("/stats")
async def get_storage_stats():
    """Get storage statistics"""
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get object count and total size
    cursor.execute("""
        SELECT COUNT(*) as object_count, SUM(size_bytes) as total_size 
        FROM objects
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    # Get disk usage
    storage_path = Path(STORAGE_ROOT)
    if storage_path.exists():
        disk_usage = sum(f.stat().st_size for f in storage_path.rglob('*') if f.is_file())
    else:
        disk_usage = 0
    
    return {
        "object_count": row['object_count'] or 0,
        "total_size_bytes": row['total_size'] or 0,
        "disk_usage_bytes": disk_usage,
        "storage_root": STORAGE_ROOT
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7881)