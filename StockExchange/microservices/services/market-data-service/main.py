import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import uvicorn
import asyncio
import json
import redis.asyncio as redis
from collections import defaultdict, deque

from shared.models.base import OrderBook, Candlestick
from shared.utils.database import get_redis_url

app = FastAPI(title="Market Data Service", version="1.0.0")

# Redis for subscribing to market data
redis_client = None

# WebSocket connections
websocket_connections: Dict[str, List[WebSocket]] = defaultdict(list)

# In-memory storage for market data
order_books: Dict[str, OrderBook] = {}
candlestick_data: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))

# Candlestick intervals
INTERVALS = ["1m", "1h", "1d"]
MAX_CANDLES_IN_MEMORY = 1000

class CandlestickBuilder:
    def __init__(self):
        self.current_candles: Dict[str, Dict[str, Candlestick]] = defaultdict(dict)
    
    def add_execution(self, symbol: str, price: Decimal, quantity: Decimal, timestamp: datetime):
        """Add execution to candlestick data"""
        for interval in INTERVALS:
            candle_time = self._get_candle_time(timestamp, interval)
            key = f"{symbol}_{interval}"
            
            if key not in self.current_candles or self.current_candles[key] is None:
                # Create new candle
                self.current_candles[key] = Candlestick(
                    symbol=symbol,
                    open_price=price,
                    high_price=price,
                    low_price=price,
                    close_price=price,
                    volume=quantity,
                    timestamp=candle_time,
                    interval=interval
                )
            else:
                candle = self.current_candles[key]
                if candle.timestamp == candle_time:
                    # Update existing candle
                    candle.high_price = max(candle.high_price, price)
                    candle.low_price = min(candle.low_price, price)
                    candle.close_price = price
                    candle.volume += quantity
                else:
                    # Store completed candle and create new one
                    candlestick_data[symbol][interval].append(candle)
                    if len(candlestick_data[symbol][interval]) > MAX_CANDLES_IN_MEMORY:
                        candlestick_data[symbol][interval].popleft()
                    
                    # Create new candle
                    self.current_candles[key] = Candlestick(
                        symbol=symbol,
                        open_price=price,
                        high_price=price,
                        low_price=price,
                        close_price=price,
                        volume=quantity,
                        timestamp=candle_time,
                        interval=interval
                    )
    
    def _get_candle_time(self, timestamp: datetime, interval: str) -> datetime:
        """Get the start time of the candle for the given timestamp and interval"""
        if interval == "1m":
            return timestamp.replace(second=0, microsecond=0)
        elif interval == "1h":
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif interval == "1d":
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            return timestamp

candlestick_builder = CandlestickBuilder()

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(get_redis_url())
    return redis_client

async def subscribe_to_executions():
    """Subscribe to execution stream from matching engine"""
    redis_conn = await get_redis()
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe("executions")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                execution_data = json.loads(message["data"])
                
                # Update candlestick data
                symbol = execution_data["symbol"]
                price = Decimal(execution_data["price"])
                quantity = Decimal(execution_data["quantity"])
                executed_at = datetime.fromisoformat(execution_data["executed_at"])
                
                candlestick_builder.add_execution(symbol, price, quantity, executed_at)
                
                # Broadcast to WebSocket clients
                await broadcast_execution(execution_data)
                
            except Exception as e:
                print(f"Error processing execution: {e}")

async def subscribe_to_order_books():
    """Subscribe to order book updates from matching engine"""
    redis_conn = await get_redis()
    pubsub = redis_conn.pubsub()
    
    # Subscribe to all order book channels
    await pubsub.psubscribe("orderbook:*")
    
    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            try:
                channel = message["channel"].decode()
                symbol = channel.split(":")[1]
                order_book_data = json.loads(message["data"])
                
                # Update order book
                order_books[symbol] = OrderBook(
                    symbol=order_book_data["symbol"],
                    bids=[(Decimal(bid[0]), Decimal(bid[1])) for bid in order_book_data["bids"]],
                    asks=[(Decimal(ask[0]), Decimal(ask[1])) for ask in order_book_data["asks"]],
                    timestamp=datetime.fromisoformat(order_book_data["timestamp"])
                )
                
                # Broadcast to WebSocket clients
                await broadcast_order_book(symbol, order_book_data)
                
            except Exception as e:
                print(f"Error processing order book update: {e}")

async def broadcast_execution(execution_data: dict):
    """Broadcast execution to WebSocket clients"""
    symbol = execution_data["symbol"]
    
    # Broadcast to symbol-specific subscribers
    if symbol in websocket_connections:
        message = json.dumps({
            "type": "execution",
            "data": execution_data
        })
        
        disconnected = []
        for websocket in websocket_connections[symbol]:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            websocket_connections[symbol].remove(ws)

async def broadcast_order_book(symbol: str, order_book_data: dict):
    """Broadcast order book update to WebSocket clients"""
    if symbol in websocket_connections:
        message = json.dumps({
            "type": "orderbook",
            "data": order_book_data
        }, default=str)
        
        disconnected = []
        for websocket in websocket_connections[symbol]:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            websocket_connections[symbol].remove(ws)

@app.websocket("/ws/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for real-time market data"""
    await websocket.accept()
    websocket_connections[symbol].append(websocket)
    
    try:
        # Send current order book
        if symbol in order_books:
            await websocket.send_text(json.dumps({
                "type": "orderbook",
                "data": {
                    "symbol": order_books[symbol].symbol,
                    "bids": [[str(bid[0]), str(bid[1])] for bid in order_books[symbol].bids],
                    "asks": [[str(ask[0]), str(ask[1])] for ask in order_books[symbol].asks],
                    "timestamp": order_books[symbol].timestamp.isoformat()
                }
            }))
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text(json.dumps({"type": "pong", "data": data}))
            
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in websocket_connections[symbol]:
            websocket_connections[symbol].remove(websocket)

@app.get("/orderbook/{symbol}")
async def get_order_book(symbol: str, depth: int = Query(5, ge=1, le=20)):
    """Get order book for a symbol"""
    
    if symbol not in order_books:
        # Return mock data for demonstration
        return {
            "symbol": symbol,
            "bids": [[str(150 - i * 0.01), str(10 * (i + 1))] for i in range(depth)],
            "asks": [[str(150 + i * 0.01), str(10 * (i + 1))] for i in range(depth)],
            "timestamp": datetime.now().isoformat()
        }
    
    order_book = order_books[symbol]
    
    # Limit depth
    bids = order_book.bids[:depth]
    asks = order_book.asks[:depth]
    
    return {
        "symbol": order_book.symbol,
        "bids": [[str(bid[0]), str(bid[1])] for bid in bids],
        "asks": [[str(ask[0]), str(ask[1])] for ask in asks],
        "timestamp": order_book.timestamp.isoformat()
    }

@app.get("/orderBook/L2")
async def get_order_book_l2(symbol: str = Query(...), depth: int = Query(5, ge=1, le=20)):
    """Get L2 order book for a symbol (alternative endpoint for compatibility)"""
    return await get_order_book(symbol, depth)

@app.get("/candles", response_model=List[Candlestick])
async def get_candlestick_data(
    symbol: str,
    interval: str = Query("1m", regex="^(1m|1h|1d)$"),
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get candlestick chart data"""
    
    if symbol not in candlestick_data or interval not in candlestick_data[symbol]:
        return []
    
    candles = list(candlestick_data[symbol][interval])
    
    # Filter by time range if provided
    if start_time:
        start_dt = datetime.fromtimestamp(start_time)
        candles = [c for c in candles if c.timestamp >= start_dt]
    
    if end_time:
        end_dt = datetime.fromtimestamp(end_time)
        candles = [c for c in candles if c.timestamp <= end_dt]
    
    # Apply limit
    candles = candles[-limit:]
    
    return candles

@app.get("/best-bid-ask/{symbol}")
async def get_best_bid_ask(symbol: str):
    """Get best bid and ask for a symbol"""
    
    if symbol not in order_books:
        return {
            "symbol": symbol,
            "best_bid": None,
            "best_ask": None,
            "timestamp": datetime.now()
        }
    
    order_book = order_books[symbol]
    
    best_bid = order_book.bids[0] if order_book.bids else None
    best_ask = order_book.asks[0] if order_book.asks else None
    
    return {
        "symbol": symbol,
        "best_bid": {"price": best_bid[0], "quantity": best_bid[1]} if best_bid else None,
        "best_ask": {"price": best_ask[0], "quantity": best_ask[1]} if best_ask else None,
        "timestamp": order_book.timestamp
    }

@app.get("/symbols")
async def get_available_symbols():
    """Get list of symbols with available market data"""
    return {
        "symbols": list(order_books.keys()),
        "intervals": INTERVALS
    }

@app.get("/market-summary")
async def get_market_summary():
    """Get market summary for all symbols"""
    summary = {}
    
    for symbol, order_book in order_books.items():
        best_bid = order_book.bids[0] if order_book.bids else None
        best_ask = order_book.asks[0] if order_book.asks else None
        
        # Get latest 1-day candle for price info
        latest_candle = None
        if symbol in candlestick_data and "1d" in candlestick_data[symbol]:
            if candlestick_data[symbol]["1d"]:
                latest_candle = candlestick_data[symbol]["1d"][-1]
        
        summary[symbol] = {
            "best_bid": best_bid[0] if best_bid else None,
            "best_ask": best_ask[0] if best_ask else None,
            "last_price": latest_candle.close_price if latest_candle else None,
            "volume_24h": latest_candle.volume if latest_candle else None,
            "timestamp": order_book.timestamp
        }
    
    return summary

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "websocket_connections": {symbol: len(connections) for symbol, connections in websocket_connections.items()},
        "order_books": list(order_books.keys())
    }

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    # Start Redis subscribers
    asyncio.create_task(subscribe_to_executions())
    asyncio.create_task(subscribe_to_order_books())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8864)