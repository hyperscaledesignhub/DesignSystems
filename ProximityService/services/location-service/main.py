from fastapi import FastAPI, Query, HTTPException
from typing import List, Dict, Optional
import json
import asyncio
from pydantic import BaseModel
import geohash
import logging

from redis_manager import get_redis_manager

app = FastAPI(title="Location Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    radius: int = 5000

class BusinessDistance(BaseModel):
    business_id: str
    distance: float

class NearbyResponse(BaseModel):
    businesses: List[BusinessDistance]
    total: int

RADIUS_TO_PRECISION = {
    500: 6,
    1000: 5,
    2000: 5,
    5000: 4
}

@app.get("/nearby", response_model=NearbyResponse)
async def find_nearby_businesses(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: int = Query(5000, ge=500, le=20000)
):
    try:
        precision = RADIUS_TO_PRECISION.get(radius, 4)
        center_geohash = geohash.encode(latitude, longitude, precision)
        
        geohashes = [center_geohash] + geohash.get_neighbors(center_geohash)
        
        all_business_ids = set()
        tasks = []
        
        async def fetch_businesses(gh):
            redis_mgr = get_redis_manager()
            return redis_mgr.get_geohash_businesses(precision, gh)
        
        for gh in geohashes:
            tasks.append(fetch_businesses(gh))
        
        results = await asyncio.gather(*tasks)
        for business_ids in results:
            all_business_ids.update(business_ids)
        
        business_distances = []
        redis_mgr = get_redis_manager()
        
        for business_id in all_business_ids:
            business_data = redis_mgr.get_business(business_id)
            if business_data:
                distance = geohash.haversine_distance(
                    latitude, longitude,
                    business_data['latitude'], business_data['longitude']
                )
                
                if distance <= radius:
                    business_distances.append(BusinessDistance(
                        business_id=business_id,
                        distance=round(distance, 2)
                    ))
        
        business_distances.sort(key=lambda x: x.distance)
        
        return NearbyResponse(
            businesses=business_distances[:50],
            total=len(business_distances[:50])
        )
    
    except Exception as e:
        logger.error(f"Error finding nearby businesses: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    try:
        redis_mgr = get_redis_manager()
        redis_health = redis_mgr.health_check()
        
        redis_healthy = redis_health["master"] or any(s.get("healthy", False) for s in redis_health["slaves"])
        
        if redis_healthy:
            return {
                "status": "healthy",
                "redis": redis_health
            }
        else:
            return {
                "status": "unhealthy", 
                "redis": redis_health
            }, 503
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8921)