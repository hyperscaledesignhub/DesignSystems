from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set
import json
import redis.asyncio as redis
import asyncio
import os
import sys
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import local tracing module  
from tracing import setup_tracing, instrument_fastapi, create_span_attributes

# Initialize tracing first
tracer = setup_tracing("websocket-service")

app = FastAPI(title="WebSocket Service")

# Instrument FastAPI app for tracing
instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, channel: str, user_id: str = None):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        if user_id:
            self.user_connections[user_id] = websocket
        logger.info(f"New connection to channel: {channel}, user: {user_id}")
        
    def disconnect(self, websocket: WebSocket, channel: str, user_id: str = None):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        logger.info(f"Disconnected from channel: {channel}, user: {user_id}")
        
    async def broadcast_to_channel(self, message: dict, channel: str):
        if channel in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.add(connection)
            for conn in dead_connections:
                self.active_connections[channel].discard(conn)
                
    async def send_to_user(self, message: dict, user_id: str):
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json(message)
            except:
                del self.user_connections[user_id]

manager = ConnectionManager()
redis_client = None

async def get_redis():
    global redis_client
    if not redis_client:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        redis_client = await redis.from_url(redis_url, decode_responses=True)
    return redis_client

@app.on_event("startup")
async def startup():
    await get_redis()
    asyncio.create_task(redis_subscriber())

async def redis_subscriber():
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(
        "leaderboard:updates",
        "game:updates", 
        "tournament:updates",
        "score:updates"
    )
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                channel = message['channel'].split(':')[0]
                
                await manager.broadcast_to_channel({
                    "type": f"{channel}_update",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }, channel)
                
            except Exception as e:
                logger.error(f"Error processing Redis message: {e}")

@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str, user_id: str = None):
    await manager.connect(websocket, channel, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
            elif data.get("type") == "subscribe":
                sub_channels = data.get("channels", [])
                for ch in sub_channels:
                    await manager.connect(websocket, ch, user_id)
                    
            elif data.get("type") == "message":
                await manager.broadcast_to_channel({
                    "type": "user_message",
                    "user_id": user_id,
                    "message": data.get("message"),
                    "timestamp": datetime.utcnow().isoformat()
                }, channel)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel, user_id)

@app.post("/broadcast/{channel}")
async def broadcast_message(channel: str, message: dict):
    with tracer.start_as_current_span("broadcast_message", attributes=create_span_attributes(
        operation="websocket_broadcast",
        channel=channel,
        message_type=message.get("type", "unknown")
    )) as span:
        await manager.broadcast_to_channel(message, channel)
        
        r = await get_redis()
        await r.publish(f"{channel}:updates", json.dumps(message))
        
        span.set_attributes(create_span_attributes(
            active_connections=sum(len(conns) for conns in manager.active_connections.values()),
            channel_connections=len(manager.active_connections.get(channel, set()))
        ))
        
        return {"status": "broadcasted", "channel": channel}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "websocket-service",
        "active_channels": list(manager.active_connections.keys()),
        "connection_count": sum(len(conns) for conns in manager.active_connections.values())
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "23456"))
    uvicorn.run(app, host="0.0.0.0", port=port)