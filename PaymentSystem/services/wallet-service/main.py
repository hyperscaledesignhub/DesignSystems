"""
Wallet Service - Manages user wallets and balances
"""
import os
import sys
import asyncio
import asyncpg
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis.asyncio as redis
import json

# Import tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing
tracer = setup_tracing("wallet-service")

# Create FastAPI app
app = FastAPI(title="Wallet Service", version="1.0.0")
instrument_fastapi(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None

# Pydantic models
class WalletCreate(BaseModel):
    user_id: str
    currency: str = "USD"
    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    wallet_type: str = "personal"  # personal, business, merchant

class WalletResponse(BaseModel):
    wallet_id: str
    user_id: str
    balance: Decimal
    currency: str
    wallet_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    holds: Decimal = Decimal("0.00")
    available_balance: Decimal

class TransactionRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    transaction_type: str  # credit, debit, hold, release
    reference_id: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TransferRequest(BaseModel):
    from_wallet_id: str
    to_wallet_id: str
    amount: Decimal = Field(gt=0)
    description: Optional[str] = None

class WalletTransaction(BaseModel):
    transaction_id: str
    wallet_id: str
    amount: Decimal
    transaction_type: str
    balance_before: Decimal
    balance_after: Decimal
    reference_id: str
    description: Optional[str]
    created_at: datetime
    status: str

async def get_db_pool():
    """Get database connection pool"""
    return db_pool

async def get_redis():
    """Get Redis client"""
    return redis_client

@app.on_event("startup")
async def startup():
    """Initialize database and Redis connections"""
    global db_pool, redis_client
    
    with tracer.start_as_current_span("service_startup"):
        # Connect to PostgreSQL
        db_url = os.getenv("DATABASE_URL", "postgresql://wallet_user:wallet_pass@postgres-wallet:5432/wallet_db")
        db_pool = await asyncpg.create_pool(db_url, min_size=5, max_size=20)
        
        # Initialize database schema
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    wallet_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    balance DECIMAL(20, 2) DEFAULT 0.00,
                    holds DECIMAL(20, 2) DEFAULT 0.00,
                    currency VARCHAR(3) DEFAULT 'USD',
                    wallet_type VARCHAR(20) DEFAULT 'personal',
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets(user_id);
                CREATE INDEX IF NOT EXISTS idx_wallets_status ON wallets(status);
                
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    transaction_id VARCHAR(50) PRIMARY KEY,
                    wallet_id VARCHAR(50) REFERENCES wallets(wallet_id),
                    amount DECIMAL(20, 2) NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    balance_before DECIMAL(20, 2) NOT NULL,
                    balance_after DECIMAL(20, 2) NOT NULL,
                    reference_id VARCHAR(100),
                    description TEXT,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'completed'
                );
                
                CREATE INDEX IF NOT EXISTS idx_transactions_wallet_id ON wallet_transactions(wallet_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_reference_id ON wallet_transactions(reference_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON wallet_transactions(created_at);
            """)
        
        # Connect to Redis
        redis_url = os.getenv("REDIS_URL", "redis://redis-wallet:6379")
        redis_client = await redis.from_url(redis_url, decode_responses=True)
        
        print("✅ Wallet Service started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup connections"""
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "wallet-service",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/wallets", response_model=WalletResponse)
async def create_wallet(
    wallet: WalletCreate,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a new wallet for a user"""
    with tracer.start_as_current_span("create_wallet", attributes=create_span_attributes(
        user_id=wallet.user_id,
        wallet_type=wallet.wallet_type,
        initial_balance=str(wallet.initial_balance)
    )):
        wallet_id = f"WLT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{wallet.user_id[:4]}"
        
        async with db.acquire() as conn:
            # Allow multiple wallets per user for demo purposes
            # In production, you might want to limit the number of wallets per user/type
            
            # Create wallet
            result = await conn.fetchrow("""
                INSERT INTO wallets (wallet_id, user_id, balance, currency, wallet_type, status)
                VALUES ($1, $2, $3, $4, $5, 'active')
                RETURNING *
            """, wallet_id, wallet.user_id, wallet.initial_balance, wallet.currency, wallet.wallet_type)
            
            # Record initial transaction if balance > 0
            if wallet.initial_balance > 0:
                transaction_id = f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                await conn.execute("""
                    INSERT INTO wallet_transactions 
                    (transaction_id, wallet_id, amount, transaction_type, balance_before, balance_after, reference_id, description)
                    VALUES ($1, $2, $3, 'credit', 0, $3, $4, 'Initial deposit')
                """, transaction_id, wallet_id, wallet.initial_balance, f"INIT_{wallet_id}")
            
            # Cache wallet info
            await redis_client.setex(
                f"wallet:{wallet_id}",
                3600,
                json.dumps({
                    "wallet_id": wallet_id,
                    "user_id": wallet.user_id,
                    "balance": str(wallet.initial_balance),
                    "currency": wallet.currency,
                    "wallet_type": wallet.wallet_type
                })
            )
            
            return WalletResponse(
                wallet_id=result['wallet_id'],
                user_id=result['user_id'],
                balance=result['balance'],
                currency=result['currency'],
                wallet_type=result['wallet_type'],
                status=result['status'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                holds=result['holds'],
                available_balance=result['balance'] - result['holds']
            )

@app.get("/api/v1/wallets/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get wallet details by ID"""
    with tracer.start_as_current_span("get_wallet", attributes=create_span_attributes(
        wallet_id=wallet_id
    )):
        # Try cache first
        cached = await redis_client.get(f"wallet:{wallet_id}")
        if cached:
            data = json.loads(cached)
            async with db.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM wallets WHERE wallet_id = $1",
                    wallet_id
                )
        else:
            async with db.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM wallets WHERE wallet_id = $1",
                    wallet_id
                )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return WalletResponse(
            wallet_id=result['wallet_id'],
            user_id=result['user_id'],
            balance=result['balance'],
            currency=result['currency'],
            wallet_type=result['wallet_type'],
            status=result['status'],
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            holds=result['holds'],
            available_balance=result['balance'] - result['holds']
        )

@app.get("/api/v1/users/{user_id}/wallets", response_model=List[WalletResponse])
async def get_user_wallets(
    user_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get all wallets for a user"""
    with tracer.start_as_current_span("get_user_wallets", attributes=create_span_attributes(
        user_id=user_id
    )):
        async with db.acquire() as conn:
            results = await conn.fetch(
                "SELECT * FROM wallets WHERE user_id = $1 AND status = 'active' ORDER BY created_at DESC",
                user_id
            )
        
        return [
            WalletResponse(
                wallet_id=row['wallet_id'],
                user_id=row['user_id'],
                balance=row['balance'],
                currency=row['currency'],
                wallet_type=row['wallet_type'],
                status=row['status'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                holds=row['holds'],
                available_balance=row['balance'] - row['holds']
            )
            for row in results
        ]

@app.post("/api/v1/wallets/{wallet_id}/transactions", response_model=WalletTransaction)
async def create_transaction(
    wallet_id: str,
    transaction: TransactionRequest,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a transaction on a wallet"""
    with tracer.start_as_current_span("create_transaction", attributes=create_span_attributes(
        wallet_id=wallet_id,
        transaction_type=transaction.transaction_type,
        amount=str(transaction.amount),
        reference_id=transaction.reference_id
    )):
        transaction_id = f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        async with db.acquire() as conn:
            async with conn.transaction():
                # Lock wallet row for update
                wallet = await conn.fetchrow(
                    "SELECT * FROM wallets WHERE wallet_id = $1 FOR UPDATE",
                    wallet_id
                )
                
                if not wallet:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Wallet not found"
                    )
                
                if wallet['status'] != 'active':
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Wallet is not active"
                    )
                
                balance_before = wallet['balance']
                holds_before = wallet['holds']
                
                # Process transaction based on type
                if transaction.transaction_type == 'credit':
                    balance_after = balance_before + transaction.amount
                    await conn.execute(
                        "UPDATE wallets SET balance = $1, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = $2",
                        balance_after, wallet_id
                    )
                    
                elif transaction.transaction_type == 'debit':
                    available = balance_before - holds_before
                    if available < transaction.amount:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Insufficient funds. Available: {available}"
                        )
                    balance_after = balance_before - transaction.amount
                    await conn.execute(
                        "UPDATE wallets SET balance = $1, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = $2",
                        balance_after, wallet_id
                    )
                    
                elif transaction.transaction_type == 'hold':
                    available = balance_before - holds_before
                    if available < transaction.amount:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Insufficient funds for hold. Available: {available}"
                        )
                    balance_after = balance_before  # Balance doesn't change for holds
                    await conn.execute(
                        "UPDATE wallets SET holds = holds + $1, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = $2",
                        transaction.amount, wallet_id
                    )
                    
                elif transaction.transaction_type == 'release':
                    if holds_before < transaction.amount:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Cannot release more than held. Held: {holds_before}"
                        )
                    balance_after = balance_before
                    await conn.execute(
                        "UPDATE wallets SET holds = holds - $1, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = $2",
                        transaction.amount, wallet_id
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid transaction type: {transaction.transaction_type}"
                    )
                
                # Record transaction
                result = await conn.fetchrow("""
                    INSERT INTO wallet_transactions 
                    (transaction_id, wallet_id, amount, transaction_type, balance_before, balance_after, 
                     reference_id, description, metadata, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'completed')
                    RETURNING *
                """, transaction_id, wallet_id, transaction.amount, transaction.transaction_type,
                    balance_before, balance_after, transaction.reference_id, transaction.description,
                    json.dumps(transaction.metadata or {}))
                
                # Invalidate cache
                await redis_client.delete(f"wallet:{wallet_id}")
                
                return WalletTransaction(
                    transaction_id=result['transaction_id'],
                    wallet_id=result['wallet_id'],
                    amount=result['amount'],
                    transaction_type=result['transaction_type'],
                    balance_before=result['balance_before'],
                    balance_after=result['balance_after'],
                    reference_id=result['reference_id'],
                    description=result['description'],
                    created_at=result['created_at'],
                    status=result['status']
                )

@app.post("/api/v1/wallets/transfer")
async def transfer_funds(
    transfer: TransferRequest,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Transfer funds between wallets"""
    with tracer.start_as_current_span("transfer_funds", attributes=create_span_attributes(
        from_wallet=transfer.from_wallet_id,
        to_wallet=transfer.to_wallet_id,
        amount=str(transfer.amount)
    )):
        transfer_id = f"TRF{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        async with db.acquire() as conn:
            async with conn.transaction():
                # Lock both wallets
                from_wallet = await conn.fetchrow(
                    "SELECT * FROM wallets WHERE wallet_id = $1 FOR UPDATE",
                    transfer.from_wallet_id
                )
                to_wallet = await conn.fetchrow(
                    "SELECT * FROM wallets WHERE wallet_id = $1 FOR UPDATE",
                    transfer.to_wallet_id
                )
                
                if not from_wallet or not to_wallet:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="One or both wallets not found"
                    )
                
                # Check available balance
                available = from_wallet['balance'] - from_wallet['holds']
                if available < transfer.amount:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient funds. Available: {available}"
                    )
                
                # Perform transfer
                await conn.execute(
                    "UPDATE wallets SET balance = balance - $1, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = $2",
                    transfer.amount, transfer.from_wallet_id
                )
                await conn.execute(
                    "UPDATE wallets SET balance = balance + $1, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = $2",
                    transfer.amount, transfer.to_wallet_id
                )
                
                # Record transactions
                await conn.execute("""
                    INSERT INTO wallet_transactions 
                    (transaction_id, wallet_id, amount, transaction_type, balance_before, balance_after, 
                     reference_id, description)
                    VALUES ($1, $2, $3, 'debit', $4, $5, $6, $7)
                """, f"{transfer_id}_D", transfer.from_wallet_id, transfer.amount,
                    from_wallet['balance'], from_wallet['balance'] - transfer.amount,
                    transfer_id, transfer.description or f"Transfer to {transfer.to_wallet_id}")
                
                await conn.execute("""
                    INSERT INTO wallet_transactions 
                    (transaction_id, wallet_id, amount, transaction_type, balance_before, balance_after, 
                     reference_id, description)
                    VALUES ($1, $2, $3, 'credit', $4, $5, $6, $7)
                """, f"{transfer_id}_C", transfer.to_wallet_id, transfer.amount,
                    to_wallet['balance'], to_wallet['balance'] + transfer.amount,
                    transfer_id, transfer.description or f"Transfer from {transfer.from_wallet_id}")
                
                # Invalidate cache
                await redis_client.delete(f"wallet:{transfer.from_wallet_id}")
                await redis_client.delete(f"wallet:{transfer.to_wallet_id}")
                
                return {
                    "transfer_id": transfer_id,
                    "from_wallet_id": transfer.from_wallet_id,
                    "to_wallet_id": transfer.to_wallet_id,
                    "amount": str(transfer.amount),
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }

@app.get("/api/v1/wallets/{wallet_id}/transactions", response_model=List[WalletTransaction])
async def get_wallet_transactions(
    wallet_id: str,
    limit: int = 50,
    offset: int = 0,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get transaction history for a wallet"""
    with tracer.start_as_current_span("get_wallet_transactions", attributes=create_span_attributes(
        wallet_id=wallet_id,
        limit=limit,
        offset=offset
    )):
        async with db.acquire() as conn:
            results = await conn.fetch("""
                SELECT * FROM wallet_transactions 
                WHERE wallet_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2 OFFSET $3
            """, wallet_id, limit, offset)
        
        return [
            WalletTransaction(
                transaction_id=row['transaction_id'],
                wallet_id=row['wallet_id'],
                amount=row['amount'],
                transaction_type=row['transaction_type'],
                balance_before=row['balance_before'],
                balance_after=row['balance_after'],
                reference_id=row['reference_id'],
                description=row['description'],
                created_at=row['created_at'],
                status=row['status']
            )
            for row in results
        ]

@app.get("/api/v1/wallets/stats/summary")
async def get_wallet_stats(
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get wallet system statistics"""
    with tracer.start_as_current_span("get_wallet_stats"):
        async with db.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT wallet_id) as total_wallets,
                    COUNT(DISTINCT user_id) as total_users,
                    SUM(balance) as total_balance,
                    SUM(holds) as total_holds,
                    COUNT(CASE WHEN wallet_type = 'personal' THEN 1 END) as personal_wallets,
                    COUNT(CASE WHEN wallet_type = 'business' THEN 1 END) as business_wallets,
                    COUNT(CASE WHEN wallet_type = 'merchant' THEN 1 END) as merchant_wallets
                FROM wallets 
                WHERE status = 'active'
            """)
            
            transactions = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END) as total_credits,
                    SUM(CASE WHEN transaction_type = 'debit' THEN amount ELSE 0 END) as total_debits,
                    COUNT(DISTINCT wallet_id) as active_wallets
                FROM wallet_transactions 
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """)
        
        return {
            "wallets": {
                "total": stats['total_wallets'],
                "users": stats['total_users'],
                "personal": stats['personal_wallets'],
                "business": stats['business_wallets'],
                "merchant": stats['merchant_wallets']
            },
            "balances": {
                "total": str(stats['total_balance'] or 0),
                "holds": str(stats['total_holds'] or 0),
                "available": str((stats['total_balance'] or 0) - (stats['total_holds'] or 0))
            },
            "transactions_24h": {
                "total": transactions['total_transactions'],
                "credits": str(transactions['total_credits'] or 0),
                "debits": str(transactions['total_debits'] or 0),
                "active_wallets": transactions['active_wallets']
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8740)