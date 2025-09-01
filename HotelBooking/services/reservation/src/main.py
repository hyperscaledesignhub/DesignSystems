from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import uuid
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Reservation Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INVENTORY_SERVICE = os.getenv("INVENTORY_SERVICE", "http://inventory-service:8004")
ROOM_SERVICE = os.getenv("ROOM_SERVICE", "http://room-service:8002")
HOTEL_SERVICE = os.getenv("HOTEL_SERVICE", "http://hotel-service:8001")

def get_db_connection():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/reservation_db")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def enrich_reservation_data(reservations):
    """Enrich reservation data with hotel names and room type names"""
    if not reservations:
        return []
    
    enriched_reservations = []
    
    for reservation in reservations:
        reservation_dict = dict(reservation)
        
        # First, get room type information to find the correct hotel_id
        room_data = None
        actual_hotel_id = reservation['hotel_id']
        
        # Try to get room type from all hotels if hotel_id is default-hotel or not found
        try:
            with httpx.Client() as client:
                # Get all hotels first
                hotels_response = client.get(f"{HOTEL_SERVICE}/api/v1/hotels")
                if hotels_response.status_code == 200:
                    hotels = hotels_response.json()
                    
                    # Try each hotel to find the room type
                    for hotel in hotels:
                        try:
                            room_response = client.get(f"{ROOM_SERVICE}/api/v1/hotels/{hotel['hotel_id']}/room-types/{reservation['room_type_id']}")
                            if room_response.status_code == 200:
                                room_data = room_response.json()
                                actual_hotel_id = hotel['hotel_id']  # Update to correct hotel_id
                                reservation_dict['hotel_name'] = hotel.get('name', 'Unknown Hotel')
                                reservation_dict['room_name'] = room_data.get('name', 'Unknown Room Type')
                                break
                        except Exception:
                            continue
        except Exception as e:
            print(f"Failed to enrich reservation data: {e}")
        
        # If we couldn't get the data above, set defaults
        if 'hotel_name' not in reservation_dict:
            reservation_dict['hotel_name'] = 'Unknown Hotel'
        if 'room_name' not in reservation_dict:
            reservation_dict['room_name'] = 'Unknown Room Type'
        
        enriched_reservations.append(reservation_dict)
    
    return enriched_reservations

class ReservationCreate(BaseModel):
    guest_id: str
    room_type_id: str
    check_in: str  # ISO date format
    check_out: str  # ISO date format
    num_rooms: int = 1
    total_amount: float

class Reservation(BaseModel):
    id: str
    guest_id: str
    hotel_id: Optional[str] = None
    room_type_id: str
    check_in_date: date
    check_out_date: date
    num_rooms: int
    total_amount: float
    status: str
    created_at: Optional[datetime] = None

@app.on_event("startup")
async def startup_event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id VARCHAR(36) PRIMARY KEY,
            guest_id VARCHAR(36) NOT NULL,
            hotel_id VARCHAR(36),
            room_type_id VARCHAR(36) NOT NULL,
            check_in_date DATE NOT NULL,
            check_out_date DATE NOT NULL,
            num_rooms INTEGER NOT NULL DEFAULT 1,
            total_amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(50) DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "reservation"}

@app.post("/reservations", response_model=Reservation, status_code=201)
def create_reservation(reservation: ReservationCreate):
    reservation_id = str(uuid.uuid4())
    
    try:
        check_in_date = datetime.fromisoformat(reservation.check_in).date()
        check_out_date = datetime.fromisoformat(reservation.check_out).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")
    
    # Get room type info to get hotel_id
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # First, get the hotel_id from the room_type
        with httpx.Client() as client:
            # Query the room service to get room type details
            room_response = client.get(f"{ROOM_SERVICE}/api/v1/room-types/{reservation.room_type_id}")
            if room_response.status_code == 200:
                room_data = room_response.json()
                hotel_id = room_data.get("hotel_id", "default-hotel")
            else:
                # If we can't get room info, try to get it from database
                hotel_id = "default-hotel"
        
        # Check availability via inventory service
        with httpx.Client() as client:
            availability_response = client.get(
                f"{INVENTORY_SERVICE}/availability",
                params={
                    "room_type_id": reservation.room_type_id,
                    "check_in": reservation.check_in,
                    "check_out": reservation.check_out,
                    "num_rooms": reservation.num_rooms
                }
            )
            
            if availability_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not check availability")
            
            availability = availability_response.json()
            if availability["available_rooms"] < reservation.num_rooms:
                raise HTTPException(status_code=400, detail="Not enough rooms available")
        
        # Create reservation
        cur.execute("""
            INSERT INTO reservations (
                id, guest_id, hotel_id, room_type_id,
                check_in_date, check_out_date, num_rooms, total_amount, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            reservation_id, 
            reservation.guest_id, 
            hotel_id,
            reservation.room_type_id,
            check_in_date, 
            check_out_date, 
            reservation.num_rooms, 
            reservation.total_amount,
            'confirmed'
        ))
        
        new_reservation = cur.fetchone()
        
        # Reserve rooms in inventory service
        try:
            with httpx.Client() as client:
                reserve_response = client.post(
                    f"{INVENTORY_SERVICE}/reserve",
                    params={
                        "room_type_id": reservation.room_type_id,
                        "hotel_id": hotel_id,
                        "check_in": reservation.check_in,
                        "check_out": reservation.check_out,
                        "num_rooms": reservation.num_rooms
                    }
                )
                
                if reserve_response.status_code != 200:
                    raise Exception(f"Failed to reserve rooms in inventory: {reserve_response.text}")
        
        except Exception as e:
            # If inventory reservation fails, rollback
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to reserve rooms: {str(e)}")
        
        conn.commit()
        return new_reservation
        
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

@app.get("/reservations")
def get_reservations(guest_id: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if guest_id:
            cur.execute("SELECT * FROM reservations WHERE guest_id = %s ORDER BY created_at DESC", (guest_id,))
        else:
            cur.execute("SELECT * FROM reservations ORDER BY created_at DESC LIMIT 100")
        
        reservations = cur.fetchall()
        if not reservations:
            return []
        
        # Enrich reservations with hotel names and room type names
        enriched_reservations = enrich_reservation_data(reservations)
        return enriched_reservations
        
    finally:
        cur.close()
        conn.close()

@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM reservations WHERE id = %s", (reservation_id,))
        reservation = cur.fetchone()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        
        # Enrich single reservation with hotel name and room type name
        enriched_reservations = enrich_reservation_data([reservation])
        return enriched_reservations[0] if enriched_reservations else reservation
        
    finally:
        cur.close()
        conn.close()

@app.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(reservation_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE reservations 
            SET status = 'cancelled' 
            WHERE id = %s AND status != 'cancelled'
            RETURNING *
        """, (reservation_id,))
        
        reservation = cur.fetchone()
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found or already cancelled")
        
        conn.commit()
        return {"message": "Reservation cancelled successfully"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5005)))