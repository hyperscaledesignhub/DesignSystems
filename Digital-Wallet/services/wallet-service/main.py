from fastapi import FastAPI, HTTPException, status
import sys
import os
import httpx
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.models.base import Wallet, WalletCreation
from shared.utils.database import db_pool, get_database_url
from shared.utils.logger import setup_logger
from uuid import UUID
from decimal import Decimal

app = FastAPI(title="Wallet Service", version="1.0.0")
logger = setup_logger("wallet-service")

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:9081")

@app.on_event("startup")
async def startup():
    database_url = get_database_url("wallet-service")
    await db_pool.create_pool(database_url)
    await create_tables()
    logger.info("Wallet Service started on port 9082")

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close_pool()

async def create_tables():
    create_wallets_table = """
    CREATE TABLE IF NOT EXISTS wallets (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL,
        balance DECIMAL(15,2) DEFAULT 0.00,
        currency VARCHAR(3) DEFAULT 'USD',
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets(user_id);
    """
    await db_pool.execute(create_wallets_table)

async def validate_user(user_id: UUID) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{USER_SERVICE_URL}/v1/users/validate/{user_id}")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to validate user {user_id}: {e}")
        return False

async def get_wallet_by_id(wallet_id: UUID):
    query = "SELECT * FROM wallets WHERE id = $1"
    row = await db_pool.fetchrow(query, wallet_id)
    if row:
        return Wallet(**dict(row))
    return None

async def get_wallets_by_user(user_id: UUID):
    query = "SELECT * FROM wallets WHERE user_id = $1"
    rows = await db_pool.fetch(query, user_id)
    return [Wallet(**dict(row)) for row in rows]

@app.post("/v1/wallets/create")
async def create_wallet(wallet_data: WalletCreation):
    if not await validate_user(wallet_data.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user"
        )
    
    existing_wallets = await get_wallets_by_user(wallet_data.user_id)
    if len(existing_wallets) >= 5:  # Limit wallets per user
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum wallets limit reached"
        )
    
    wallet = Wallet(
        user_id=wallet_data.user_id,
        currency=wallet_data.currency
    )
    
    query = """
    INSERT INTO wallets (id, user_id, balance, currency, status, created_at, updated_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    """
    await db_pool.execute(
        query, wallet.id, wallet.user_id, wallet.balance, 
        wallet.currency, wallet.status, wallet.created_at, wallet.updated_at
    )
    
    logger.info(f"Wallet created: {wallet.id} for user {wallet.user_id}")
    return {"message": "Wallet created successfully", "wallet_id": str(wallet.id)}

@app.get("/v1/wallets/{wallet_id}/balance")
async def get_wallet_balance(wallet_id: UUID):
    wallet = await get_wallet_by_id(wallet_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    return {
        "wallet_id": str(wallet.id),
        "balance": str(wallet.balance),
        "currency": wallet.currency,
        "status": wallet.status
    }

@app.get("/v1/wallets/user/{user_id}")
async def get_user_wallets(user_id: UUID):
    if not await validate_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user"
        )
    
    wallets = await get_wallets_by_user(user_id)
    
    return {
        "user_id": str(user_id),
        "wallets": [
            {
                "wallet_id": str(wallet.id),
                "balance": str(wallet.balance),
                "currency": wallet.currency,
                "status": wallet.status,
                "created_at": wallet.created_at
            }
            for wallet in wallets
        ]
    }

@app.put("/v1/wallets/{wallet_id}/status")
async def update_wallet_status(wallet_id: UUID, status_data: dict):
    wallet = await get_wallet_by_id(wallet_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    new_status = status_data.get("status")
    if new_status not in ["active", "inactive", "frozen"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status"
        )
    
    query = "UPDATE wallets SET status = $1, updated_at = NOW() WHERE id = $2"
    await db_pool.execute(query, new_status, wallet_id)
    
    logger.info(f"Wallet status updated: {wallet_id} -> {new_status}")
    return {"message": "Wallet status updated successfully"}

@app.post("/v1/wallets/{wallet_id}/balance/update")
async def update_wallet_balance(wallet_id: UUID, balance_data: dict):
    """Internal API for balance updates from transaction service"""
    wallet = await get_wallet_by_id(wallet_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    if wallet.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet is not active"
        )
    
    amount = Decimal(str(balance_data.get("amount", "0")))
    operation = balance_data.get("operation")  # "credit" or "debit"
    
    if operation == "credit":
        new_balance = wallet.balance + amount
    elif operation == "debit":
        if wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance"
            )
        new_balance = wallet.balance - amount
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid operation"
        )
    
    query = "UPDATE wallets SET balance = $1, updated_at = NOW() WHERE id = $2"
    await db_pool.execute(query, new_balance, wallet_id)
    
    logger.info(f"Wallet balance updated: {wallet_id} {operation} {amount} -> {new_balance}")
    return {
        "wallet_id": str(wallet_id),
        "new_balance": str(new_balance),
        "operation": operation,
        "amount": str(amount)
    }

@app.get("/v1/wallets/{wallet_id}/validate")
async def validate_wallet(wallet_id: UUID):
    wallet = await get_wallet_by_id(wallet_id)
    if not wallet or wallet.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found or inactive"
        )
    
    return {
        "valid": True,
        "wallet_id": str(wallet.id),
        "balance": str(wallet.balance),
        "currency": wallet.currency
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "wallet-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9082)