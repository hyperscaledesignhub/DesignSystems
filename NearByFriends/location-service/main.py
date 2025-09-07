from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import jwt
import redis.asyncio as redis
import asyncpg
import os
import json
from contextlib import asynccontextmanager
from geopy.distance import geodesic
import httpx

app = FastAPI(title="Location Service", version="1.0.0")
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
ALGORITHM = "HS256"

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost/nearbyfriendsdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
FRIEND_SERVICE_URL = os.getenv("FRIEND_SERVICE_URL", "http://friend-service:8902")

LOCATION_TTL = 600  # 10 minutes
NEARBY_RADIUS_MILES = 5

redis_client = None
db_pool = None

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

class LocationResponse(BaseModel):
    user_id: int
    latitude: float
    longitude: float
    timestamp: datetime

class NearbyFriend(BaseModel):
    user_id: int
    username: Optional[str] = None
    latitude: float
    longitude: float
    distance_miles: float
    last_updated: datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(POSTGRES_URL)
    redis_client = await redis.from_url(REDIS_URL)
    
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS location_history (
                user_id INTEGER NOT NULL,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON location_history (user_id, timestamp)
        ''')
    
    yield
    
    await db_pool.close()
    await redis_client.close()

app = FastAPI(title="Location Service", version="1.0.0", lifespan=lifespan)

def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return geodesic((lat1, lon1), (lat2, lon2)).miles

@app.post("/location/update")
async def update_location(
    location: LocationUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    payload = verify_token(credentials)
    user_id = payload['user_id']
    
    timestamp = datetime.utcnow()
    location_data = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": timestamp.isoformat()
    }
    
    await redis_client.setex(
        f"location:{user_id}",
        LOCATION_TTL,
        json.dumps(location_data)
    )
    
    async with db_pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO location_history (user_id, latitude, longitude)
            VALUES ($1, $2, $3)
        ''', user_id, location.latitude, location.longitude)
    
    await redis_client.publish(
        f"location_channel:{user_id}",
        json.dumps({
            "user_id": user_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timestamp": timestamp.isoformat()
        })
    )
    
    return {"message": "Location updated successfully"}

@app.get("/location/nearby/{user_id}")
async def get_nearby_friends(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_token(credentials)
    
    user_location = await redis_client.get(f"location:{user_id}")
    if not user_location:
        raise HTTPException(status_code=404, detail="User location not found")
    
    user_loc_data = json.loads(user_location)
    user_lat = user_loc_data['latitude']
    user_lon = user_loc_data['longitude']
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {credentials.credentials}"}
        response = await client.get(
            f"{FRIEND_SERVICE_URL}/friends/{user_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch friends")
        
        friends = response.json()
    
    nearby_friends = []
    
    for friend in friends:
        friend_id = friend['friend_id']
        friend_location = await redis_client.get(f"location:{friend_id}")
        
        if friend_location:
            friend_loc_data = json.loads(friend_location)
            distance = calculate_distance(
                user_lat, user_lon,
                friend_loc_data['latitude'], friend_loc_data['longitude']
            )
            
            if distance <= NEARBY_RADIUS_MILES:
                nearby_friends.append({
                    "user_id": friend_id,
                    "latitude": friend_loc_data['latitude'],
                    "longitude": friend_loc_data['longitude'],
                    "distance_miles": round(distance, 2),
                    "last_updated": friend_loc_data['timestamp']
                })
    
    nearby_friends.sort(key=lambda x: x['distance_miles'])
    
    return nearby_friends

@app.get("/location/{user_id}")
async def get_user_location(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_token(credentials)
    
    location = await redis_client.get(f"location:{user_id}")
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    location_data = json.loads(location)
    return {
        "user_id": user_id,
        "latitude": location_data['latitude'],
        "longitude": location_data['longitude'],
        "timestamp": location_data['timestamp']
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "location-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8903)