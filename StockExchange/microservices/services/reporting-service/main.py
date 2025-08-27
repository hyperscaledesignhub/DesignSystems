import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import uvicorn
import asyncio
import json
import redis.asyncio as redis
import csv
import io

from shared.models.base import Order, Execution, OrderSide, OrderStatus
from shared.utils.database import DatabaseManager, get_database_url, get_redis_url
from shared.utils.auth import verify_token
from models import ReportDB, TradeReportDB

app = FastAPI(title="Reporting Service", version="1.0.0")
security = HTTPBearer()

# Database setup
db_manager = DatabaseManager(get_database_url("reporting"))

# Redis for listening to executions
redis_client = None

class TradeReport(BaseModel):
    id: Optional[int] = None
    user_id: int
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    total_value: Decimal
    executed_at: datetime

class DailyTradingSummary(BaseModel):
    user_id: int
    date: str
    total_trades: int
    total_volume: Decimal
    total_value: Decimal
    symbols_traded: List[str]

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

async def process_execution_for_reporting(execution_data: dict):
    """Process execution and store in reporting database"""
    try:
        async for session in db_manager.get_session():
            # Extract order IDs (buyer and seller)
            order_ids = execution_data["order_id"].split(",")
            buyer_id = execution_data["buyer_id"]
            seller_id = execution_data["seller_id"]
            
            # Create trade reports for both buyer and seller
            trades = [
                TradeReportDB(
                    user_id=buyer_id,
                    order_id=order_ids[0] if len(order_ids) > 0 else execution_data["order_id"],
                    execution_id=execution_data["id"],
                    symbol=execution_data["symbol"],
                    side=OrderSide.BUY,
                    quantity=Decimal(execution_data["quantity"]),
                    price=Decimal(execution_data["price"]),
                    total_value=Decimal(execution_data["quantity"]) * Decimal(execution_data["price"]),
                    executed_at=datetime.fromisoformat(execution_data["executed_at"])
                ),
                TradeReportDB(
                    user_id=seller_id,
                    order_id=order_ids[1] if len(order_ids) > 1 else execution_data["order_id"],
                    execution_id=execution_data["id"],
                    symbol=execution_data["symbol"],
                    side=OrderSide.SELL,
                    quantity=Decimal(execution_data["quantity"]),
                    price=Decimal(execution_data["price"]),
                    total_value=Decimal(execution_data["quantity"]) * Decimal(execution_data["price"]),
                    executed_at=datetime.fromisoformat(execution_data["executed_at"])
                )
            ]
            
            for trade in trades:
                session.add(trade)
            
            await session.commit()
            break  # Exit the async generator
            
    except Exception as e:
        print(f"Error processing execution for reporting: {e}")

async def subscribe_to_executions():
    """Subscribe to execution stream for reporting"""
    redis_conn = await get_redis()
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe("executions")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                execution_data = json.loads(message["data"])
                await process_execution_for_reporting(execution_data)
            except Exception as e:
                print(f"Error processing execution for reporting: {e}")

@app.get("/trades", response_model=List[TradeReport])
async def get_user_trades(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get user's trade history"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    query = select(TradeReportDB).where(TradeReportDB.user_id == user_id)
    
    if symbol:
        query = query.where(TradeReportDB.symbol == symbol)
    
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.where(TradeReportDB.executed_at >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.where(TradeReportDB.executed_at <= end_dt)
    
    query = query.order_by(TradeReportDB.executed_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    return [
        TradeReport(
            id=trade.id,
            user_id=trade.user_id,
            symbol=trade.symbol,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            total_value=trade.total_value,
            executed_at=trade.executed_at
        ) for trade in trades
    ]

@app.get("/daily-summary", response_model=List[DailyTradingSummary])
async def get_daily_trading_summary(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get user's daily trading summary"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Query for daily aggregated data
    query = select(
        func.date(TradeReportDB.executed_at).label('trade_date'),
        func.count(TradeReportDB.id).label('total_trades'),
        func.sum(TradeReportDB.quantity).label('total_volume'),
        func.sum(TradeReportDB.total_value).label('total_value'),
        func.array_agg(func.distinct(TradeReportDB.symbol)).label('symbols')
    ).where(
        and_(
            TradeReportDB.user_id == user_id,
            TradeReportDB.executed_at >= start_date
        )
    ).group_by(
        func.date(TradeReportDB.executed_at)
    ).order_by(
        func.date(TradeReportDB.executed_at).desc()
    )
    
    result = await db.execute(query)
    daily_data = result.all()
    
    summaries = []
    for row in daily_data:
        summaries.append(DailyTradingSummary(
            user_id=user_id,
            date=row.trade_date.isoformat(),
            total_trades=row.total_trades,
            total_volume=row.total_volume or Decimal("0"),
            total_value=row.total_value or Decimal("0"),
            symbols_traded=row.symbols or []
        ))
    
    return summaries

@app.get("/portfolio-summary")
async def get_portfolio_summary(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get user's portfolio summary (positions by symbol)"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    # Calculate net positions by symbol
    query = select(
        TradeReportDB.symbol,
        func.sum(
            func.case(
                (TradeReportDB.side == OrderSide.BUY, TradeReportDB.quantity),
                else_=-TradeReportDB.quantity
            )
        ).label('net_quantity'),
        func.sum(TradeReportDB.total_value).label('total_traded_value'),
        func.count(TradeReportDB.id).label('total_trades')
    ).where(
        TradeReportDB.user_id == user_id
    ).group_by(
        TradeReportDB.symbol
    ).having(
        func.sum(
            func.case(
                (TradeReportDB.side == OrderSide.BUY, TradeReportDB.quantity),
                else_=-TradeReportDB.quantity
            )
        ) != 0
    )
    
    result = await db.execute(query)
    positions = result.all()
    
    portfolio = []
    for position in positions:
        portfolio.append({
            "symbol": position.symbol,
            "net_quantity": position.net_quantity,
            "total_traded_value": position.total_traded_value,
            "total_trades": position.total_trades
        })
    
    return {"positions": portfolio}

@app.get("/export/trades")
async def export_trades_csv(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Export user's trades to CSV"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    query = select(TradeReportDB).where(TradeReportDB.user_id == user_id)
    
    if symbol:
        query = query.where(TradeReportDB.symbol == symbol)
    
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.where(TradeReportDB.executed_at >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.where(TradeReportDB.executed_at <= end_dt)
    
    query = query.order_by(TradeReportDB.executed_at.desc())
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Execution ID', 'Order ID', 'Symbol', 'Side', 'Quantity', 
        'Price', 'Total Value', 'Executed At'
    ])
    
    # Write data
    for trade in trades:
        writer.writerow([
            trade.execution_id,
            trade.order_id,
            trade.symbol,
            trade.side,
            str(trade.quantity),
            str(trade.price),
            str(trade.total_value),
            trade.executed_at.isoformat()
        ])
    
    output.seek(0)
    
    # Create streaming response
    def iter_csv():
        yield output.getvalue()
    
    headers = {
        'Content-Disposition': f'attachment; filename="trades_{user_id}_{datetime.now().strftime("%Y%m%d")}.csv"'
    }
    
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers=headers
    )

@app.get("/trading-statistics")
async def get_trading_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get user's trading statistics"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Overall statistics
    overall_query = select(
        func.count(TradeReportDB.id).label('total_trades'),
        func.sum(TradeReportDB.quantity).label('total_volume'),
        func.sum(TradeReportDB.total_value).label('total_value'),
        func.count(func.distinct(TradeReportDB.symbol)).label('unique_symbols'),
        func.avg(TradeReportDB.price).label('avg_price')
    ).where(
        and_(
            TradeReportDB.user_id == user_id,
            TradeReportDB.executed_at >= start_date
        )
    )
    
    overall_result = await db.execute(overall_query)
    overall_stats = overall_result.first()
    
    # Buy vs Sell statistics
    side_query = select(
        TradeReportDB.side,
        func.count(TradeReportDB.id).label('count'),
        func.sum(TradeReportDB.quantity).label('volume'),
        func.sum(TradeReportDB.total_value).label('value')
    ).where(
        and_(
            TradeReportDB.user_id == user_id,
            TradeReportDB.executed_at >= start_date
        )
    ).group_by(TradeReportDB.side)
    
    side_result = await db.execute(side_query)
    side_stats = {row.side: {
        'count': row.count,
        'volume': row.volume,
        'value': row.value
    } for row in side_result}
    
    return {
        "period_days": days,
        "overall": {
            "total_trades": overall_stats.total_trades or 0,
            "total_volume": overall_stats.total_volume or Decimal("0"),
            "total_value": overall_stats.total_value or Decimal("0"),
            "unique_symbols": overall_stats.unique_symbols or 0,
            "avg_price": overall_stats.avg_price or Decimal("0")
        },
        "by_side": side_stats
    }

@app.get("/statistics")
async def get_system_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide statistics for dashboard"""
    
    user_data = verify_token(credentials.credentials)
    
    # Get overall system metrics
    total_volume_query = select(func.sum(TradeReportDB.total_value)).where(
        TradeReportDB.executed_at >= datetime.now() - timedelta(days=1)
    )
    total_orders_query = select(func.count(TradeReportDB.id)).where(
        TradeReportDB.executed_at >= datetime.now() - timedelta(days=1)
    )
    active_users_query = select(func.count(func.distinct(TradeReportDB.user_id))).where(
        TradeReportDB.executed_at >= datetime.now() - timedelta(days=1)
    )
    
    volume_result = await db.execute(total_volume_query)
    orders_result = await db.execute(total_orders_query)
    users_result = await db.execute(active_users_query)
    
    return {
        "totalVolume": float(volume_result.scalar() or 0),
        "totalOrders": orders_result.scalar() or 0,
        "activeUsers": users_result.scalar() or 0,
        "totalTrades": orders_result.scalar() or 0,
        "avgSpread": 0.05,
        "successRate": 98.5
    }

@app.get("/positions")
async def get_user_positions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current positions with P&L calculations"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    # Calculate positions with average price
    positions_query = select(
        TradeReportDB.symbol,
        func.sum(
            func.case(
                (TradeReportDB.side == OrderSide.BUY, TradeReportDB.quantity),
                else_=-TradeReportDB.quantity
            )
        ).label('quantity'),
        func.sum(
            func.case(
                (TradeReportDB.side == OrderSide.BUY, TradeReportDB.total_value),
                else_=-TradeReportDB.total_value
            )
        ).label('net_cost')
    ).where(
        TradeReportDB.user_id == user_id
    ).group_by(
        TradeReportDB.symbol
    ).having(
        func.sum(
            func.case(
                (TradeReportDB.side == OrderSide.BUY, TradeReportDB.quantity),
                else_=-TradeReportDB.quantity
            )
        ) != 0
    )
    
    result = await db.execute(positions_query)
    positions = result.all()
    
    # Mock current prices (in real system, get from market data service)
    current_prices = {
        'AAPL': 152.50,
        'GOOGL': 2850.00,
        'MSFT': 385.00,
        'AMZN': 175.00,
        'TSLA': 255.00
    }
    
    positions_list = []
    for position in positions:
        if position.quantity > 0:  # Only positive positions
            average_price = float(position.net_cost) / float(position.quantity)
            current_price = current_prices.get(position.symbol, average_price)
            unrealized_pnl = float(position.quantity) * (current_price - average_price)
            pnl_percentage = (unrealized_pnl / (float(position.quantity) * average_price)) * 100 if average_price > 0 else 0
            
            positions_list.append({
                "symbol": position.symbol,
                "quantity": int(position.quantity),
                "average_price": round(average_price, 2),
                "current_price": current_price,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "pnl_percentage": round(pnl_percentage, 2)
            })
    
    return {"positions": positions_list}

@app.get("/pnl")
async def get_user_pnl(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get user's P&L report"""
    
    user_data = verify_token(credentials.credentials)
    user_id = user_data["user_id"]
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Daily P&L calculation
    daily_pnl_query = select(
        func.date(TradeReportDB.executed_at).label('date'),
        func.sum(
            func.case(
                (TradeReportDB.side == OrderSide.BUY, -TradeReportDB.total_value),
                else_=TradeReportDB.total_value
            )
        ).label('daily_pnl')
    ).where(
        and_(
            TradeReportDB.user_id == user_id,
            TradeReportDB.executed_at >= start_date
        )
    ).group_by(
        func.date(TradeReportDB.executed_at)
    ).order_by(
        func.date(TradeReportDB.executed_at)
    )
    
    result = await db.execute(daily_pnl_query)
    daily_data = result.all()
    
    return {
        "period_days": days,
        "daily_pnl": [
            {
                "date": row.date.isoformat(),
                "pnl": float(row.daily_pnl or 0)
            } for row in daily_data
        ],
        "total_pnl": sum(float(row.daily_pnl or 0) for row in daily_data)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    # Start Redis subscriber for executions
    asyncio.create_task(subscribe_to_executions())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9127)