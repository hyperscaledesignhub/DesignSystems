from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import time
import logging
import asyncio
from contextlib import asynccontextmanager

from .database import DatabaseManager
from .models import LocationUpdate, LocationBatch, UserCurrentLocation, LocationHistory
from .batch_processor import BatchProcessor
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global database manager
db_manager = None
batch_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_manager, batch_processor
    logger.info("Starting Location Service...")
    
    # Initialize database connection
    db_manager = DatabaseManager(settings.cassandra_hosts, settings.cassandra_keyspace)
    await db_manager.connect()
    
    # Initialize batch processor
    batch_processor = BatchProcessor(db_manager)
    
    logger.info("Location Service started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down Location Service...")
    if db_manager:
        await db_manager.close()
    logger.info("Location Service shutdown complete")

app = FastAPI(
    title="Location Service",
    description="Microservice for tracking user locations with batched updates",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_manager():
    """Dependency to get database manager"""
    if db_manager is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_manager

def get_batch_processor():
    """Dependency to get batch processor"""
    if batch_processor is None:
        raise HTTPException(status_code=503, detail="Batch processor not available")
    return batch_processor

@app.post("/api/v1/locations/batch")
async def submit_location_batch(
    batch: LocationBatch,
    background_tasks: BackgroundTasks,
    processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Submit a batch of location updates for processing
    """
    try:
        # Validate batch size
        if len(batch.locations) > settings.max_batch_size:
            raise HTTPException(
                status_code=400, 
                detail=f"Batch size exceeds maximum of {settings.max_batch_size}"
            )
        
        # Generate batch ID for tracking
        batch_id = str(uuid.uuid4())
        
        # Process batch in background
        background_tasks.add_task(
            processor.process_location_batch,
            batch_id,
            batch.user_id,
            batch.locations
        )
        
        logger.info(f"Queued batch {batch_id} for user {batch.user_id} with {len(batch.locations)} locations")
        
        return {
            "status": "accepted",
            "batch_id": batch_id,
            "processed_count": len(batch.locations),
            "message": "Location batch queued for processing"
        }
    
    except Exception as e:
        logger.error(f"Error processing location batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/locations/{user_id}/current")
async def get_current_location(
    user_id: str,
    db: DatabaseManager = Depends(get_db_manager)
) -> UserCurrentLocation:
    """
    Get the current (most recent) location for a user
    """
    try:
        location = await db.get_current_location(user_id)
        
        if not location:
            raise HTTPException(
                status_code=404, 
                detail=f"No location found for user {user_id}"
            )
        
        return location
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving current location for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/locations/{user_id}/history")
async def get_location_history(
    user_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Field(default=100, ge=1, le=1000),
    db: DatabaseManager = Depends(get_db_manager)
) -> LocationHistory:
    """
    Get location history for a user within a time range
    """
    try:
        # Set default time range (last 24 hours if not specified)
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=24)
        
        # Convert to timestamps
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        
        locations = await db.get_location_history(
            user_id, start_timestamp, end_timestamp, limit
        )
        
        return LocationHistory(
            user_id=user_id,
            locations=locations,
            total_count=len(locations),
            start_time=start_time,
            end_time=end_time
        )
    
    except Exception as e:
        logger.error(f"Error retrieving location history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/locations/{user_id}/nearby")
async def get_nearby_users(
    user_id: str,
    radius_km: float = Field(default=1.0, ge=0.1, le=50.0),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    Get users within a specified radius (simplified implementation)
    Note: This is a basic implementation. For production, consider geospatial indexing.
    """
    try:
        # Get current user location
        user_location = await db.get_current_location(user_id)
        if not user_location:
            raise HTTPException(
                status_code=404,
                detail=f"Location not found for user {user_id}"
            )
        
        # This is a simplified implementation
        # In production, you'd use geospatial queries or external services
        nearby_users = await db.get_nearby_users(
            user_location.latitude,
            user_location.longitude,
            radius_km
        )
        
        return {
            "user_id": user_id,
            "center_location": {
                "latitude": user_location.latitude,
                "longitude": user_location.longitude
            },
            "radius_km": radius_km,
            "nearby_users": nearby_users
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding nearby users for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/health")
async def health_check(db: DatabaseManager = Depends(get_db_manager)):
    """
    Health check endpoint
    """
    try:
        # Check database connectivity
        is_healthy = await db.health_check()
        
        if not is_healthy:
            raise HTTPException(status_code=503, detail="Database unhealthy")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "location-service",
            "version": "1.0.0"
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/api/v1/metrics")
async def get_metrics(db: DatabaseManager = Depends(get_db_manager)):
    """
    Get service metrics
    """
    try:
        metrics = await db.get_location_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
    
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Error handlers
@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8765,  # Changed from 8080
        reload=settings.debug,
        log_level="info"
    )