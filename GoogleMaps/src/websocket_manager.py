"""
WebSocket Manager for Real-time Updates
Handles live location sharing, navigation updates, and traffic feeds
"""

import logging
import json
import asyncio
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum

logger = logging.getLogger(__name__)

class ChannelType(Enum):
    LOCATION = "location"
    NAVIGATION = "navigation"
    TRAFFIC = "traffic"
    NEARBY = "nearby"

class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        # Store active connections by channel and user
        self.active_connections: Dict[ChannelType, Dict[str, WebSocket]] = {
            ChannelType.LOCATION: {},
            ChannelType.NAVIGATION: {},
            ChannelType.TRAFFIC: {},
            ChannelType.NEARBY: {}
        }
        
        # Store user subscriptions
        self.user_subscriptions: Dict[str, Set[str]] = {}
        
        # Store navigation sessions
        self.navigation_sessions: Dict[str, Dict] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        channel: ChannelType
    ):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        # Store connection
        if channel not in self.active_connections:
            self.active_connections[channel] = {}
        
        self.active_connections[channel][user_id] = websocket
        
        # Initialize user subscriptions
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        
        logger.info(f"User {user_id} connected to {channel.value} channel")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "channel": channel.value,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
    
    def disconnect(self, user_id: str, channel: ChannelType):
        """Remove a WebSocket connection"""
        if channel in self.active_connections:
            if user_id in self.active_connections[channel]:
                del self.active_connections[channel][user_id]
                logger.info(f"User {user_id} disconnected from {channel.value} channel")
        
        # Clean up subscriptions if no active connections
        all_disconnected = True
        for ch in self.active_connections.values():
            if user_id in ch:
                all_disconnected = False
                break
        
        if all_disconnected and user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast_to_channel(
        self,
        message: Dict,
        channel: ChannelType,
        exclude_user: Optional[str] = None
    ):
        """Broadcast message to all users in a channel"""
        if channel not in self.active_connections:
            return
        
        disconnected_users = []
        
        for user_id, websocket in self.active_connections[channel].items():
            if user_id == exclude_user:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id, channel)
    
    async def broadcast_to_nearby_users(
        self,
        message: Dict,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        channel: ChannelType = ChannelType.NEARBY
    ):
        """Broadcast to users within a geographic radius"""
        # This would integrate with location service to find nearby users
        # For now, broadcast to all in nearby channel
        await self.broadcast_to_channel(message, channel)
    
    async def send_location_update(
        self,
        user_id: str,
        location_data: Dict
    ):
        """Send location update to subscribers"""
        message = {
            "type": "location_update",
            "user_id": user_id,
            "data": location_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to user's subscribers
        if user_id in self.user_subscriptions:
            for subscriber_id in self.user_subscriptions[user_id]:
                if subscriber_id in self.active_connections[ChannelType.LOCATION]:
                    websocket = self.active_connections[ChannelType.LOCATION][subscriber_id]
                    await self.send_personal_message(message, websocket)
    
    async def send_navigation_update(
        self,
        user_id: str,
        navigation_data: Dict
    ):
        """Send navigation update (ETA, reroute, etc.)"""
        message = {
            "type": "navigation_update",
            "user_id": user_id,
            "data": navigation_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id in self.active_connections[ChannelType.NAVIGATION]:
            websocket = self.active_connections[ChannelType.NAVIGATION][user_id]
            await self.send_personal_message(message, websocket)
    
    async def broadcast_traffic_update(
        self,
        traffic_data: Dict,
        affected_routes: Optional[Set[str]] = None
    ):
        """Broadcast traffic updates to affected users"""
        message = {
            "type": "traffic_update",
            "data": traffic_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if affected_routes:
            # Send to users on affected routes
            for user_id, session in self.navigation_sessions.items():
                if session.get("route_id") in affected_routes:
                    if user_id in self.active_connections[ChannelType.TRAFFIC]:
                        websocket = self.active_connections[ChannelType.TRAFFIC][user_id]
                        await self.send_personal_message(message, websocket)
        else:
            # Broadcast to all traffic subscribers
            await self.broadcast_to_channel(message, ChannelType.TRAFFIC)
    
    async def handle_location_stream(
        self,
        websocket: WebSocket,
        user_id: str
    ):
        """Handle incoming location stream from user"""
        try:
            while True:
                # Receive location data
                data = await websocket.receive_json()
                
                if data.get("type") == "location":
                    # Process location update
                    location_data = {
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "accuracy": data.get("accuracy"),
                        "speed": data.get("speed"),
                        "bearing": data.get("bearing"),
                        "timestamp": data.get("timestamp", datetime.utcnow().timestamp())
                    }
                    
                    # Broadcast to subscribers
                    await self.send_location_update(user_id, location_data)
                    
                    # Send acknowledgment
                    await self.send_personal_message(
                        {
                            "type": "ack",
                            "status": "received",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        websocket
                    )
                
                elif data.get("type") == "subscribe":
                    # Subscribe to another user's location
                    target_user = data.get("target_user_id")
                    if target_user and target_user != user_id:
                        if target_user not in self.user_subscriptions:
                            self.user_subscriptions[target_user] = set()
                        self.user_subscriptions[target_user].add(user_id)
                        
                        await self.send_personal_message(
                            {
                                "type": "subscription",
                                "status": "subscribed",
                                "target_user": target_user,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            websocket
                        )
                
                elif data.get("type") == "unsubscribe":
                    # Unsubscribe from user's location
                    target_user = data.get("target_user_id")
                    if target_user in self.user_subscriptions:
                        self.user_subscriptions[target_user].discard(user_id)
                
        except WebSocketDisconnect:
            self.disconnect(user_id, ChannelType.LOCATION)
        except Exception as e:
            logger.error(f"Error in location stream for user {user_id}: {e}")
            self.disconnect(user_id, ChannelType.LOCATION)
    
    async def handle_navigation_stream(
        self,
        websocket: WebSocket,
        user_id: str,
        route_id: str
    ):
        """Handle navigation session with real-time updates"""
        try:
            # Store navigation session
            self.navigation_sessions[user_id] = {
                "route_id": route_id,
                "started_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "position_update":
                    # Process position update during navigation
                    current_position = {
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude")
                    }
                    
                    # Calculate new ETA (would integrate with navigation service)
                    eta_update = {
                        "type": "eta_update",
                        "current_position": current_position,
                        "remaining_distance_km": data.get("remaining_distance", 0),
                        "remaining_time_minutes": data.get("remaining_time", 0),
                        "next_instruction": data.get("next_instruction", "")
                    }
                    
                    await self.send_navigation_update(user_id, eta_update)
                
                elif data.get("type") == "navigation_end":
                    # End navigation session
                    if user_id in self.navigation_sessions:
                        self.navigation_sessions[user_id]["status"] = "completed"
                        self.navigation_sessions[user_id]["ended_at"] = datetime.utcnow().isoformat()
                    
                    await self.send_personal_message(
                        {
                            "type": "navigation_complete",
                            "route_id": route_id,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        websocket
                    )
                    break
                
        except WebSocketDisconnect:
            self.disconnect(user_id, ChannelType.NAVIGATION)
            if user_id in self.navigation_sessions:
                self.navigation_sessions[user_id]["status"] = "disconnected"
        except Exception as e:
            logger.error(f"Error in navigation stream for user {user_id}: {e}")
            self.disconnect(user_id, ChannelType.NAVIGATION)
    
    async def handle_traffic_stream(
        self,
        websocket: WebSocket,
        user_id: str,
        area_bounds: Optional[Dict] = None
    ):
        """Handle traffic updates subscription"""
        try:
            # Send initial traffic state
            await self.send_personal_message(
                {
                    "type": "traffic_init",
                    "area": area_bounds,
                    "timestamp": datetime.utcnow().isoformat()
                },
                websocket
            )
            
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "report_incident":
                    # User reporting traffic incident
                    incident = {
                        "reporter_id": user_id,
                        "type": data.get("incident_type", "traffic"),
                        "severity": data.get("severity", "moderate"),
                        "location": {
                            "latitude": data.get("latitude"),
                            "longitude": data.get("longitude")
                        },
                        "description": data.get("description", ""),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Broadcast incident to nearby users
                    await self.broadcast_traffic_update(
                        {"incident": incident},
                        affected_routes=None  # Would calculate affected routes
                    )
                
                elif data.get("type") == "update_area":
                    # User moved to different area
                    area_bounds = data.get("bounds")
                    # Update subscription area
                
        except WebSocketDisconnect:
            self.disconnect(user_id, ChannelType.TRAFFIC)
        except Exception as e:
            logger.error(f"Error in traffic stream for user {user_id}: {e}")
            self.disconnect(user_id, ChannelType.TRAFFIC)

# Global connection manager instance
manager = ConnectionManager()