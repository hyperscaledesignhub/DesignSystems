from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, str] = {}  # websocket_id -> user_id
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        self.user_connections[id(websocket)] = user_id
        
        print(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket):
        websocket_id = id(websocket)
        if websocket_id in self.user_connections:
            user_id = self.user_connections[websocket_id]
            
            if user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            del self.user_connections[websocket_id]
            print(f"User {user_id} disconnected")
    
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def send_personal_json(self, data: dict, user_id: str):
        await self.send_personal_message(json.dumps(data), user_id)
    
    async def broadcast_message(self, message: str):
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_text(message)
                except:
                    pass
    
    def is_user_online(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_online_users(self) -> List[str]:
        return list(self.active_connections.keys())

manager = ConnectionManager()