import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import uvicorn
import httpx
import asyncio
import uuid
import json
import redis.asyncio as redis

from shared.models.base import Order, OrderSide, OrderStatus, OrderType, Execution
from shared.utils.database import DatabaseManager, get_database_url, get_redis_url
from shared.utils.auth import verify_token
from models import OrderDB, ExecutionDB
from shared.tracing import setup_tracing, instrument_fastapi, TracingMiddleware

tracer = setup_tracing("order-manager")
app = FastAPI(title="Order Manager Service", version="1.0.0")
instrument_fastapi(app)
app.add_middleware(TracingMiddleware, service_name="order-manager")
security = HTTPBearer()

# Database setup
db_manager = DatabaseManager(get_database_url("order"))

# Service URLs
RISK_MANAGER_URL = "http://risk-manager:8539"
WALLET_SERVICE_URL = "http://wallet-service:8651"
MATCHING_ENGINE_URL = "http://matching-engine:8792"
NOTIFICATION_SERVICE_URL = "http://notification-service:9243"

# Redis for listening to executions
redis_client = None

class OrderCreate(BaseModel):
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.LIMIT
    quantity: Decimal
    price: Decimal

class OrderCancel(BaseModel):
    order_id: str

async def get_db():
    async for session in db_manager.get_session():
        yield session

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(get_redis_url())
    return redis_client

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)

async def call_risk_manager(user_id: int, order_data: OrderCreate, token: str) -> bool:
    """Call risk manager to check if order is allowed"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{RISK_MANAGER_URL}/check-risk",
                json={
                    "user_id": user_id,
                    "symbol": order_data.symbol,
                    "side": order_data.side,
                    "quantity": str(order_data.quantity),
                    "price": str(order_data.price)
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("approved", False)
            return False
        except Exception:
            return False

async def call_wallet_service(user_id: int, action: str, amount: Decimal, order_id: str, token: str) -> bool:
    """Call wallet service to block/unblock funds"""
    async with httpx.AsyncClient() as client:
        try:
            if action == "block":
                response = await client.post(
                    f"{WALLET_SERVICE_URL}/block-funds/{user_id}",
                    json={
                        "amount": str(amount),
                        "reference_id": order_id
                    },
                    headers={"Authorization": f"Bearer {token}"}
                )
            elif action == "unblock":
                response = await client.post(
                    f"{WALLET_SERVICE_URL}/unblock-funds/{user_id}",
                    json={
                        "amount": str(amount),
                        "reference_id": order_id
                    },
                    headers={"Authorization": f"Bearer {token}"}
                )
            return response.status_code == 200
        except Exception:
            return False

async def call_matching_engine(order: Order, token: str) -> List[Execution]:
    """Send order to matching engine"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{MATCHING_ENGINE_URL}/order",
                json={
                    "id": order.id,
                    "user_id": order.user_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "order_type": order.order_type,
                    "quantity": str(order.quantity),
                    "price": str(order.price)
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                executions_data = response.json()
                executions = []
                for exec_data in executions_data:
                    execution = Execution(
                        id=exec_data["id"],
                        order_id=exec_data["order_id"],
                        symbol=exec_data["symbol"],
                        side=exec_data["side"],
                        quantity=Decimal(exec_data["quantity"]),
                        price=Decimal(exec_data["price"]),
                        buyer_id=exec_data["buyer_id"],
                        seller_id=exec_data["seller_id"],
                        executed_at=datetime.fromisoformat(exec_data["executed_at"])
                    )
                    executions.append(execution)
                return executions
            return []
        except Exception:
            return []

async def cancel_order_in_matching_engine(order_id: str, token: str) -> bool:
    """Cancel order in matching engine"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{MATCHING_ENGINE_URL}/cancel",
                json={"order_id": order_id},
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.status_code == 200
        except Exception:
            return False

@app.post("/order", response_model=Order)
async def place_order(
    order_data: OrderCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Place a new order"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    token = credentials.credentials
    
    # Generate order ID
    order_id = str(uuid.uuid4())
    
    # Check risk management
    risk_approved = await call_risk_manager(user_id, order_data, token)
    if not risk_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order rejected by risk management"
        )
    
    # Calculate required funds for buy orders
    if order_data.side == OrderSide.BUY:
        required_funds = order_data.quantity * order_data.price
        funds_blocked = await call_wallet_service(user_id, "block", required_funds, order_id, token)
        if not funds_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds"
            )
    
    # Create order
    order = Order(
        id=order_id,
        user_id=user_id,
        symbol=order_data.symbol,
        side=order_data.side,
        order_type=order_data.order_type,
        quantity=order_data.quantity,
        price=order_data.price,
        status=OrderStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Save to database
    db_order = OrderDB(
        id=order.id,
        user_id=order.user_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        price=order.price,
        status=order.status
    )
    
    db.add(db_order)
    await db.commit()
    
    # Send to matching engine
    try:
        executions = await call_matching_engine(order, token)
        
        # Process executions if any
        if executions:
            await process_executions(executions, db, token)
            
            # Update order status
            result = await db.execute(select(OrderDB).where(OrderDB.id == order_id))
            updated_order = result.scalar_one()
            order.status = updated_order.status
            order.filled_quantity = updated_order.filled_quantity
            
    except Exception as e:
        # If matching engine fails, unblock funds and mark order as rejected
        if order_data.side == OrderSide.BUY:
            await call_wallet_service(user_id, "unblock", required_funds, order_id, token)
        
        db_order.status = OrderStatus.REJECTED
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process order in matching engine"
        )
    
    return order

@app.delete("/order/{order_id}")
async def cancel_order(
    order_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an existing order"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    token = credentials.credentials
    
    # Get order from database
    result = await db.execute(
        select(OrderDB).where(
            and_(OrderDB.id == order_id, OrderDB.user_id == user_id)
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be cancelled"
        )
    
    # Cancel in matching engine
    cancelled = await cancel_order_in_matching_engine(order_id, token)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order in matching engine"
        )
    
    # Unblock funds if buy order
    if order.side == OrderSide.BUY:
        remaining_funds = (order.quantity - order.filled_quantity) * order.price
        await call_wallet_service(user_id, "unblock", remaining_funds, order_id, token)
    
    # Update order status
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now()
    await db.commit()
    
    return {"message": "Order cancelled successfully", "order_id": order_id}

@app.get("/orders", response_model=List[Order])
async def get_user_orders(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    symbol: Optional[str] = None,
    status: Optional[OrderStatus] = None
):
    """Get user's orders"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    query = select(OrderDB).where(OrderDB.user_id == user_id)
    
    if symbol:
        query = query.where(OrderDB.symbol == symbol)
    if status:
        query = query.where(OrderDB.status == status)
    
    query = query.order_by(OrderDB.created_at.desc())
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return [
        Order(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            filled_quantity=order.filled_quantity,
                status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at
        ) for order in orders
    ]

@app.get("/order/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get specific order details"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    result = await db.execute(
        select(OrderDB).where(
            and_(OrderDB.id == order_id, OrderDB.user_id == user_id)
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return Order(
        id=order.id,
        user_id=order.user_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        price=order.price,
        filled_quantity=order.filled_quantity,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at
    )

async def process_executions(executions: List[Execution], db: AsyncSession, token: str):
    """Process executions from matching engine"""
    for execution in executions:
        # Save execution to database
        db_execution = ExecutionDB(
            id=execution.id,
            order_id=execution.order_id,
            symbol=execution.symbol,
            side=execution.side,
            quantity=execution.quantity,
            price=execution.price,
            buyer_id=execution.buyer_id,
            seller_id=execution.seller_id,
            executed_at=execution.executed_at
        )
        db.add(db_execution)
        
        # Update order statuses for both orders
        order_ids = execution.order_id.split(",")
        for order_id in order_ids:
            result = await db.execute(select(OrderDB).where(OrderDB.id == order_id))
            order = result.scalar_one_or_none()
            if order:
                order.filled_quantity += execution.quantity
                
                if (order.quantity - order.filled_quantity) <= 0:
                    order.status = OrderStatus.FILLED
                    # Unblock any remaining funds for buy orders
                    if order.side == OrderSide.BUY and (order.quantity - order.filled_quantity) > 0:
                        remaining_funds = (order.quantity - order.filled_quantity) * order.price
                        await call_wallet_service(order.user_id, "unblock", remaining_funds, order_id, token)
                else:
                    order.status = OrderStatus.PARTIAL
                
                order.updated_at = datetime.now()
    
    await db.commit()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8426)