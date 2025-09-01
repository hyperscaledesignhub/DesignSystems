from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
import redis
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Hotel Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url, decode_responses=True)

def get_db_connection():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hotel_db")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

class Hotel(BaseModel):
    name: str
    address: str
    location: str

class HotelResponse(BaseModel):
    hotel_id: str
    name: str
    address: str
    location: str
    created_at: datetime

@app.on_event("startup")
async def startup_event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            hotel_id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address TEXT NOT NULL,
            location VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "hotel"}

@app.get("/api/v1/hotels/{hotel_id}", response_model=HotelResponse)
async def get_hotel(hotel_id: str):
    cache_key = f"hotel:{hotel_id}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM hotels WHERE hotel_id = %s", (hotel_id,))
    hotel = cur.fetchone()
    cur.close()
    conn.close()
    
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    redis_client.setex(cache_key, 300, json.dumps(dict(hotel), default=str))
    return hotel

@app.get("/api/v1/hotels", response_model=List[HotelResponse])
async def list_hotels(limit: int = 100, offset: int = 0):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM hotels ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
    hotels = cur.fetchall()
    cur.close()
    conn.close()
    return hotels

@app.post("/api/v1/hotels", response_model=HotelResponse)
async def create_hotel(hotel: Hotel):
    hotel_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO hotels (hotel_id, name, address, location)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """, (hotel_id, hotel.name, hotel.address, hotel.location))
    
    new_hotel = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return new_hotel

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5001)))