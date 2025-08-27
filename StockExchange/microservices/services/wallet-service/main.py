import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
import uvicorn
import httpx
import uuid

from shared.models.base import Wallet
from shared.utils.database import DatabaseManager, get_database_url
from shared.utils.auth import verify_token
from models import WalletDB, TransactionDB
from shared.tracing import setup_tracing, instrument_fastapi, TracingMiddleware

tracer = setup_tracing("wallet-service")
app = FastAPI(title="Wallet Service", version="1.0.0")
instrument_fastapi(app)
app.add_middleware(TracingMiddleware, service_name="wallet-service")
security = HTTPBearer()

# Database setup
db_manager = DatabaseManager(get_database_url("wallet"))

class WalletCreate(BaseModel):
    user_id: int
    initial_balance: Decimal = Decimal("10000")  # Default balance for demo

class BalanceUpdate(BaseModel):
    amount: Decimal
    transaction_type: str  # CREDIT, DEBIT
    reference_id: str = None
    description: str = None

class BlockFunds(BaseModel):
    amount: Decimal
    reference_id: str

async def get_db():
    async for session in db_manager.get_session():
        yield session

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)

@app.post("/create", response_model=Wallet)
async def create_wallet(
    wallet_data: WalletCreate,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(verify_user_token)
):
    # Check if wallet already exists
    result = await db.execute(
        select(WalletDB).where(WalletDB.user_id == wallet_data.user_id)
    )
    existing_wallet = result.scalar_one_or_none()
    
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet already exists for this user"
        )
    
    # Create new wallet
    db_wallet = WalletDB(
        user_id=wallet_data.user_id,
        available_balance=wallet_data.initial_balance
    )
    
    db.add(db_wallet)
    await db.commit()
    await db.refresh(db_wallet)
    
    return Wallet(
        id=db_wallet.id,
        user_id=db_wallet.user_id,
        currency=db_wallet.currency,
        available_balance=db_wallet.available_balance,
        blocked_balance=db_wallet.blocked_balance,
        updated_at=db_wallet.updated_at
    )

@app.get("/balance/{user_id}", response_model=Wallet)
async def get_balance(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(verify_user_token)
):
    result = await db.execute(
        select(WalletDB).where(WalletDB.user_id == user_id)
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    return Wallet(
        id=wallet.id,
        user_id=wallet.user_id,
        currency=wallet.currency,
        available_balance=wallet.available_balance,
        blocked_balance=wallet.blocked_balance,
        updated_at=wallet.updated_at
    )

@app.post("/block-funds/{user_id}")
async def block_funds(
    user_id: int,
    block_data: BlockFunds,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(verify_user_token)
):
    result = await db.execute(
        select(WalletDB).where(WalletDB.user_id == user_id)
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    if wallet.available_balance < block_data.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance"
        )
    
    # Block funds
    wallet.available_balance -= block_data.amount
    wallet.blocked_balance += block_data.amount
    
    # Record transaction
    transaction = TransactionDB(
        user_id=user_id,
        amount=block_data.amount,
        transaction_type="BLOCK",
        reference_id=uuid.UUID(block_data.reference_id) if block_data.reference_id else None,
        description=f"Blocked funds for order {block_data.reference_id}",
        balance_after=wallet.available_balance
    )
    
    db.add(transaction)
    await db.commit()
    
    return {"message": "Funds blocked successfully", "amount": block_data.amount}

@app.post("/unblock-funds/{user_id}")
async def unblock_funds(
    user_id: int,
    block_data: BlockFunds,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(verify_user_token)
):
    result = await db.execute(
        select(WalletDB).where(WalletDB.user_id == user_id)
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    if wallet.blocked_balance < block_data.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient blocked balance"
        )
    
    # Unblock funds
    wallet.blocked_balance -= block_data.amount
    wallet.available_balance += block_data.amount
    
    # Record transaction
    transaction = TransactionDB(
        user_id=user_id,
        amount=block_data.amount,
        transaction_type="UNBLOCK",
        reference_id=block_data.reference_id,
        description=f"Unblocked funds for order {block_data.reference_id}",
        balance_after=wallet.available_balance
    )
    
    db.add(transaction)
    await db.commit()
    
    return {"message": "Funds unblocked successfully", "amount": block_data.amount}

@app.post("/update-balance/{user_id}")
async def update_balance(
    user_id: int,
    balance_data: BalanceUpdate,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(verify_user_token)
):
    result = await db.execute(
        select(WalletDB).where(WalletDB.user_id == user_id)
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        # If it's a deposit and wallet doesn't exist, create it
        if balance_data.transaction_type in ["DEPOSIT", "CREDIT"]:
            wallet = WalletDB(
                user_id=user_id,
                available_balance=Decimal("0")
            )
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
    
    # Map transaction types for database constraints
    db_transaction_type = balance_data.transaction_type
    if balance_data.transaction_type == "DEBIT":
        if wallet.available_balance < balance_data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance"
            )
        wallet.available_balance -= balance_data.amount
        db_transaction_type = "WITHDRAWAL"
    elif balance_data.transaction_type == "CREDIT":
        wallet.available_balance += balance_data.amount
        db_transaction_type = "DEPOSIT"
    elif balance_data.transaction_type in ["DEPOSIT", "WITHDRAWAL", "TRADE_BUY", "TRADE_SELL"]:
        if balance_data.transaction_type in ["WITHDRAWAL", "TRADE_BUY"]:
            if wallet.available_balance < balance_data.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient balance"
                )
            wallet.available_balance -= balance_data.amount
        else:  # DEPOSIT, TRADE_SELL
            wallet.available_balance += balance_data.amount
        db_transaction_type = balance_data.transaction_type
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction type"
        )
    
    # Record transaction
    transaction = TransactionDB(
        user_id=user_id,
        amount=balance_data.amount,
        transaction_type=db_transaction_type,
        reference_id=balance_data.reference_id,
        description=balance_data.description,
        balance_after=wallet.available_balance
    )
    
    db.add(transaction)
    await db.commit()
    
    return {"message": "Balance updated successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8651)