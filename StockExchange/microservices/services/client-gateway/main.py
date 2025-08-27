import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from decimal import Decimal
import uvicorn
import httpx
import time
import json
import redis.asyncio as redis
from datetime import datetime, timedelta
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from shared.models.base import Order, OrderSide, OrderType, User
from shared.utils.auth import verify_token
from shared.utils.database import get_redis_url
from shared.tracing import setup_tracing, instrument_fastapi, TracingMiddleware

# Setup tracing
tracer = setup_tracing("client-gateway")

app = FastAPI(title="Client Gateway", version="1.0.0")
security = HTTPBearer()

# Add tracing instrumentation
instrument_fastapi(app)
app.add_middleware(TracingMiddleware, service_name="client-gateway")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
USER_SERVICE_URL = "http://user-service:8975"
ORDER_MANAGER_URL = "http://order-manager:8426"
WALLET_SERVICE_URL = "http://wallet-service:8651"
MARKET_DATA_URL = "http://market-data-service:8864"
REPORTING_SERVICE_URL = "http://reporting-service:9127"

# Redis for rate limiting
redis_client = None

# Rate limiting settings
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class OrderCreate(BaseModel):
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.LIMIT
    quantity: Decimal
    price: Decimal

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(get_redis_url())
    return redis_client

async def check_rate_limit(request: Request) -> bool:
    """Check if request is within rate limits"""
    client_ip = request.client.host
    redis_conn = await get_redis()
    
    key = f"rate_limit:{client_ip}"
    current_time = int(time.time())
    window_start = current_time - RATE_LIMIT_WINDOW
    
    # Clean up old entries
    await redis_conn.zremrangebyscore(key, 0, window_start)
    
    # Count current requests
    request_count = await redis_conn.zcard(key)
    
    if request_count >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    await redis_conn.zadd(key, {str(current_time): current_time})
    await redis_conn.expire(key, RATE_LIMIT_WINDOW)
    
    return True

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)

async def forward_request_with_auth(url: str, method: str, data: dict = None, token: str = None):
    """Forward request to another service with authentication and tracing propagation"""
    from opentelemetry import propagate
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    # Inject tracing context into headers for distributed tracing
    propagate.inject(headers)
    
    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            response = await client.get(url, headers=headers)
        elif method.upper() == "POST":
            response = await client.post(url, json=data, headers=headers)
        elif method.upper() == "DELETE":
            response = await client.delete(url, headers=headers)
        else:
            raise HTTPException(status_code=405, detail="Method not allowed")
        
        return response

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not await check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    response = await call_next(request)
    return response

# Authentication endpoints
@app.post("/auth/register", response_model=User)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    response = await forward_request_with_auth(
        f"{USER_SERVICE_URL}/register",
        "POST",
        user_data.dict()
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json().get("detail", "Registration failed")
        )
    
    # Create wallet for new user
    user_info = response.json()
    try:
        wallet_response = await forward_request_with_auth(
            f"{WALLET_SERVICE_URL}/create",
            "POST",
            {"user_id": user_info["id"], "initial_balance": "10000"},
            # We need a token for wallet creation, but user just registered
            # In a real system, this would be handled differently
        )
    except:
        pass  # Wallet creation can be done later
    
    return response.json()

@app.post("/auth/login", response_model=Token)
async def login_user(user_data: UserLogin):
    """Login user"""
    response = await forward_request_with_auth(
        f"{USER_SERVICE_URL}/login",
        "POST",
        user_data.dict()
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json().get("detail", "Login failed")
        )
    
    return response.json()

@app.get("/auth/me", response_model=User)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user info"""
    response = await forward_request_with_auth(
        f"{USER_SERVICE_URL}/me",
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to get user info"
        )
    
    return response.json()

# Order management endpoints
@app.post("/v1/order", response_model=Order)
async def place_order(
    order_data: OrderCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Place a new order"""
    
    # Create tracing span
    with tracer.start_as_current_span(
        "place_order",
        attributes={
            "order.symbol": order_data.symbol,
            "order.side": order_data.side,
            "order.quantity": str(order_data.quantity),
            "order.price": str(order_data.price)
        }
    ) as span:
        # Validate order data
        if order_data.quantity <= 0:
            span.set_status(Status(StatusCode.ERROR, "Invalid quantity"))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order quantity must be positive"
            )
        
        if order_data.price <= 0:
            span.set_status(Status(StatusCode.ERROR, "Invalid price"))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order price must be positive"
            )
        
        # Forward to order manager
        response = await forward_request_with_auth(
            f"{ORDER_MANAGER_URL}/order",
            "POST",
            {
                "symbol": order_data.symbol,
                "side": order_data.side,
                "order_type": order_data.order_type,
                "quantity": str(order_data.quantity),
                "price": str(order_data.price)
            },
            credentials.credentials
        )
        
        if response.status_code != 200:
            span.set_status(Status(StatusCode.ERROR, f"Order failed: {response.status_code}"))
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", "Failed to place order")
            )
        
        result = response.json()
        span.set_attribute("order.id", result.get("id", "unknown"))
        span.set_status(Status(StatusCode.OK))
        return result

@app.delete("/v1/order/{order_id}")
async def cancel_order(
    order_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Cancel an existing order"""
    
    response = await forward_request_with_auth(
        f"{ORDER_MANAGER_URL}/order/{order_id}",
        "DELETE",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json().get("detail", "Failed to cancel order")
        )
    
    return response.json()

@app.get("/v1/orders", response_model=List[Order])
async def get_orders(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    symbol: Optional[str] = None,
    status: Optional[str] = None
):
    """Get user's orders"""
    
    url = f"{ORDER_MANAGER_URL}/orders"
    params = []
    if symbol:
        params.append(f"symbol={symbol}")
    if status:
        params.append(f"status={status}")
    
    if params:
        url += "?" + "&".join(params)
    
    response = await forward_request_with_auth(
        url,
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to get orders"
        )
    
    return response.json()

@app.get("/v1/order/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get specific order details"""
    
    response = await forward_request_with_auth(
        f"{ORDER_MANAGER_URL}/order/{order_id}",
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Order not found"
        )
    
    return response.json()

# Market data endpoints
@app.get("/marketdata/orderBook/L2")
async def get_order_book(symbol: str, depth: int = 5):
    """Get L2 order book data"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MARKET_DATA_URL}/orderbook/{symbol}?depth={depth}")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get order book"
            )
        
        return response.json()

@app.get("/marketdata/candles")
async def get_candlestick_data(
    symbol: str,
    resolution: str = "1m",
    startTime: Optional[int] = None,
    endTime: Optional[int] = None
):
    """Get candlestick chart data"""
    
    params = [f"symbol={symbol}", f"interval={resolution}"]
    if startTime:
        params.append(f"start_time={startTime}")
    if endTime:
        params.append(f"end_time={endTime}")
    
    url = f"{MARKET_DATA_URL}/candles?" + "&".join(params)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to get candlestick data"
            )
        
        return response.json()

# Wallet endpoints
@app.get("/wallet/balance")
async def get_wallet_balance(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's wallet balance"""
    
    # First get user info to get user_id
    user_response = await forward_request_with_auth(
        f"{USER_SERVICE_URL}/me",
        "GET",
        token=credentials.credentials
    )
    
    if user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_data = user_response.json()
    user_id = user_data["id"]
    
    # Get wallet balance
    response = await forward_request_with_auth(
        f"{WALLET_SERVICE_URL}/balance/{user_id}",
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to get wallet balance"
        )
    
    return response.json()

@app.post("/wallet/create")
async def create_wallet(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a wallet for the current user"""
    
    # First get user info to get user_id
    user_response = await forward_request_with_auth(
        f"{USER_SERVICE_URL}/me",
        "GET",
        token=credentials.credentials
    )
    
    if user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_data = user_response.json()
    user_id = user_data["id"]
    
    # Create wallet with initial balance
    response = await forward_request_with_auth(
        f"{WALLET_SERVICE_URL}/create",
        "POST",
        {
            "user_id": user_id,
            "initial_balance": 100000.0  # $100,000 demo balance
        },
        credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to create wallet"
        )
    
    return response.json()

class AddFundsRequest(BaseModel):
    amount: float

class CreateWalletRequest(BaseModel):
    initial_balance: float = 10000.0

@app.post("/wallet/create")
async def create_wallet(
    request: CreateWalletRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a wallet for the authenticated user"""
    
    # Get user info
    user_response = await forward_request_with_auth(
        f"{USER_SERVICE_URL}/me",
        "GET",
        token=credentials.credentials
    )
    
    if user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_data = user_response.json()
    user_id = user_data["id"]
    
    # Create wallet
    response = await forward_request_with_auth(
        f"{WALLET_SERVICE_URL}/create",
        "POST",
        {"user_id": user_id, "initial_balance": str(request.initial_balance)},
        credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json().get("detail", "Failed to create wallet")
        )
    
    return response.json()

@app.post("/wallet/add-funds")
async def add_funds(
    request: AddFundsRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add funds to user's wallet (demo/testing only)"""
    
    # First get user info to get user_id
    user_response = await forward_request_with_auth(
        f"{USER_SERVICE_URL}/me",
        "GET",
        token=credentials.credentials
    )
    
    if user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_data = user_response.json()
    user_id = user_data["id"]
    
    # First check if wallet exists
    wallet_check = await forward_request_with_auth(
        f"{WALLET_SERVICE_URL}/balance/{user_id}",
        "GET",
        token=credentials.credentials
    )
    
    # If wallet doesn't exist, create it first
    if wallet_check.status_code == 404:
        create_response = await forward_request_with_auth(
            f"{WALLET_SERVICE_URL}/create",
            "POST",
            {"user_id": user_id, "initial_balance": "0"},
            credentials.credentials
        )
        
        if create_response.status_code != 200:
            raise HTTPException(
                status_code=create_response.status_code,
                detail="Failed to create wallet"
            )
    
    # Now add funds to wallet
    response = await forward_request_with_auth(
        f"{WALLET_SERVICE_URL}/update-balance/{user_id}",
        "POST",
        {
            "amount": request.amount,
            "transaction_type": "DEPOSIT",
            "description": f"Demo funds added: ${request.amount}"
        },
        credentials.credentials
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to add funds"
        )
    
    return response.json()

# Reporting service endpoints
@app.get("/reports/trades")
async def get_user_trades(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = 100
):
    """Get user's trade history"""
    
    response = await forward_request_with_auth(
        f"{REPORTING_SERVICE_URL}/trades?limit={limit}",
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        return {"trades": []}
    
    return response.json()

@app.get("/reports/positions")
async def get_user_positions(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's positions"""
    
    response = await forward_request_with_auth(
        f"{REPORTING_SERVICE_URL}/positions",
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        return {"positions": []}
    
    return response.json()

@app.get("/reports/statistics")
async def get_system_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get system statistics"""
    
    response = await forward_request_with_auth(
        f"{REPORTING_SERVICE_URL}/statistics",
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        return {
            "totalVolume": 0,
            "totalOrders": 0,
            "activeUsers": 0,
            "totalTrades": 0,
            "avgSpread": 0,
            "successRate": 98.5
        }
    
    return response.json()

@app.get("/reports/pnl")
async def get_user_pnl(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's P&L report"""
    
    response = await forward_request_with_auth(
        f"{REPORTING_SERVICE_URL}/pnl",
        "GET",
        token=credentials.credentials
    )
    
    if response.status_code != 200:
        return {"daily_pnl": [], "total_pnl": 0}
    
    return response.json()

@app.get("/marketdata/symbols")
async def get_market_symbols():
    """Get available market symbols"""
    
    # Return mock data for demonstration
    return [
        {"symbol": "AAPL", "price": 150.00, "change": 2.5, "volume": 1000000},
        {"symbol": "GOOGL", "price": 2800.00, "change": -1.2, "volume": 500000},
        {"symbol": "MSFT", "price": 380.00, "change": 1.8, "volume": 750000},
        {"symbol": "AMZN", "price": 170.00, "change": -0.5, "volume": 600000},
        {"symbol": "TSLA", "price": 250.00, "change": 3.2, "volume": 1200000}
    ]

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data and order updates"""
    await websocket.accept()
    
    try:
        while True:
            # Keep connection alive and handle messages
            data = await websocket.receive_text()
            
            # Echo back with timestamp for demo purposes
            await websocket.send_text(json.dumps({
                "type": "ping",
                "timestamp": datetime.now().isoformat(),
                "message": "Connection active"
            }))
            
            # In a real implementation, this would subscribe to Redis channels
            # and forward market data, order updates, etc.
            
    except WebSocketDisconnect:
        pass

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "client-gateway"}

@app.get("/")
async def root():
    return {
        "service": "Stock Exchange Client Gateway",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth/*",
            "orders": "/v1/order*",
            "market_data": "/marketdata/*",
            "wallet": "/wallet/*"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8347)