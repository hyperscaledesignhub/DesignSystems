from fastapi import FastAPI, HTTPException, status, BackgroundTasks
import sys
import os
import httpx
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from shared.models.base import Transaction, TransferRequest
from shared.utils.database import db_pool, get_database_url
from shared.utils.logger import setup_logger
from uuid import UUID
from decimal import Decimal
from datetime import datetime

app = FastAPI(title="Transaction Service", version="1.0.0")
logger = setup_logger("transaction-service")

WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://localhost:9082")
EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://localhost:9085")
STATE_SERVICE_URL = os.getenv("STATE_SERVICE_URL", "http://localhost:9084")

@app.on_event("startup")
async def startup():
    database_url = get_database_url("transaction-service")
    await db_pool.create_pool(database_url)
    await create_tables()
    logger.info("Transaction Service started on port 9083")

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close_pool()

async def create_tables():
    create_transactions_table = """
    CREATE TABLE IF NOT EXISTS transactions (
        id UUID PRIMARY KEY,
        from_wallet_id UUID,
        to_wallet_id UUID,
        amount DECIMAL(15,2) NOT NULL,
        currency VARCHAR(3) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        transaction_type VARCHAR(50) NOT NULL,
        idempotency_key UUID UNIQUE,
        created_at TIMESTAMP DEFAULT NOW(),
        completed_at TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_transactions_from_wallet ON transactions(from_wallet_id);
    CREATE INDEX IF NOT EXISTS idx_transactions_to_wallet ON transactions(to_wallet_id);
    CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
    CREATE INDEX IF NOT EXISTS idx_transactions_idempotency ON transactions(idempotency_key);
    """
    await db_pool.execute(create_transactions_table)

async def validate_wallet(wallet_id: UUID):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{WALLET_SERVICE_URL}/v1/wallets/{wallet_id}/validate")
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        logger.error(f"Failed to validate wallet {wallet_id}: {e}")
        return None

async def update_wallet_balance(wallet_id: UUID, amount: Decimal, operation: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WALLET_SERVICE_URL}/v1/wallets/{wallet_id}/balance/update",
                json={"amount": str(amount), "operation": operation}
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to update wallet balance {wallet_id}: {e}")
        return False

async def publish_event(event_data: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EVENT_SERVICE_URL}/v1/events/append",
                json=event_data
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        return False

async def update_state_service(wallet_id: UUID, balance: Decimal, currency: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{STATE_SERVICE_URL}/v1/state/update",
                json={
                    "wallet_id": str(wallet_id),
                    "balance": str(balance),
                    "currency": currency
                }
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to update state service: {e}")
        return False

async def get_transaction_by_id(transaction_id: UUID):
    query = "SELECT * FROM transactions WHERE id = $1"
    row = await db_pool.fetchrow(query, transaction_id)
    if row:
        return Transaction(**dict(row))
    return None

async def get_transaction_by_idempotency_key(idempotency_key: UUID):
    query = "SELECT * FROM transactions WHERE idempotency_key = $1"
    row = await db_pool.fetchrow(query, idempotency_key)
    if row:
        return Transaction(**dict(row))
    return None

async def process_transfer_transaction(transaction: Transaction):
    """Background task to process the transfer"""
    try:
        # Validate wallets
        from_wallet = await validate_wallet(transaction.from_wallet_id) if transaction.from_wallet_id else None
        to_wallet = await validate_wallet(transaction.to_wallet_id)
        
        if transaction.from_wallet_id and not from_wallet:
            await update_transaction_status(transaction.id, "failed", "Invalid from wallet")
            return
        
        if not to_wallet:
            await update_transaction_status(transaction.id, "failed", "Invalid to wallet")
            return
        
        # Check sufficient balance for debit operations
        if transaction.from_wallet_id:
            from_balance = Decimal(from_wallet["balance"])
            if from_balance < transaction.amount:
                await update_transaction_status(transaction.id, "failed", "Insufficient balance")
                return
        
        # Process the transfer (simplified Saga pattern)
        success = True
        
        # Step 1: Debit from source wallet (if exists)
        if transaction.from_wallet_id:
            if not await update_wallet_balance(transaction.from_wallet_id, transaction.amount, "debit"):
                await update_transaction_status(transaction.id, "failed", "Failed to debit source wallet")
                return
            
            # Publish debit event
            await publish_event({
                "event_type": "wallet_debited",
                "wallet_id": str(transaction.from_wallet_id),
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "transaction_id": str(transaction.id),
                "metadata": {"to_wallet": str(transaction.to_wallet_id)}
            })
        
        # Step 2: Credit to destination wallet
        if not await update_wallet_balance(transaction.to_wallet_id, transaction.amount, "credit"):
            # Rollback: Credit back to source wallet if debit was successful
            if transaction.from_wallet_id:
                await update_wallet_balance(transaction.from_wallet_id, transaction.amount, "credit")
            await update_transaction_status(transaction.id, "failed", "Failed to credit destination wallet")
            return
        
        # Publish credit event
        await publish_event({
            "event_type": "wallet_credited",
            "wallet_id": str(transaction.to_wallet_id),
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "transaction_id": str(transaction.id),
            "metadata": {"from_wallet": str(transaction.from_wallet_id) if transaction.from_wallet_id else None}
        })
        
        # Mark transaction as completed
        await update_transaction_status(transaction.id, "completed", None)
        logger.info(f"Transfer completed: {transaction.id}")
        
    except Exception as e:
        logger.error(f"Error processing transfer {transaction.id}: {e}")
        await update_transaction_status(transaction.id, "failed", str(e))

async def update_transaction_status(transaction_id: UUID, status: str, error_message: str = None):
    completed_at = datetime.utcnow() if status in ["completed", "failed"] else None
    query = """
    UPDATE transactions 
    SET status = $1, completed_at = $2 
    WHERE id = $3
    """
    await db_pool.execute(query, status, completed_at, transaction_id)

@app.post("/v1/transactions/transfer")
async def create_transfer(transfer_data: TransferRequest, background_tasks: BackgroundTasks):
    # Check for existing transaction with same idempotency key
    existing_transaction = await get_transaction_by_idempotency_key(transfer_data.idempotency_key)
    if existing_transaction:
        return {
            "message": "Transaction already exists",
            "transaction_id": str(existing_transaction.id),
            "status": existing_transaction.status
        }
    
    # Create new transaction
    transaction = Transaction(
        from_wallet_id=transfer_data.from_wallet_id,
        to_wallet_id=transfer_data.to_wallet_id,
        amount=transfer_data.amount,
        currency=transfer_data.currency,
        transaction_type="transfer",
        idempotency_key=transfer_data.idempotency_key
    )
    
    query = """
    INSERT INTO transactions (
        id, from_wallet_id, to_wallet_id, amount, currency, 
        status, transaction_type, idempotency_key, created_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """
    await db_pool.execute(
        query, transaction.id, transaction.from_wallet_id, transaction.to_wallet_id,
        transaction.amount, transaction.currency, transaction.status,
        transaction.transaction_type, transaction.idempotency_key, transaction.created_at
    )
    
    # Process transfer in background
    background_tasks.add_task(process_transfer_transaction, transaction)
    
    logger.info(f"Transfer initiated: {transaction.id}")
    return {
        "message": "Transfer initiated",
        "transaction_id": str(transaction.id),
        "status": "pending"
    }

@app.get("/v1/transactions/{transaction_id}")
async def get_transaction(transaction_id: UUID):
    transaction = await get_transaction_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return {
        "transaction_id": str(transaction.id),
        "from_wallet_id": str(transaction.from_wallet_id) if transaction.from_wallet_id else None,
        "to_wallet_id": str(transaction.to_wallet_id),
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "status": transaction.status,
        "transaction_type": transaction.transaction_type,
        "created_at": transaction.created_at,
        "completed_at": transaction.completed_at
    }

@app.get("/v1/transactions/wallet/{wallet_id}")
async def get_wallet_transactions(wallet_id: UUID, limit: int = 50, offset: int = 0):
    query = """
    SELECT * FROM transactions 
    WHERE from_wallet_id = $1 OR to_wallet_id = $1 
    ORDER BY created_at DESC 
    LIMIT $2 OFFSET $3
    """
    rows = await db_pool.fetch(query, wallet_id, limit, offset)
    
    transactions = []
    for row in rows:
        transaction = Transaction(**dict(row))
        transactions.append({
            "transaction_id": str(transaction.id),
            "from_wallet_id": str(transaction.from_wallet_id) if transaction.from_wallet_id else None,
            "to_wallet_id": str(transaction.to_wallet_id),
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status,
            "transaction_type": transaction.transaction_type,
            "created_at": transaction.created_at,
            "completed_at": transaction.completed_at
        })
    
    return {
        "wallet_id": str(wallet_id),
        "transactions": transactions,
        "count": len(transactions)
    }

@app.post("/v1/transactions/deposit")
async def create_deposit(deposit_data: dict, background_tasks: BackgroundTasks):
    """Create a deposit transaction (credit only)"""
    wallet_id = UUID(deposit_data["wallet_id"])
    amount = Decimal(str(deposit_data["amount"]))
    currency = deposit_data.get("currency", "USD")
    idempotency_key = UUID(deposit_data["idempotency_key"])
    
    # Check for existing transaction
    existing_transaction = await get_transaction_by_idempotency_key(idempotency_key)
    if existing_transaction:
        return {
            "message": "Transaction already exists",
            "transaction_id": str(existing_transaction.id),
            "status": existing_transaction.status
        }
    
    transaction = Transaction(
        from_wallet_id=None,  # No source wallet for deposits
        to_wallet_id=wallet_id,
        amount=amount,
        currency=currency,
        transaction_type="deposit",
        idempotency_key=idempotency_key
    )
    
    query = """
    INSERT INTO transactions (
        id, from_wallet_id, to_wallet_id, amount, currency, 
        status, transaction_type, idempotency_key, created_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """
    await db_pool.execute(
        query, transaction.id, None, transaction.to_wallet_id,
        transaction.amount, transaction.currency, transaction.status,
        transaction.transaction_type, transaction.idempotency_key, transaction.created_at
    )
    
    background_tasks.add_task(process_transfer_transaction, transaction)
    
    logger.info(f"Deposit initiated: {transaction.id}")
    return {
        "message": "Deposit initiated",
        "transaction_id": str(transaction.id),
        "status": "pending"
    }

@app.post("/v1/transactions/withdraw")
async def create_withdrawal(withdraw_data: dict, background_tasks: BackgroundTasks):
    """Create a withdrawal transaction (debit only)"""
    wallet_id = UUID(withdraw_data["wallet_id"])
    amount = Decimal(str(withdraw_data["amount"]))
    currency = withdraw_data.get("currency", "USD")
    idempotency_key = UUID(withdraw_data["idempotency_key"])
    
    # Check for existing transaction
    existing_transaction = await get_transaction_by_idempotency_key(idempotency_key)
    if existing_transaction:
        return {
            "message": "Transaction already exists",
            "transaction_id": str(existing_transaction.id),
            "status": existing_transaction.status
        }
    
    # Validate wallet exists and has sufficient balance
    try:
        async with httpx.AsyncClient() as client:
            wallet_response = await client.get(f"{WALLET_SERVICE_URL}/v1/wallets/{wallet_id}/validate")
            if wallet_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Wallet not found or inactive"
                )
            
            wallet_data = wallet_response.json()
            current_balance = Decimal(wallet_data["balance"])
            
            if current_balance < amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient balance"
                )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wallet service unavailable"
        )
    
    # Create withdrawal transaction
    transaction = Transaction(
        from_wallet_id=wallet_id,
        to_wallet_id=None,  # No destination for withdrawal
        amount=amount,
        currency=currency,
        transaction_type="withdraw",
        idempotency_key=idempotency_key
    )
    
    # Save transaction
    query = """
    INSERT INTO transactions (id, from_wallet_id, to_wallet_id, amount, currency, status, transaction_type, idempotency_key, created_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """
    await db_pool.execute(
        query, transaction.id, transaction.from_wallet_id, None,
        transaction.amount, transaction.currency, transaction.status,
        transaction.transaction_type, transaction.idempotency_key, transaction.created_at
    )
    
    background_tasks.add_task(process_withdrawal_transaction, transaction)
    
    logger.info(f"Withdrawal initiated: {transaction.id}")
    return {
        "message": "Withdrawal initiated",
        "transaction_id": str(transaction.id),
        "status": "pending"
    }

async def process_withdrawal_transaction(transaction: Transaction):
    """Process withdrawal transaction by debiting wallet"""
    try:
        # Update wallet balance (debit)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WALLET_SERVICE_URL}/v1/wallets/{transaction.from_wallet_id}/balance/update",
                json={
                    "amount": str(transaction.amount),
                    "operation": "debit"
                }
            )
            
            if response.status_code == 200:
                # Mark transaction as completed
                await update_transaction_status(transaction.id, "completed")
                logger.info(f"Withdrawal completed: {transaction.id}")
            else:
                await update_transaction_status(transaction.id, "failed")
                logger.error(f"Withdrawal failed: {transaction.id}")
                
    except Exception as e:
        await update_transaction_status(transaction.id, "failed")
        logger.error(f"Withdrawal processing error: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "transaction-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9083)