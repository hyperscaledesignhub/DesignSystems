from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Payment Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/payment_db")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

class PaymentCreate(BaseModel):
    reservation_id: str
    amount: float
    currency: str = "USD"
    payment_method: str

class Payment(BaseModel):
    id: str
    reservation_id: str
    amount: float
    currency: str
    payment_method: str
    status: str
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

@app.on_event("startup")
async def startup_event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id VARCHAR(36) PRIMARY KEY,
            reservation_id VARCHAR(36) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'USD',
            payment_method VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'completed',
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "payment"}

@app.post("/payments/process", response_model=Payment, status_code=201)
def process_payment(payment: PaymentCreate):
    payment_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Simulate payment processing (always successful for demo)
        cur.execute("""
            INSERT INTO payments (id, reservation_id, amount, currency, payment_method, status, processed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            payment_id, 
            payment.reservation_id, 
            payment.amount, 
            payment.currency,
            payment.payment_method, 
            'completed', 
            datetime.utcnow()
        ))
        
        new_payment = cur.fetchone()
        
        # Update reservation status to 'paid'
        try:
            reservation_db_url = os.getenv("RESERVATION_DATABASE_URL", "postgresql://postgres:postgres@postgres-db:5432/reservation_db")
            res_conn = psycopg2.connect(reservation_db_url, cursor_factory=RealDictCursor)
            res_cur = res_conn.cursor()
            res_cur.execute("""
                UPDATE reservations 
                SET status = 'paid' 
                WHERE id = %s
            """, (payment.reservation_id,))
            res_conn.commit()
            res_cur.close()
            res_conn.close()
        except Exception as e:
            # Log error but don't fail payment if reservation update fails
            print(f"Failed to update reservation status: {str(e)}")
        
        conn.commit()
        
        return new_payment
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

@app.get("/payments", response_model=List[Payment])
def get_payments(reservation_id: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if reservation_id:
            cur.execute("SELECT * FROM payments WHERE reservation_id = %s ORDER BY created_at DESC", (reservation_id,))
        else:
            cur.execute("SELECT * FROM payments ORDER BY created_at DESC LIMIT 100")
        
        payments = cur.fetchall()
        return payments if payments else []
        
    finally:
        cur.close()
        conn.close()

@app.get("/payments/{payment_id}", response_model=Payment)
def get_payment(payment_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
        payment = cur.fetchone()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return payment
        
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5006)))