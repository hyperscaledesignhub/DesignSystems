import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, timedelta
import uvicorn
import redis.asyncio as redis

from shared.models.base import Order, OrderSide
from shared.utils.auth import verify_token
from shared.utils.database import get_redis_url
from shared.tracing import setup_tracing, instrument_fastapi, TracingMiddleware

tracer = setup_tracing("risk-manager")
app = FastAPI(title="Risk Manager Service", version="1.0.0")
instrument_fastapi(app)
app.add_middleware(TracingMiddleware, service_name="risk-manager")
security = HTTPBearer()

# Redis setup for real-time calculations
redis_client = None

class RiskCheck(BaseModel):
    user_id: int
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal

class RiskResult(BaseModel):
    approved: bool
    reason: str = None
    risk_score: float = 0.0

# Risk limits
MAX_POSITION_PER_SYMBOL = Decimal("1000")  # Max 1000 shares per symbol
MAX_DAILY_VOLUME = Decimal("50000")  # Max $50K per day per user
MAX_ORDER_VALUE = Decimal("10000")  # Max $10K per order

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(get_redis_url())
    return redis_client

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)

async def get_user_position(user_id: int, symbol: str) -> Decimal:
    """Get current position for user in symbol"""
    redis_conn = await get_redis()
    position_key = f"position:{user_id}:{symbol}"
    position = await redis_conn.get(position_key)
    return Decimal(position) if position else Decimal("0")

async def get_daily_volume(user_id: int) -> Decimal:
    """Get today's trading volume for user"""
    redis_conn = await get_redis()
    today = datetime.now().strftime("%Y-%m-%d")
    volume_key = f"daily_volume:{user_id}:{today}"
    volume = await redis_conn.get(volume_key)
    return Decimal(volume) if volume else Decimal("0")

async def update_user_position(user_id: int, symbol: str, quantity_change: Decimal):
    """Update user position in symbol"""
    redis_conn = await get_redis()
    position_key = f"position:{user_id}:{symbol}"
    await redis_conn.incrbyfloat(position_key, float(quantity_change))
    await redis_conn.expire(position_key, 86400)  # Expire after 24 hours

async def update_daily_volume(user_id: int, order_value: Decimal):
    """Update user's daily trading volume"""
    redis_conn = await get_redis()
    today = datetime.now().strftime("%Y-%m-%d")
    volume_key = f"daily_volume:{user_id}:{today}"
    await redis_conn.incrbyfloat(volume_key, float(order_value))
    await redis_conn.expire(volume_key, 86400)  # Expire after 24 hours

@app.post("/check-risk", response_model=RiskResult)
async def check_risk(
    risk_check: RiskCheck,
    user_data: dict = Depends(verify_user_token)
):
    """Perform risk checks on an order"""
    
    order_value = risk_check.quantity * risk_check.price
    
    # Check 1: Order value limit
    if order_value > MAX_ORDER_VALUE:
        return RiskResult(
            approved=False,
            reason=f"Order value ${order_value} exceeds maximum ${MAX_ORDER_VALUE}",
            risk_score=1.0
        )
    
    # Check 2: Position limits
    current_position = await get_user_position(risk_check.user_id, risk_check.symbol)
    
    if risk_check.side == OrderSide.BUY:
        new_position = current_position + risk_check.quantity
    else:
        new_position = current_position - risk_check.quantity
    
    if abs(new_position) > MAX_POSITION_PER_SYMBOL:
        return RiskResult(
            approved=False,
            reason=f"Position limit exceeded. Current: {current_position}, Max: {MAX_POSITION_PER_SYMBOL}",
            risk_score=0.9
        )
    
    # Check 3: Daily volume limit
    daily_volume = await get_daily_volume(risk_check.user_id)
    if daily_volume + order_value > MAX_DAILY_VOLUME:
        return RiskResult(
            approved=False,
            reason=f"Daily volume limit exceeded. Current: ${daily_volume}, Max: ${MAX_DAILY_VOLUME}",
            risk_score=0.8
        )
    
    # Calculate risk score (0-1, where 1 is highest risk)
    risk_score = 0.0
    risk_score += float(order_value / MAX_ORDER_VALUE) * 0.3
    risk_score += float(abs(new_position) / MAX_POSITION_PER_SYMBOL) * 0.4
    risk_score += float((daily_volume + order_value) / MAX_DAILY_VOLUME) * 0.3
    
    return RiskResult(
        approved=True,
        reason="Risk checks passed",
        risk_score=min(risk_score, 1.0)
    )

@app.post("/update-position")
async def update_position(
    user_id: int,
    symbol: str,
    quantity_change: Decimal,
    order_value: Decimal,
    user_data: dict = Depends(verify_user_token)
):
    """Update user position and daily volume after trade execution"""
    
    await update_user_position(user_id, symbol, quantity_change)
    await update_daily_volume(user_id, order_value)
    
    return {"message": "Position updated successfully"}

@app.get("/position/{user_id}/{symbol}")
async def get_position(
    user_id: int,
    symbol: str,
    user_data: dict = Depends(verify_user_token)
):
    """Get current position for user in symbol"""
    
    position = await get_user_position(user_id, symbol)
    return {"user_id": user_id, "symbol": symbol, "position": position}

@app.get("/daily-volume/{user_id}")
async def get_user_daily_volume(
    user_id: int,
    user_data: dict = Depends(verify_user_token)
):
    """Get today's trading volume for user"""
    
    volume = await get_daily_volume(user_id)
    return {"user_id": user_id, "daily_volume": volume}

@app.get("/limits")
async def get_risk_limits():
    """Get current risk limits"""
    return {
        "max_position_per_symbol": MAX_POSITION_PER_SYMBOL,
        "max_daily_volume": MAX_DAILY_VOLUME,
        "max_order_value": MAX_ORDER_VALUE
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8539)