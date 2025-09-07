from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Set
import jwt
import redis.asyncio as redis
import json
import asyncio
import os
from datetime import datetime
from contextlib import asynccontextmanager
import httpx

app = FastAPI(title="WebSocket Gateway", version="1.0.0")

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
ALGORITHM = "HS256"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://location-service:8903")
FRIEND_SERVICE_URL = os.getenv("FRIEND_SERVICE_URL", "http://friend-service:8902")

redis_client = None
pubsub = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_subscriptions: Dict[int, Set[int]] = {}
        self.subscription_tasks: Dict[int, asyncio.Task] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        self.active_connections[user_id] = websocket
        self.user_subscriptions[user_id] = set()
    
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
        if user_id in self.subscription_tasks:
            self.subscription_tasks[user_id].cancel()
            del self.subscription_tasks[user_id]
    
    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)
    
    async def subscribe_to_friends(self, user_id: int, token: str):
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                f"{FRIEND_SERVICE_URL}/friends/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                friends = response.json()
                friend_ids = [f['friend_id'] for f in friends]
                self.user_subscriptions[user_id] = set(friend_ids)
                return friend_ids
        return []

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, pubsub
    redis_client = await redis.from_url(REDIS_URL)
    pubsub = redis_client.pubsub()
    yield
    await pubsub.close()
    await redis_client.close()

app = FastAPI(title="WebSocket Gateway", version="1.0.0", lifespan=lifespan)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def listen_to_location_updates(user_id: int, friend_ids: Set[int]):
    channels = [f"location_channel:{friend_id}" for friend_id in friend_ids]
    
    if not channels:
        return
    
    await pubsub.subscribe(*channels)
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                friend_id = data['user_id']
                
                if friend_id in friend_ids:
                    user_location = await redis_client.get(f"location:{user_id}")
                    if user_location:
                        user_loc = json.loads(user_location)
                        friend_location = await redis_client.get(f"location:{friend_id}")
                        
                        if friend_location:
                            friend_loc = json.loads(friend_location)
                            
                            from geopy.distance import geodesic
                            distance = geodesic(
                                (user_loc['latitude'], user_loc['longitude']),
                                (friend_loc['latitude'], friend_loc['longitude'])
                            ).miles
                            
                            if distance <= 5:
                                update_message = {
                                    "type": "nearby_update",
                                    "friend_id": friend_id,
                                    "latitude": friend_loc['latitude'],
                                    "longitude": friend_loc['longitude'],
                                    "distance_miles": round(distance, 2),
                                    "timestamp": friend_loc['timestamp']
                                }
                                
                                await manager.send_personal_message(
                                    json.dumps(update_message),
                                    user_id
                                )
    except asyncio.CancelledError:
        await pubsub.unsubscribe(*channels)
        raise

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user_id = None
    try:
        await websocket.accept()
        
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)
        
        if auth_data.get('type') != 'auth':
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        token = auth_data.get('token')
        if not token:
            await websocket.close(code=1008, reason="Token required")
            return
        
        payload = verify_token(token)
        user_id = payload['user_id']
        
        await manager.connect(user_id, websocket)
        
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Successfully connected"
        }))
        
        friend_ids = await manager.subscribe_to_friends(user_id, token)
        
        if user_id in manager.user_subscriptions:
            task = asyncio.create_task(
                listen_to_location_updates(user_id, manager.user_subscriptions[user_id])
            )
            manager.subscription_tasks[user_id] = task
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                f"{LOCATION_SERVICE_URL}/location/nearby/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                nearby_friends = response.json()
                await websocket.send_text(json.dumps({
                    "type": "initial_nearby",
                    "friends": nearby_friends
                }))
        
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data['type'] == 'location_update':
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {token}"}
                    response = await client.post(
                        f"{LOCATION_SERVICE_URL}/location/update",
                        headers=headers,
                        json={
                            "latitude": data['latitude'],
                            "longitude": data['longitude']
                        }
                    )
                    
                    if response.status_code == 200:
                        await websocket.send_text(json.dumps({
                            "type": "location_updated",
                            "message": "Location updated successfully"
                        }))
            
            elif data['type'] == 'ping':
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }))
    
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id)
    except Exception as e:
        if user_id:
            manager.disconnect(user_id)
        await websocket.close(code=1011, reason=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "websocket-gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8904)