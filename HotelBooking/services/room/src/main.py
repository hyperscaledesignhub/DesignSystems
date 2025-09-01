from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uuid
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
import os

app = FastAPI(title="Room Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hotel_db")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def create_initial_inventory(hotel_id: str, room_type_id: str, base_price: float):
    """Create initial inventory records for the next 365 days"""
    print(f"Starting inventory creation for room_type {room_type_id}")
    try:
        # Get inventory database connection (use postgres-db service name in Docker network)
        inventory_db_url = os.getenv("INVENTORY_DATABASE_URL", "postgresql://postgres:postgres@postgres-db:5432/inventory_db")
        conn = psycopg2.connect(inventory_db_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Create inventory for next 365 days (1 year)
        start_date = date.today()
        for i in range(365):
            inventory_date = date.fromordinal(start_date.toordinal() + i)
            
            # Insert inventory record with 10 rooms available by default
            cur.execute("""
                INSERT INTO room_inventory (hotel_id, room_type_id, date, total_inventory, total_reserved, price)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (hotel_id, room_type_id, date) DO NOTHING
            """, (hotel_id, room_type_id, inventory_date, 10, 0, base_price))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"Created inventory records for room_type {room_type_id}")
        
    except Exception as e:
        print(f"Failed to create inventory: {str(e)}")
        import traceback
        traceback.print_exc()
        # Don't fail room creation if inventory creation fails

class RoomType(BaseModel):
    hotel_id: str
    name: str
    max_occupancy: int
    base_price: float

class RoomTypeResponse(BaseModel):
    room_type_id: str
    hotel_id: str
    name: str
    max_occupancy: int
    base_price: float
    created_at: datetime

@app.on_event("startup")
async def startup_event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS room_types (
            room_type_id VARCHAR(36) PRIMARY KEY,
            hotel_id VARCHAR(36) NOT NULL,
            name VARCHAR(100) NOT NULL,
            max_occupancy INT NOT NULL,
            base_price DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "room"}

@app.get("/api/v1/hotels/{hotel_id}/room-types/{room_type_id}", response_model=RoomTypeResponse)
async def get_room_type(hotel_id: str, room_type_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM room_types 
        WHERE hotel_id = %s AND room_type_id = %s
    """, (hotel_id, room_type_id))
    room_type = cur.fetchone()
    cur.close()
    conn.close()
    
    if not room_type:
        raise HTTPException(status_code=404, detail="Room type not found")
    
    return room_type

@app.get("/api/v1/hotels/{hotel_id}/room-types", response_model=List[RoomTypeResponse])
async def list_room_types(hotel_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM room_types 
        WHERE hotel_id = %s 
        ORDER BY base_price ASC
    """, (hotel_id,))
    room_types = cur.fetchall()
    cur.close()
    conn.close()
    return room_types

@app.post("/api/v1/hotels/{hotel_id}/room-types", response_model=RoomTypeResponse)
async def create_room_type(hotel_id: str, room_type: RoomType):
    room_type_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO room_types (room_type_id, hotel_id, name, max_occupancy, base_price)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (room_type_id, hotel_id, room_type.name, room_type.max_occupancy, room_type.base_price))
    
    new_room_type = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    # Create initial inventory records for this room type
    print(f"About to create inventory for room_type {room_type_id}")
    create_initial_inventory(hotel_id, room_type_id, room_type.base_price)
    print(f"Inventory creation call completed for room_type {room_type_id}")
    
    return new_room_type

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5002)))