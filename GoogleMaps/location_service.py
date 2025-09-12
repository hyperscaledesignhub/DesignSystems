#!/usr/bin/env python3
"""
Location Service - Real-time Location Updates & Traffic Simulation
Handles user location updates and generates mock traffic data
Port: 8085 (New location service)
"""

import asyncio
import uuid
import time
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Models
class LocationUpdate(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    timestamp: str
    speed_kmh: Optional[float] = None
    vehicle_type: Optional[str] = "car"
    navigation_active: bool = False

class LocationBatch(BaseModel):
    locations: List[LocationUpdate]
    timestamp: str

class TrafficRequest(BaseModel):
    center_lat: float
    center_lng: float
    radius_km: float = 5.0

@dataclass
class MockUser:
    user_id: str
    current_lat: float
    current_lng: float
    destination_lat: float
    destination_lng: float
    speed_kmh: float
    route_points: List[Tuple[float, float]]
    current_route_index: int
    vehicle_type: str
    last_update: datetime

class LocationService:
    def __init__(self):
        self.user_locations: Dict[str, LocationUpdate] = {}
        self.location_history: List[LocationUpdate] = []
        self.mock_users: List[MockUser] = []
        self.is_simulation_running = False
        self.simulation_center_lat = 12.9716  # Default Bangalore
        self.simulation_center_lng = 77.5946
        
    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat/2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlng/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def generate_random_point_in_radius(self, center_lat: float, center_lng: float, radius_km: float) -> Tuple[float, float]:
        """Generate random coordinate within radius"""
        radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km
        
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, radius_deg) * math.sqrt(random.uniform(0, 1))
        
        lat = center_lat + distance * math.cos(angle)
        lng = center_lng + distance * math.sin(angle)
        
        return (lat, lng)
    
    def generate_major_routes(self, center_lat: float, center_lng: float) -> List[List[Tuple[float, float]]]:
        """Generate major routes dynamically based on center location"""
        routes = []
        
        directions = [
            (0, 1),      # North
            (1, 1),      # Northeast  
            (1, 0),      # East
            (1, -1),     # Southeast
            (0, -1),     # South
            (-1, -1),    # Southwest
            (-1, 0),     # West
            (-1, 1)      # Northwest
        ]
        
        for dx, dy in directions:
            route_length = random.uniform(2, 4)  # 2-4 km routes
            
            lat_offset = (dy * route_length) / 111.0
            lng_offset = (dx * route_length) / (111.0 * math.cos(math.radians(center_lat)))
            
            intermediate_lat = center_lat + lat_offset * 0.5
            intermediate_lng = center_lng + lng_offset * 0.5
            end_lat = center_lat + lat_offset
            end_lng = center_lng + lng_offset
            
            route = [
                (center_lat, center_lng),
                (intermediate_lat, intermediate_lng),
                (end_lat, end_lng)
            ]
            routes.append(route)
            
        return routes
    
    def interpolate_route(self, start: Tuple[float, float], end: Tuple[float, float], num_points: int = 8) -> List[Tuple[float, float]]:
        """Create route points between start and end"""
        route_points = []
        for i in range(num_points + 1):
            ratio = i / num_points
            lat = start[0] + (end[0] - start[0]) * ratio
            lng = start[1] + (end[1] - start[1]) * ratio
            route_points.append((lat, lng))
        return route_points
    
    def create_mock_users(self, center_lat: float, center_lng: float, num_users: int = 60) -> List[MockUser]:
        """Create mock users with realistic routes"""
        users = []
        major_routes = self.generate_major_routes(center_lat, center_lng)
        
        for i in range(num_users):
            user_id = f"mock_user_{i:03d}"
            
            # 70% use major routes, 30% use random routes
            if random.random() < 0.7 and major_routes:
                route = random.choice(major_routes)
                start_point = route[0]
                end_point = route[-1]
                route_points = []
                for point in route:
                    lat_offset = random.uniform(-0.001, 0.001)
                    lng_offset = random.uniform(-0.001, 0.001)
                    route_points.append((point[0] + lat_offset, point[1] + lng_offset))
            else:
                start_point = self.generate_random_point_in_radius(center_lat, center_lng, 5.0)
                end_point = self.generate_random_point_in_radius(center_lat, center_lng, 5.0)
                route_points = self.interpolate_route(start_point, end_point, 8)
            
            # Realistic speeds based on time and vehicle type
            vehicle_types = ["car", "bike", "auto", "bus"]
            vehicle_type = random.choice(vehicle_types)
            
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 10 or 17 <= current_hour <= 20:  # Rush hours
                base_speed = {"car": 15, "bike": 20, "auto": 12, "bus": 10}
            else:
                base_speed = {"car": 35, "bike": 40, "auto": 25, "bus": 20}
                
            speed_kmh = base_speed[vehicle_type] + random.uniform(-5, 10)
            speed_kmh = max(5, speed_kmh)
            
            user = MockUser(
                user_id=user_id,
                current_lat=start_point[0],
                current_lng=start_point[1],
                destination_lat=end_point[0],
                destination_lng=end_point[1],
                speed_kmh=speed_kmh,
                route_points=route_points,
                current_route_index=0,
                vehicle_type=vehicle_type,
                last_update=datetime.now()
            )
            users.append(user)
        
        return users
    
    def update_mock_user_location(self, user: MockUser, center_lat: float, center_lng: float) -> bool:
        """Update mock user's location along their route"""
        if user.current_route_index >= len(user.route_points) - 1:
            # User reached destination, create new route
            start_point = self.generate_random_point_in_radius(center_lat, center_lng, 5.0)
            end_point = self.generate_random_point_in_radius(center_lat, center_lng, 5.0)
            user.route_points = self.interpolate_route(start_point, end_point, 8)
            user.current_route_index = 0
            user.destination_lat = end_point[0]
            user.destination_lng = end_point[1]
        
        # Move to next point on route
        next_point = user.route_points[user.current_route_index + 1]
        user.current_lat = next_point[0]
        user.current_lng = next_point[1]
        user.current_route_index += 1
        user.last_update = datetime.now()
        
        return True
    
    async def start_traffic_simulation(self, center_lat: float, center_lng: float):
        """Start mock traffic simulation"""
        if self.is_simulation_running:
            return
            
        self.simulation_center_lat = center_lat
        self.simulation_center_lng = center_lng
        self.mock_users = self.create_mock_users(center_lat, center_lng, 60)
        self.is_simulation_running = True
        
        print(f"🚀 Started traffic simulation at ({center_lat:.4f}, {center_lng:.4f})")
        print(f"👥 Generated {len(self.mock_users)} mock users")
        
        # Start background simulation task
        asyncio.create_task(self._simulation_loop())
    
    async def _simulation_loop(self):
        """Background task for updating mock user locations"""
        while self.is_simulation_running:
            try:
                # Update all mock users
                for user in self.mock_users:
                    self.update_mock_user_location(user, self.simulation_center_lat, self.simulation_center_lng)
                    
                    # Add to location history
                    location_update = LocationUpdate(
                        user_id=user.user_id,
                        latitude=user.current_lat,
                        longitude=user.current_lng,
                        timestamp=user.last_update.isoformat(),
                        speed_kmh=user.speed_kmh,
                        vehicle_type=user.vehicle_type,
                        navigation_active=True
                    )
                    
                    self.user_locations[user.user_id] = location_update
                    self.location_history.append(location_update)
                    
                    # Keep only last 1000 location updates
                    if len(self.location_history) > 1000:
                        self.location_history = self.location_history[-1000:]
                
                # Wait 15 seconds before next update
                await asyncio.sleep(15)
                
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                await asyncio.sleep(5)
    
    def get_traffic_data(self, center_lat: float, center_lng: float, radius_km: float) -> Dict:
        """Get traffic data for a specific area"""
        recent_locations = [
            loc for loc in self.location_history 
            if (datetime.now() - datetime.fromisoformat(loc.timestamp.replace('Z', '+00:00').replace('+00:00', ''))).seconds < 300  # Last 5 minutes
        ]
        
        # Filter locations within radius
        area_locations = []
        for loc in recent_locations:
            distance = self.calculate_distance(center_lat, center_lng, loc.latitude, loc.longitude)
            if distance <= radius_km:
                area_locations.append(loc)
        
        # Calculate traffic metrics
        if not area_locations:
            return {
                "traffic_level": "light",
                "average_speed": 40.0,
                "active_users": 0,
                "congestion_areas": []
            }
        
        avg_speed = sum(loc.speed_kmh or 30 for loc in area_locations) / len(area_locations)
        
        # Determine traffic level
        if avg_speed > 30:
            traffic_level = "light"
        elif avg_speed > 20:
            traffic_level = "moderate"
        elif avg_speed > 10:
            traffic_level = "heavy"
        else:
            traffic_level = "severe"
        
        return {
            "traffic_level": traffic_level,
            "average_speed": round(avg_speed, 1),
            "active_users": len(set(loc.user_id for loc in area_locations)),
            "congestion_areas": self._identify_congestion_areas(area_locations, center_lat, center_lng)
        }
    
    def _identify_congestion_areas(self, locations: List[LocationUpdate], center_lat: float, center_lng: float) -> List[Dict]:
        """Identify areas with traffic congestion - show all user activity"""
        congestion_areas = []
        
        # Use smaller grid for better visibility of individual users
        grid_size = 0.01  # ~1km grid 
        grid_users = {}
        
        for loc in locations:
            grid_lat = round(loc.latitude / grid_size) * grid_size
            grid_lng = round(loc.longitude / grid_size) * grid_size
            grid_key = (grid_lat, grid_lng)
            
            if grid_key not in grid_users:
                grid_users[grid_key] = []
            grid_users[grid_key].append(loc)
        
        # Show ALL grids with users (even single users) and prioritize by user count
        potential_areas = []
        for (grid_lat, grid_lng), users in grid_users.items():
            if len(users) >= 1:  # Show even single users
                avg_speed = sum(u.speed_kmh or 30 for u in users) / len(users)
                
                # Determine severity based on speed and user count
                if len(users) >= 5:
                    severity = "high"
                elif len(users) >= 3:
                    severity = "medium" 
                else:
                    severity = "low"
                
                # Override severity if speed is very slow
                if avg_speed < 10:
                    severity = "high"
                elif avg_speed < 20:
                    severity = "medium"
                    
                potential_areas.append({
                    "lat": grid_lat,
                    "lng": grid_lng,
                    "severity": severity,
                    "user_count": len(users),
                    "avg_speed": round(avg_speed, 1),
                    "weight": len(users) * 10 + (30 - avg_speed)  # Weight by user count and speed
                })
        
        # Sort by weight and take top 20 most significant areas for better visibility
        potential_areas.sort(key=lambda x: x["weight"], reverse=True)
        for area in potential_areas[:20]:
            del area["weight"]  # Remove weight from final result
            congestion_areas.append(area)
        
        return congestion_areas

# FastAPI App
app = FastAPI(title="Location Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

location_service = LocationService()

@app.post("/api/locations/batch")
async def batch_location_update(batch: LocationBatch):
    """Receive batch location updates"""
    for location in batch.locations:
        location_service.user_locations[location.user_id] = location
        location_service.location_history.append(location)
    
    # Keep only last 1000 locations
    if len(location_service.location_history) > 1000:
        location_service.location_history = location_service.location_history[-1000:]
    
    return {"status": "success", "processed": len(batch.locations)}

@app.post("/api/locations/single")
async def single_location_update(location: LocationUpdate):
    """Receive single location update"""
    location_service.user_locations[location.user_id] = location
    location_service.location_history.append(location)
    
    return {"status": "success"}

@app.get("/api/locations/user/{user_id}")
async def get_user_location(user_id: str):
    """Get latest location for a specific user"""
    if user_id not in location_service.user_locations:
        raise HTTPException(status_code=404, detail="User not found")
    
    return location_service.user_locations[user_id]

@app.post("/api/traffic/start-simulation")
async def start_traffic_simulation(request: TrafficRequest):
    """Start mock traffic simulation for an area"""
    await location_service.start_traffic_simulation(request.center_lat, request.center_lng)
    
    return {
        "status": "started",
        "center": {"lat": request.center_lat, "lng": request.center_lng},
        "radius_km": request.radius_km,
        "mock_users": len(location_service.mock_users)
    }

@app.get("/api/traffic/data")
async def get_traffic_data(lat: float, lng: float, radius: float = 5.0):
    """Get real-time traffic data for an area"""
    traffic_data = location_service.get_traffic_data(lat, lng, radius)
    
    return {
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius,
        "timestamp": datetime.now().isoformat(),
        **traffic_data
    }

@app.get("/api/locations/stats")
async def get_location_stats():
    """Get location service statistics"""
    recent_count = len([
        loc for loc in location_service.location_history 
        if (datetime.now() - datetime.fromisoformat(loc.timestamp.replace('Z', '+00:00').replace('+00:00', ''))).seconds < 300
    ])
    
    return {
        "total_users": len(location_service.user_locations),
        "mock_users": len(location_service.mock_users),
        "recent_updates": recent_count,
        "total_history": len(location_service.location_history),
        "simulation_running": location_service.is_simulation_running,
        "simulation_center": {
            "lat": location_service.simulation_center_lat,
            "lng": location_service.simulation_center_lng
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "location-service",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "simulation_running": location_service.is_simulation_running
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Location Service on port 8086")
    uvicorn.run(app, host="0.0.0.0", port=8086)