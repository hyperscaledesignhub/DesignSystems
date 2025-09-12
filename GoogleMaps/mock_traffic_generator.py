#!/usr/bin/env python3
"""
Mock Traffic Generator - Real-time User Location Simulation
Generates 50+ mock users traveling within 5km radius of Bangalore
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json
import math
import requests
from dataclasses import dataclass

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

class TrafficSimulator:
    def __init__(self, center_lat: float = None, center_lng: float = None):
        # Use provided coordinates or default to Bangalore
        self.center_lat = center_lat or 12.9716
        self.center_lng = center_lng or 77.5946
        self.radius_km = 5.0
        
        print(f"🎯 Traffic simulation centered at: ({self.center_lat:.4f}, {self.center_lng:.4f})")
        
        # Generate major routes dynamically based on current location
        self.major_routes = self._generate_major_routes()
        
        self.mock_users: List[MockUser] = []
        self.location_service_url = "http://localhost:8080/api/locations/batch"
    
    def _generate_major_routes(self) -> List[List[Tuple[float, float]]]:
        """Generate major routes dynamically based on current location"""
        routes = []
        
        # Generate 8 major routes in different directions from current location
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
            # Create route from center to 3-5km in this direction
            route_length = random.uniform(2, 4)  # 2-4 km routes
            
            # Convert to approximate lat/lng offsets
            lat_offset = (dy * route_length) / 111.0  # 1 degree ≈ 111 km
            lng_offset = (dx * route_length) / (111.0 * math.cos(math.radians(self.center_lat)))
            
            # Create route with intermediate points
            intermediate_lat = self.center_lat + lat_offset * 0.5
            intermediate_lng = self.center_lng + lng_offset * 0.5
            end_lat = self.center_lat + lat_offset
            end_lng = self.center_lng + lng_offset
            
            route = [
                (self.center_lat, self.center_lng),                    # Start (your location)
                (intermediate_lat, intermediate_lng),                  # Intermediate point
                (end_lat, end_lng)                                     # End point
            ]
            routes.append(route)
            
        return routes
        
    def generate_random_point_in_radius(self, center_lat: float, center_lng: float, radius_km: float) -> Tuple[float, float]:
        """Generate random coordinate within radius"""
        # Convert radius to degrees (approximately)
        radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km
        
        # Generate random angle and distance
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, radius_deg) * math.sqrt(random.uniform(0, 1))
        
        # Calculate coordinates
        lat = center_lat + distance * math.cos(angle)
        lng = center_lng + distance * math.sin(angle)
        
        return (lat, lng)
    
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
    
    def interpolate_route(self, start: Tuple[float, float], end: Tuple[float, float], num_points: int = 10) -> List[Tuple[float, float]]:
        """Create route points between start and end"""
        route_points = []
        for i in range(num_points + 1):
            ratio = i / num_points
            lat = start[0] + (end[0] - start[0]) * ratio
            lng = start[1] + (end[1] - start[1]) * ratio
            route_points.append((lat, lng))
        return route_points
    
    def create_mock_users(self, num_users: int = 60) -> List[MockUser]:
        """Create mock users with realistic routes"""
        users = []
        
        for i in range(num_users):
            user_id = f"mock_user_{i:03d}"
            
            # Choose random major route or random points
            if random.random() < 0.7:  # 70% use major routes
                route = random.choice(self.major_routes)
                start_point = route[0]
                end_point = route[-1]
                # Add some randomness to route points
                route_points = []
                for point in route:
                    lat_offset = random.uniform(-0.001, 0.001)
                    lng_offset = random.uniform(-0.001, 0.001)
                    route_points.append((point[0] + lat_offset, point[1] + lng_offset))
            else:  # 30% use completely random routes
                start_point = self.generate_random_point_in_radius(self.center_lat, self.center_lng, self.radius_km)
                end_point = self.generate_random_point_in_radius(self.center_lat, self.center_lng, self.radius_km)
                route_points = self.interpolate_route(start_point, end_point, 8)
            
            # Realistic speeds based on time of day and vehicle type
            vehicle_types = ["car", "bike", "auto", "bus"]
            vehicle_type = random.choice(vehicle_types)
            
            # Speed varies by vehicle and traffic conditions
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 10 or 17 <= current_hour <= 20:  # Rush hours
                base_speed = {"car": 15, "bike": 20, "auto": 12, "bus": 10}
            else:  # Non-rush hours
                base_speed = {"car": 35, "bike": 40, "auto": 25, "bus": 20}
                
            speed_kmh = base_speed[vehicle_type] + random.uniform(-5, 10)
            speed_kmh = max(5, speed_kmh)  # Minimum 5 km/h
            
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
    
    def update_user_location(self, user: MockUser) -> bool:
        """Update user's location along their route"""
        if user.current_route_index >= len(user.route_points) - 1:
            # User reached destination, create new route
            start_point = self.generate_random_point_in_radius(self.center_lat, self.center_lng, self.radius_km)
            end_point = self.generate_random_point_in_radius(self.center_lat, self.center_lng, self.radius_km)
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
    
    async def send_location_batch(self, location_updates: List[Dict]) -> bool:
        """Send batch location updates to location service"""
        try:
            payload = {
                "locations": location_updates,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                self.location_service_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Sent {len(location_updates)} location updates")
                return True
            else:
                print(f"❌ Location service error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send locations: {e}")
            return False
    
    async def run_simulation(self):
        """Main simulation loop"""
        print(f"🚀 Starting traffic simulation with {len(self.mock_users)} users")
        print(f"📍 Center: ({self.center_lat}, {self.center_lng})")
        print(f"📏 Radius: {self.radius_km}km")
        
        while True:
            try:
                location_updates = []
                
                # Update each user's location
                for user in self.mock_users:
                    self.update_user_location(user)
                    
                    # Create location update
                    location_update = {
                        "user_id": user.user_id,
                        "latitude": user.current_lat,
                        "longitude": user.current_lng,
                        "timestamp": user.last_update.isoformat(),
                        "speed_kmh": user.speed_kmh,
                        "vehicle_type": user.vehicle_type,
                        "navigation_active": True
                    }
                    location_updates.append(location_update)
                
                # Send batch update
                await self.send_location_batch(location_updates)
                
                # Show some stats
                avg_speed = sum(user.speed_kmh for user in self.mock_users) / len(self.mock_users)
                print(f"📊 Average speed: {avg_speed:.1f} km/h | Active users: {len(self.mock_users)}")
                
                # Wait before next update (every 15 seconds)
                await asyncio.sleep(15)
                
            except KeyboardInterrupt:
                print("🛑 Simulation stopped by user")
                break
            except Exception as e:
                print(f"❌ Simulation error: {e}")
                await asyncio.sleep(5)

async def main():
    """Main function"""
    import sys
    
    # Get current location from command line or use default
    if len(sys.argv) >= 3:
        center_lat = float(sys.argv[1])
        center_lng = float(sys.argv[2])
        print(f"📍 Using provided location: ({center_lat:.4f}, {center_lng:.4f})")
    else:
        # Try to get user's current location from UI or use default
        center_lat = None
        center_lng = None
        print("📍 Using default location - pass lat lng as arguments to use your current location")
    
    simulator = TrafficSimulator(center_lat, center_lng)
    
    # Create mock users
    simulator.mock_users = simulator.create_mock_users(60)
    
    print("🎯 Mock Traffic Generator")
    print("=" * 50)
    print(f"👥 Generated {len(simulator.mock_users)} mock users")
    print(f"📏 Coverage radius: {simulator.radius_km}km")
    print(f"🛣️ Major routes: {len(simulator.major_routes)}")
    
    # Run simulation
    await simulator.run_simulation()

if __name__ == "__main__":
    asyncio.run(main())