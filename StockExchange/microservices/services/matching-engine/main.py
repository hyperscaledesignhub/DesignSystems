import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict
from decimal import Decimal
import asyncio
import uvicorn
import uuid
from datetime import datetime
import redis.asyncio as redis
import json

from shared.models.base import Order, OrderSide, OrderStatus, OrderType, Execution, OrderBook as OrderBookModel
from shared.utils.auth import verify_token
from shared.utils.database import get_redis_url
from orderbook import OrderBook
from shared.tracing import setup_tracing, instrument_fastapi, TracingMiddleware

tracer = setup_tracing("matching-engine")
app = FastAPI(title="Matching Engine", version="1.0.0")
instrument_fastapi(app)
app.add_middleware(TracingMiddleware, service_name="matching-engine")
security = HTTPBearer()

# In-memory order books for each symbol
order_books: Dict[str, OrderBook] = {}

# Supported symbols
SUPPORTED_SYMBOLS = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA", "NFLX", "AMD", "ORCL"]

# Redis for pub/sub
redis_client = None

class OrderRequest(BaseModel):
    id: str
    user_id: int
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.LIMIT
    quantity: Decimal
    price: Decimal

class CancelRequest(BaseModel):
    order_id: str

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(get_redis_url())
    return redis_client

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)

async def publish_execution(execution: Execution):
    """Publish execution to Redis for other services"""
    redis_conn = await get_redis()
    execution_data = {
        "id": execution.id,
        "order_id": execution.order_id,
        "symbol": execution.symbol,
        "side": execution.side,
        "quantity": str(execution.quantity),
        "price": str(execution.price),
        "buyer_id": execution.buyer_id,
        "seller_id": execution.seller_id,
        "executed_at": execution.executed_at.isoformat()
    }
    await redis_conn.publish("executions", json.dumps(execution_data))

async def publish_order_book_update(symbol: str, order_book_data: Dict):
    """Publish order book update to Redis"""
    redis_conn = await get_redis()
    await redis_conn.publish(f"orderbook:{symbol}", json.dumps(order_book_data, default=str))

def get_or_create_order_book(symbol: str) -> OrderBook:
    """Get or create order book for symbol"""
    if symbol not in order_books:
        if symbol not in SUPPORTED_SYMBOLS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol {symbol} not supported"
            )
        order_books[symbol] = OrderBook(symbol)
    return order_books[symbol]

@app.post("/order", response_model=List[Execution])
async def place_order(
    order_request: OrderRequest,
    user_data: dict = Depends(verify_user_token)
):
    """Place a new order in the matching engine"""
    
    # Validate order
    if order_request.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order quantity must be positive"
        )
    
    if order_request.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order price must be positive"
        )
    
    # Create order
    order = Order(
        id=order_request.id,
        user_id=order_request.user_id,
        symbol=order_request.symbol,
        side=order_request.side,
        order_type=order_request.order_type,
        quantity=order_request.quantity,
        price=order_request.price,
        remaining_quantity=order_request.quantity,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Get order book and process order
    order_book = get_or_create_order_book(order_request.symbol)
    executions = order_book.add_order(order)
    
    # Publish executions
    for execution in executions:
        await publish_execution(execution)
    
    # Publish order book update
    order_book_snapshot = order_book.get_order_book_snapshot()
    await publish_order_book_update(order_request.symbol, order_book_snapshot)
    
    return executions

@app.post("/cancel")
async def cancel_order(
    cancel_request: CancelRequest,
    user_data: dict = Depends(verify_user_token)
):
    """Cancel an existing order"""
    
    cancelled = False
    
    # Try to cancel from all order books
    for symbol, order_book in order_books.items():
        if cancel_request.order_id in order_book.orders:
            cancelled = order_book.cancel_order(cancel_request.order_id)
            if cancelled:
                # Publish order book update
                order_book_snapshot = order_book.get_order_book_snapshot()
                await publish_order_book_update(symbol, order_book_snapshot)
                break
    
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or already filled/cancelled"
        )
    
    return {"message": "Order cancelled successfully", "order_id": cancel_request.order_id}

@app.get("/orderbook/{symbol}", response_model=OrderBookModel)
async def get_order_book(symbol: str, depth: int = 5):
    """Get order book for a symbol"""
    
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol {symbol} not supported"
        )
    
    if symbol not in order_books:
        # Return empty order book
        return OrderBookModel(
            symbol=symbol,
            bids=[],
            asks=[],
            timestamp=datetime.now()
        )
    
    order_book = order_books[symbol]
    snapshot = order_book.get_order_book_snapshot(depth)
    
    return OrderBookModel(
        symbol=snapshot["symbol"],
        bids=snapshot["bids"],
        asks=snapshot["asks"],
        timestamp=snapshot["timestamp"]
    )

@app.get("/order/{order_id}")
async def get_order(order_id: str):
    """Get order details"""
    
    for symbol, order_book in order_books.items():
        if order_id in order_book.orders:
            order = order_book.orders[order_id]
            return {
                "id": order.id,
                "user_id": order.user_id,
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "quantity": order.quantity,
                "price": order.price,
                "filled_quantity": order.filled_quantity,
                "remaining_quantity": order.remaining_quantity,
                "status": order.status,
                "created_at": order.created_at,
                "updated_at": order.updated_at
            }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Order not found"
    )

@app.get("/symbols")
async def get_supported_symbols():
    """Get list of supported symbols"""
    return {"symbols": SUPPORTED_SYMBOLS}

@app.get("/best-bid-ask/{symbol}")
async def get_best_bid_ask(symbol: str):
    """Get best bid and ask for a symbol"""
    
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol {symbol} not supported"
        )
    
    if symbol not in order_books:
        return {"symbol": symbol, "best_bid": None, "best_ask": None}
    
    order_book = order_books[symbol]
    best_bid = order_book.get_best_bid()
    best_ask = order_book.get_best_ask()
    
    return {
        "symbol": symbol,
        "best_bid": {"price": best_bid[0], "quantity": best_bid[1]} if best_bid else None,
        "best_ask": {"price": best_ask[0], "quantity": best_ask[1]} if best_ask else None
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "order_books": list(order_books.keys())}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8792)