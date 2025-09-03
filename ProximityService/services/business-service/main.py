from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from typing import Optional
import asyncpg
import json
import uuid
from datetime import datetime
import logging
import geohash
import sys
import os

from db_pool import initialize_database_pools, get_database_pool
from redis_manager import get_redis_manager

app = FastAPI(title="Business Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Business(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: str
    city: str
    state: str
    country: str
    category: str
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90 degrees')
        return v
    
    @validator('longitude')  
    def validate_longitude(cls, v):
        if not (-180 <= v <= 180):
            raise ValueError('Longitude must be between -180 and 180 degrees')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 255:
            raise ValueError('Name cannot exceed 255 characters')
        return v.strip()

class BusinessResponse(Business):
    id: str
    created_at: datetime
    updated_at: datetime

@app.on_event("startup")
async def startup():
    await initialize_database_pools()

@app.on_event("shutdown")
async def shutdown():
    db_pool = await get_database_pool()
    await db_pool.close()

@app.post("/businesses", response_model=BusinessResponse)
async def create_business(business: Business):
    try:
        print(f"DEBUG: Starting business creation process")
        business_id = str(uuid.uuid4())
        print(f"DEBUG: Generated business ID: {business_id}")
        now = datetime.utcnow()
        
        db_pool = await get_database_pool()
        async with await db_pool.get_write_connection() as conn:
            await conn.execute("""
                INSERT INTO businesses (id, name, latitude, longitude, address, city, state, country, category, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, business_id, business.name, business.latitude, business.longitude, 
                business.address, business.city, business.state, business.country, 
                business.category, now, now)
            
            for precision in [4, 5, 6]:
                gh = geohash.encode(business.latitude, business.longitude, precision)
                await conn.execute("""
                    INSERT INTO geohash_index (geohash, business_id)
                    VALUES ($1, $2)
                """, gh, business_id)
        
        business_data = {
            "id": business_id,
            "name": business.name,
            "latitude": business.latitude,
            "longitude": business.longitude,
            "address": business.address,
            "city": business.city,
            "state": business.state,
            "country": business.country,
            "category": business.category,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        print(f"DEBUG: About to set business cache for {business_id}")
        redis_mgr = get_redis_manager()
        redis_mgr.set_business(business_id, business_data, ttl=86400)
        print(f"DEBUG: Business cache set successfully for {business_id}")
        
        # Update geohash caches to include the new business
        print(f"DEBUG: About to update geohash caches for business {business_id}")
        for precision in [4, 5, 6]:
            gh = geohash.encode(business.latitude, business.longitude, precision)
            print(f"DEBUG: Updating geohash cache for precision {precision}, geohash {gh}")
            logger.warning(f"Updating geohash cache for precision {precision}, geohash {gh}")
            
            # Get existing businesses for this geohash
            existing_businesses = redis_mgr.get_geohash_businesses(precision, gh)
            print(f"DEBUG: Retrieved {len(existing_businesses)} existing businesses for geohash {gh}")
            logger.warning(f"Retrieved {len(existing_businesses)} existing businesses for geohash {gh}")
            
            # Add the new business if not already present
            if business_id not in existing_businesses:
                print(f"DEBUG: Adding business {business_id} to geohash {gh}")
                existing_businesses.append(business_id)
                redis_mgr.set_geohash_businesses(precision, gh, existing_businesses, ttl=86400)
                print(f"DEBUG: Successfully added business {business_id} to geohash {gh}, total: {len(existing_businesses)}")
                logger.warning(f"Added business {business_id} to geohash {gh}, total businesses: {len(existing_businesses)}")
            else:
                print(f"DEBUG: Business {business_id} already exists in geohash {gh}")
                logger.warning(f"Business {business_id} already exists in geohash {gh}")
        
        return BusinessResponse(**business_data)
    
    except Exception as e:
        logger.error(f"Error creating business: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/businesses/{business_id}", response_model=BusinessResponse)
async def get_business(business_id: str):
    try:
        redis_mgr = get_redis_manager()
        cached_data = redis_mgr.get_business(business_id)
        if cached_data:
            return BusinessResponse(**cached_data)
        
        db_pool = await get_database_pool()
        async with await db_pool.get_read_connection() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM businesses WHERE id = $1
            """, uuid.UUID(business_id) if isinstance(business_id, str) else business_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Business not found")
            
            business_data = dict(row)
            business_data['id'] = str(business_data['id'])  # Convert UUID to string
            business_data['latitude'] = float(business_data['latitude'])
            business_data['longitude'] = float(business_data['longitude'])
            business_data['created_at'] = business_data['created_at'].isoformat()
            business_data['updated_at'] = business_data['updated_at'].isoformat()
            
            redis_mgr.set_business(business_id, business_data, ttl=86400)
            
            return BusinessResponse(**business_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching business: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/businesses/{business_id}", response_model=BusinessResponse)
async def update_business(business_id: str, business: Business):
    try:
        now = datetime.utcnow()
        
        db_pool = await get_database_pool()
        async with await db_pool.get_write_connection() as conn:
            result = await conn.execute("""
                UPDATE businesses 
                SET name = $2, latitude = $3, longitude = $4, address = $5, 
                    city = $6, state = $7, country = $8, category = $9, updated_at = $10
                WHERE id = $1
            """, uuid.UUID(business_id), business.name, business.latitude, business.longitude,
                business.address, business.city, business.state, business.country,
                business.category, now)
            
            if result.split()[-1] == '0':
                raise HTTPException(status_code=404, detail="Business not found")
            
            await conn.execute("""
                DELETE FROM geohash_index WHERE business_id = $1
            """, uuid.UUID(business_id))
            
            for precision in [4, 5, 6]:
                gh = geohash.encode(business.latitude, business.longitude, precision)
                await conn.execute("""
                    INSERT INTO geohash_index (geohash, business_id)
                    VALUES ($1, $2)
                """, gh, uuid.UUID(business_id))
        
        redis_mgr = get_redis_manager()
        redis_mgr.delete_business(business_id)
        
        return await get_business(business_id)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating business: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/businesses/{business_id}")
async def delete_business(business_id: str):
    try:
        # Get business data before deletion for cache cleanup
        db_pool = await get_database_pool()
        async with await db_pool.get_read_connection() as conn:
            business_row = await conn.fetchrow("""
                SELECT latitude, longitude FROM businesses WHERE id = $1
            """, uuid.UUID(business_id))
            
            if not business_row:
                raise HTTPException(status_code=404, detail="Business not found")
        
        business_lat, business_lng = business_row['latitude'], business_row['longitude']
        
        # Delete from database
        async with await db_pool.get_write_connection() as conn:
            await conn.execute("""
                DELETE FROM geohash_index WHERE business_id = $1
            """, uuid.UUID(business_id))
            
            await conn.execute("""
                DELETE FROM businesses WHERE id = $1
            """, uuid.UUID(business_id))
        
        # Clean up Redis caches
        redis_mgr = get_redis_manager()
        redis_mgr.delete_business(business_id)
        
        # Remove business from geohash caches
        for precision in [4, 5, 6]:
            gh = geohash.encode(float(business_lat), float(business_lng), precision)
            existing_businesses = redis_mgr.get_geohash_businesses(precision, gh)
            if business_id in existing_businesses:
                existing_businesses.remove(business_id)
                redis_mgr.set_geohash_businesses(precision, gh, existing_businesses, ttl=86400)
        
        return {"message": "Business deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting business: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/debug-test")
async def debug_test():
    print("DEBUG: Debug test endpoint called!")
    return {"message": "Debug test endpoint - code is updated!", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
async def health_check():
    try:
        # Check Redis cluster health
        redis_mgr = get_redis_manager()
        redis_health = redis_mgr.health_check()
        
        # Check database health
        db_pool = await get_database_pool()
        db_health = await db_pool.check_health()
        
        # Consider system healthy if we have database and Redis available
        db_healthy = (db_health["primary"] or 
                     db_health.get("promoted_primary", False) or 
                     any(r.get("healthy", False) for r in db_health["replicas"]))
        
        redis_healthy = redis_health["master"] or any(s.get("healthy", False) for s in redis_health["slaves"])
        
        if db_healthy and redis_healthy:
            return {
                "status": "healthy",
                "database": db_health,
                "redis": redis_health
            }
        else:
            return {
                "status": "unhealthy",
                "database": db_health,
                "redis": redis_health
            }, 503
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9823)