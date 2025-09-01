from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Inventory Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/inventory_db")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

class AvailabilityCheck(BaseModel):
    room_type_id: str
    check_in: date
    check_out: date
    num_rooms: int = 1

class AvailabilityResponse(BaseModel):
    available_rooms: int
    room_type_id: str
    check_in: date
    check_out: date

@app.on_event("startup")
async def startup_event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS room_inventory (
            id SERIAL PRIMARY KEY,
            hotel_id VARCHAR(36) NOT NULL,
            room_type_id VARCHAR(36) NOT NULL,
            date DATE NOT NULL,
            total_inventory INTEGER NOT NULL DEFAULT 0,
            total_reserved INTEGER NOT NULL DEFAULT 0,
            price DECIMAL(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT check_reserved_lte_inventory CHECK (total_reserved <= total_inventory),
            UNIQUE(hotel_id, room_type_id, date)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "inventory"}

@app.get("/availability")
def check_availability(
    room_type_id: str,
    check_in: str,
    check_out: str,
    num_rooms: int = 1
):
    try:
        check_in_date = datetime.fromisoformat(check_in).date()
        check_out_date = datetime.fromisoformat(check_out).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check availability for the date range
        cur.execute("""
            SELECT MIN(total_inventory - total_reserved) as min_available
            FROM room_inventory 
            WHERE room_type_id = %s 
            AND date >= %s 
            AND date < %s
        """, (room_type_id, check_in_date, check_out_date))
        
        result = cur.fetchone()
        available_rooms = result['min_available'] if result['min_available'] else 0
        
        return {
            "available_rooms": max(0, available_rooms),
            "room_type_id": room_type_id,
            "check_in": check_in_date,
            "check_out": check_out_date
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        cur.close()
        conn.close()

@app.post("/reserve")
def reserve_rooms(
    room_type_id: str,
    hotel_id: str,
    check_in: str,
    check_out: str,
    num_rooms: int
):
    try:
        check_in_date = datetime.fromisoformat(check_in).date()
        check_out_date = datetime.fromisoformat(check_out).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Reserve rooms for each date in the range
        current_date = check_in_date
        while current_date < check_out_date:
            # Check if inventory exists for this date
            cur.execute("""
                SELECT * FROM room_inventory 
                WHERE hotel_id = %s AND room_type_id = %s AND date = %s
            """, (hotel_id, room_type_id, current_date))
            
            if not cur.fetchone():
                # Create inventory record if it doesn't exist (assume 10 rooms available)
                cur.execute("""
                    INSERT INTO room_inventory (hotel_id, room_type_id, date, total_inventory, total_reserved, price)
                    VALUES (%s, %s, %s, 10, 0, 100.00)
                """, (hotel_id, room_type_id, current_date))
            
            # Try to reserve the rooms
            cur.execute("""
                UPDATE room_inventory
                SET total_reserved = total_reserved + %s
                WHERE hotel_id = %s AND room_type_id = %s AND date = %s
                AND (total_reserved + %s) <= total_inventory
                RETURNING total_reserved, total_inventory
            """, (num_rooms, hotel_id, room_type_id, current_date, num_rooms))
            
            result = cur.fetchone()
            if not result:
                conn.rollback()
                raise HTTPException(status_code=400, detail=f"Not enough rooms available for {current_date}")
            
            current_date = date.fromordinal(current_date.toordinal() + 1)
        
        conn.commit()
        return {"message": "Rooms reserved successfully"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

@app.post("/release")
def release_rooms(
    room_type_id: str,
    hotel_id: str,
    check_in: str,
    check_out: str,
    num_rooms: int
):
    try:
        check_in_date = datetime.fromisoformat(check_in).date()
        check_out_date = datetime.fromisoformat(check_out).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Release rooms for each date in the range
        current_date = check_in_date
        while current_date < check_out_date:
            # Release the rooms by decreasing total_reserved
            cur.execute("""
                UPDATE room_inventory
                SET total_reserved = GREATEST(0, total_reserved - %s)
                WHERE hotel_id = %s AND room_type_id = %s AND date = %s
                RETURNING total_reserved, total_inventory
            """, (num_rooms, hotel_id, room_type_id, current_date))
            
            result = cur.fetchone()
            if not result:
                # If no inventory record exists, nothing to release
                pass
            
            current_date = date.fromordinal(current_date.toordinal() + 1)
        
        conn.commit()
        return {"message": "Rooms released successfully"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5004)))