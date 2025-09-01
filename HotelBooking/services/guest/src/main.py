from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Guest Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/guest_db")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

class GuestCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None

class Guest(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

@app.on_event("startup")
async def startup_event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            phone VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "guest"}

@app.post("/guests/register", response_model=Guest, status_code=201)
def register_guest(guest: GuestCreate):
    guest_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO guests (id, email, first_name, last_name, phone)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """, (guest_id, guest.email, guest.first_name, guest.last_name, guest.phone))
        
        new_guest = cur.fetchone()
        conn.commit()
        
        return new_guest
        
    except psycopg2.IntegrityError:
        conn.rollback()
        # Guest already exists, return existing guest
        cur.execute("SELECT * FROM guests WHERE email = %s", (guest.email,))
        existing_guest = cur.fetchone()
        return existing_guest
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

@app.get("/guests/{guest_id}", response_model=Guest)
def get_guest(guest_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM guests WHERE id = %s", (guest_id,))
        guest = cur.fetchone()
        
        if not guest:
            raise HTTPException(status_code=404, detail="Guest not found")
        
        return guest
        
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5003)))