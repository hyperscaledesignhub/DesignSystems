#!/usr/bin/env python3
"""
Simple API Gateway for Testing Core Location Services with Real Databases
Connects to Redis and PostgreSQL Docker containers
"""

import asyncio
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import math
import heapq
from enum import Enum

try:
    import redis
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "redis", "psycopg2-binary", "fastapi", "uvicorn"])
    
    import redis
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn

# Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "maps_spatial"
POSTGRES_USER = "maps_user" 
POSTGRES_PASSWORD = "maps_password"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Google Maps Clone - Simple API",
    description="Testing API with real Redis and PostgreSQL",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    accuracy: float = 10.0
    speed: float = 0.0
    heading: float = 0.0
    altitude: float = 0.0
    timestamp: Optional[str] = None

class LocationBatch(BaseModel):
    user_id: str
    locations: List[LocationUpdate]
    anonymous: bool = False

# Navigation & Routing Models
class TravelMode(str, Enum):
    DRIVING = "driving"
    WALKING = "walking"
    CYCLING = "cycling" 
    TRANSIT = "transit"

class RoutePreference(str, Enum):
    FASTEST = "fastest"
    SHORTEST = "shortest"
    AVOID_TOLLS = "avoid_tolls"
    AVOID_HIGHWAYS = "avoid_highways"

class Waypoint(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    stop_duration: Optional[int] = 0  # minutes

class RouteRequest(BaseModel):
    origin: Waypoint
    destination: Waypoint
    waypoints: Optional[List[Waypoint]] = []
    travel_mode: TravelMode = TravelMode.DRIVING
    preference: RoutePreference = RoutePreference.FASTEST
    alternatives: bool = True
    include_traffic: bool = True
    departure_time: Optional[str] = None

class NavigationStep(BaseModel):
    instruction: str
    distance_meters: float
    duration_seconds: int
    start_location: Waypoint
    end_location: Waypoint
    maneuver: str
    voice_instruction: Optional[str] = None

class Route(BaseModel):
    route_id: str
    distance_meters: float
    duration_seconds: int
    traffic_duration_seconds: Optional[int] = None
    steps: List[NavigationStep]
    polyline: str
    travel_mode: TravelMode
    preference: RoutePreference

# Database connections
redis_client = None
postgres_conn = None

def connect_to_databases():
    """Connect to Redis and PostgreSQL"""
    global redis_client, postgres_conn
    
    try:
        # Connect to Redis
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Connected to Redis")
        
        # Connect to PostgreSQL
        postgres_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        logger.info("✅ Connected to PostgreSQL")
        
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance using Haversine formula"""
    R = 6371  # Earth's radius in km
    
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Navigation & Routing Helper Functions
class NavigationEngine:
    """A* pathfinding and navigation engine"""
    
    def __init__(self):
        # Sample road network for demo (in real implementation, this would come from a graph database)
        self.road_network = self._generate_sample_road_network()
    
    def _generate_sample_road_network(self) -> Dict:
        """Generate sample road network around San Francisco"""
        return {
            "sf_downtown": {"lat": 37.7749, "lng": -122.4194, "name": "San Francisco Downtown"},
            "sf_financial": {"lat": 37.7849, "lng": -122.4094, "name": "Financial District"},
            "sf_mission": {"lat": 37.7649, "lng": -122.4194, "name": "Mission District"},
            "sf_soma": {"lat": 37.7749, "lng": -122.4094, "name": "SOMA"},
            "sf_richmond": {"lat": 37.7749, "lng": -122.4694, "name": "Richmond District"},
            "oakland": {"lat": 37.8044, "lng": -122.2711, "name": "Oakland"},
            "berkeley": {"lat": 37.8715, "lng": -122.2730, "name": "Berkeley"},
            "san_jose": {"lat": 37.3382, "lng": -121.8863, "name": "San Jose"}
        }
    
    def _heuristic(self, node1: Dict, node2: Dict) -> float:
        """Heuristic function for A* (Euclidean distance)"""
        return calculate_distance(node1["lat"], node1["lng"], node2["lat"], node2["lng"])
    
    def _get_neighbors(self, node: str) -> List[str]:
        """Get neighboring nodes (simplified for demo)"""
        # In real implementation, this would query road network graph
        neighbors_map = {
            "sf_downtown": ["sf_financial", "sf_mission", "sf_soma"],
            "sf_financial": ["sf_downtown", "sf_soma", "oakland"],
            "sf_mission": ["sf_downtown", "sf_soma", "san_jose"],
            "sf_soma": ["sf_downtown", "sf_financial", "sf_mission"],
            "sf_richmond": ["sf_downtown"],
            "oakland": ["sf_financial", "berkeley"],
            "berkeley": ["oakland"],
            "san_jose": ["sf_mission"]
        }
        return neighbors_map.get(node, [])
    
    def _find_nearest_node(self, lat: float, lng: float) -> str:
        """Find nearest road network node to coordinates"""
        min_distance = float('inf')
        nearest_node = None
        
        for node_id, node_data in self.road_network.items():
            distance = calculate_distance(lat, lng, node_data["lat"], node_data["lng"])
            if distance < min_distance:
                min_distance = distance
                nearest_node = node_id
        
        return nearest_node
    
    def calculate_route_astar(self, origin: Waypoint, destination: Waypoint, 
                            travel_mode: TravelMode = TravelMode.DRIVING, 
                            include_traffic: bool = True) -> Route:
        """A* pathfinding algorithm for route calculation"""
        start_node = self._find_nearest_node(origin.latitude, origin.longitude)
        end_node = self._find_nearest_node(destination.latitude, destination.longitude)
        
        if start_node == end_node:
            # Same location
            return self._create_direct_route(origin, destination, travel_mode)
        
        # A* Algorithm Implementation
        open_set = []
        heapq.heappush(open_set, (0, start_node))
        came_from = {}
        g_score = {node: float('inf') for node in self.road_network}
        g_score[start_node] = 0
        f_score = {node: float('inf') for node in self.road_network}
        f_score[start_node] = self._heuristic(self.road_network[start_node], self.road_network[end_node])
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current == end_node:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_node)
                path.reverse()
                
                return self._create_route_from_path(path, origin, destination, travel_mode, include_traffic)
            
            for neighbor in self._get_neighbors(current):
                tentative_g_score = g_score[current] + self._heuristic(
                    self.road_network[current], self.road_network[neighbor]
                )
                
                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(
                        self.road_network[neighbor], self.road_network[end_node]
                    )
                    
                    if (f_score[neighbor], neighbor) not in open_set:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        # No path found, return direct route
        return self._create_direct_route(origin, destination, travel_mode)
    
    def _create_direct_route(self, origin: Waypoint, destination: Waypoint, travel_mode: TravelMode) -> Route:
        """Create direct route between two points"""
        distance = calculate_distance(origin.latitude, origin.longitude, 
                                    destination.latitude, destination.longitude) * 1000  # Convert to meters
        
        # Speed estimates by travel mode (km/h)
        speed_map = {
            TravelMode.DRIVING: 50,
            TravelMode.WALKING: 5, 
            TravelMode.CYCLING: 15,
            TravelMode.TRANSIT: 30
        }
        
        speed_kmh = speed_map.get(travel_mode, 50)
        duration = int((distance / 1000) / speed_kmh * 3600)  # seconds
        
        step = NavigationStep(
            instruction=f"Head {self._get_direction(origin, destination)} toward destination",
            distance_meters=distance,
            duration_seconds=duration,
            start_location=origin,
            end_location=destination,
            maneuver="straight",
            voice_instruction=f"Continue straight for {distance/1000:.1f} kilometers"
        )
        
        return Route(
            route_id=str(uuid.uuid4()),
            distance_meters=distance,
            duration_seconds=duration,
            traffic_duration_seconds=int(duration * 1.2) if travel_mode == TravelMode.DRIVING else duration,
            steps=[step],
            polyline=f"{origin.latitude},{origin.longitude}|{destination.latitude},{destination.longitude}",
            travel_mode=travel_mode,
            preference=RoutePreference.FASTEST
        )
    
    def _create_route_from_path(self, path: List[str], origin: Waypoint, destination: Waypoint, 
                              travel_mode: TravelMode, include_traffic: bool) -> Route:
        """Create route from A* path"""
        steps = []
        total_distance = 0
        total_duration = 0
        
        # Speed estimates by travel mode (km/h)
        speed_map = {
            TravelMode.DRIVING: 50,
            TravelMode.WALKING: 5,
            TravelMode.CYCLING: 15, 
            TravelMode.TRANSIT: 30
        }
        speed_kmh = speed_map.get(travel_mode, 50)
        
        # Start from origin to first node
        if path:
            first_node = self.road_network[path[0]]
            start_waypoint = origin
            end_waypoint = Waypoint(latitude=first_node["lat"], longitude=first_node["lng"], name=first_node["name"])
            
            distance = calculate_distance(start_waypoint.latitude, start_waypoint.longitude,
                                        end_waypoint.latitude, end_waypoint.longitude) * 1000
            duration = int((distance / 1000) / speed_kmh * 3600)
            
            steps.append(NavigationStep(
                instruction=f"Start by heading toward {first_node['name']}",
                distance_meters=distance,
                duration_seconds=duration,
                start_location=start_waypoint,
                end_location=end_waypoint,
                maneuver="start",
                voice_instruction=f"Start your journey toward {first_node['name']}"
            ))
            
            total_distance += distance
            total_duration += duration
        
        # Add steps between nodes
        for i in range(len(path) - 1):
            current_node = self.road_network[path[i]]
            next_node = self.road_network[path[i + 1]]
            
            start_waypoint = Waypoint(latitude=current_node["lat"], longitude=current_node["lng"], name=current_node["name"])
            end_waypoint = Waypoint(latitude=next_node["lat"], longitude=next_node["lng"], name=next_node["name"])
            
            distance = calculate_distance(current_node["lat"], current_node["lng"],
                                        next_node["lat"], next_node["lng"]) * 1000
            duration = int((distance / 1000) / speed_kmh * 3600)
            
            steps.append(NavigationStep(
                instruction=f"Continue to {next_node['name']}",
                distance_meters=distance,
                duration_seconds=duration,
                start_location=start_waypoint,
                end_location=end_waypoint,
                maneuver="straight",
                voice_instruction=f"Continue for {distance/1000:.1f} kilometers to {next_node['name']}"
            ))
            
            total_distance += distance
            total_duration += duration
        
        # Final step from last node to destination
        if path:
            last_node = self.road_network[path[-1]]
            start_waypoint = Waypoint(latitude=last_node["lat"], longitude=last_node["lng"], name=last_node["name"])
            
            distance = calculate_distance(last_node["lat"], last_node["lng"],
                                        destination.latitude, destination.longitude) * 1000
            duration = int((distance / 1000) / speed_kmh * 3600)
            
            steps.append(NavigationStep(
                instruction="Arrive at destination",
                distance_meters=distance, 
                duration_seconds=duration,
                start_location=start_waypoint,
                end_location=destination,
                maneuver="arrive",
                voice_instruction="You have arrived at your destination"
            ))
            
            total_distance += distance
            total_duration += duration
        
        polyline_points = [f"{origin.latitude},{origin.longitude}"]
        for node_id in path:
            node = self.road_network[node_id]
            polyline_points.append(f"{node['lat']},{node['lng']}")
        polyline_points.append(f"{destination.latitude},{destination.longitude}")
        
        traffic_duration = total_duration
        if include_traffic and travel_mode == TravelMode.DRIVING:
            # Add 20% for traffic
            traffic_duration = int(total_duration * 1.2)
        
        return Route(
            route_id=str(uuid.uuid4()),
            distance_meters=total_distance,
            duration_seconds=total_duration,
            traffic_duration_seconds=traffic_duration,
            steps=steps,
            polyline="|".join(polyline_points),
            travel_mode=travel_mode,
            preference=RoutePreference.FASTEST
        )
    
    def _get_direction(self, start: Waypoint, end: Waypoint) -> str:
        """Get cardinal direction from start to end"""
        lat_diff = end.latitude - start.latitude
        lng_diff = end.longitude - start.longitude
        
        if abs(lat_diff) > abs(lng_diff):
            return "north" if lat_diff > 0 else "south"
        else:
            return "east" if lng_diff > 0 else "west"

def geohash_encode(lat: float, lng: float, precision: int = 7) -> str:
    """Simple geohash implementation"""
    base32 = '0123456789bcdefghjkmnpqrstuvwxyz'
    lat_range = [-90.0, 90.0]
    lng_range = [-180.0, 180.0]
    
    bits = []
    is_lat = False
    
    while len(bits) < precision * 5:
        if is_lat:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                bits.append(1)
                lat_range[0] = mid
            else:
                bits.append(0)
                lat_range[1] = mid
        else:
            mid = (lng_range[0] + lng_range[1]) / 2
            if lng >= mid:
                bits.append(1)
                lng_range[0] = mid
            else:
                bits.append(0)
                lng_range[1] = mid
        is_lat = not is_lat
    
    geohash = ''
    for i in range(0, len(bits), 5):
        chunk = bits[i:i+5]
        while len(chunk) < 5:
            chunk.append(0)
        index = sum(chunk[j] * (2 ** (4-j)) for j in range(5))
        geohash += base32[index]
    
    return geohash[:precision]

@app.on_event("startup")
async def startup_event():
    """Initialize database connections"""
    logger.info("🚀 Starting Simple API Gateway...")
    if not connect_to_databases():
        logger.error("❌ Failed to connect to databases")
        raise Exception("Database connection failed")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "healthy" if redis_client else "disconnected"
    postgres_status = "healthy" if postgres_conn else "disconnected"
    
    if redis_client:
        try:
            redis_client.ping()
        except:
            redis_status = "error"
    
    if postgres_conn:
        try:
            with postgres_conn.cursor() as cur:
                cur.execute("SELECT 1")
        except:
            postgres_status = "error"
    
    return {
        "status": "healthy" if redis_status == "healthy" and postgres_status == "healthy" else "degraded",
        "services": {
            "redis": redis_status,
            "postgres": postgres_status
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/location/batch")
async def update_location_batch(batch: LocationBatch):
    """Feature 1 & 8: Real-time Location Tracking + Batch Updates"""
    start_time = time.time()
    batch_id = str(uuid.uuid4())
    
    try:
        processed_locations = []
        
        for location in batch.locations:
            timestamp = location.timestamp or datetime.utcnow().isoformat()
            user_key = f"anon_{batch.user_id[:8]}" if batch.anonymous else batch.user_id
            
            location_data = {
                'user_id': user_key,
                'latitude': str(location.latitude),
                'longitude': str(location.longitude),
                'timestamp': timestamp,
                'accuracy': str(location.accuracy),
                'speed': str(location.speed),
                'heading': str(location.heading),
                'altitude': str(location.altitude),
                'batch_id': batch_id,
                'encrypted': str(batch.anonymous)
            }
            
            # Store in Redis (current location)
            redis_client.hset(f"current_location:{user_key}", mapping=location_data)
            
            # Store in Redis (location history)
            redis_client.lpush(f"location_history:{user_key}", json.dumps(location_data))
            redis_client.ltrim(f"location_history:{user_key}", 0, 1000)  # Keep last 1000
            
            # Store geohash for spatial indexing
            geohash = geohash_encode(location.latitude, location.longitude)
            redis_client.sadd(f"geohash:{geohash}", user_key)
            redis_client.hset(f"user_geohash:{user_key}", "geohash", geohash)
            
            processed_locations.append(location_data)
        
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'batch_id': batch_id,
            'user_id': batch.user_id,
            'processed_count': len(processed_locations),
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'success',
            'processing_time_ms': processing_time,
            'database': 'redis',
            'locations': processed_locations[:5]  # Return first 5 for brevity
        }
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/location/current/{user_id}")
async def get_current_location(user_id: str):
    """Feature 2: Current Location Retrieval (<50ms response time)"""
    start_time = time.time()
    
    try:
        location_data = redis_client.hgetall(f"current_location:{user_id}")
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if not location_data:
            return {
                'user_id': user_id,
                'found': False,
                'response_time_ms': response_time,
                'database': 'redis'
            }
        
        # Convert Redis strings back to proper types
        location_data['latitude'] = float(location_data['latitude'])
        location_data['longitude'] = float(location_data['longitude'])
        location_data['accuracy'] = float(location_data['accuracy'])
        
        return {
            'user_id': user_id,
            'found': True,
            'location': location_data,
            'response_time_ms': response_time,
            'is_fast': response_time < 50,
            'database': 'redis'
        }
        
    except Exception as e:
        logger.error(f"Current location error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/location/history/{user_id}")
async def get_location_history(
    user_id: str, 
    limit: int = 50,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Feature 3: Location History Queries (Time-based filtering)"""
    try:
        history_data = redis_client.lrange(f"location_history:{user_id}", 0, limit-1)
        
        locations = []
        for item in history_data:
            location = json.loads(item)
            
            # Apply time filtering if provided
            if start_time or end_time:
                loc_time = datetime.fromisoformat(location['timestamp'].replace('Z', '+00:00'))
                
                if start_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    if loc_time < start_dt:
                        continue
                
                if end_time:
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    if loc_time > end_dt:
                        continue
            
            locations.append(location)
        
        return {
            'user_id': user_id,
            'locations': locations,
            'count': len(locations),
            'filtered': bool(start_time or end_time),
            'database': 'redis'
        }
        
    except Exception as e:
        logger.error(f"Location history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/location/nearby/{user_id}")
async def find_nearby_users(user_id: str, radius_km: float = 1.0, limit: int = 50):
    """Feature 4: Proximity Search (Find nearby users)"""
    try:
        # Get user's current location
        current_location = redis_client.hgetall(f"current_location:{user_id}")
        if not current_location:
            return {
                'user_id': user_id,
                'nearby_users': [],
                'error': 'User location not found'
            }
        
        user_lat = float(current_location['latitude'])
        user_lng = float(current_location['longitude'])
        user_geohash = redis_client.hget(f"user_geohash:{user_id}", "geohash")
        
        # Find users in the same and neighboring geohash cells
        nearby_users = []
        
        # Get users from same geohash cell and neighboring cells
        for precision in range(4, 7):  # Check different precision levels
            check_geohash = geohash_encode(user_lat, user_lng, precision)
            users_in_cell = redis_client.smembers(f"geohash:{check_geohash}")
            
            for other_user in users_in_cell:
                if other_user == user_id:
                    continue
                    
                other_location = redis_client.hgetall(f"current_location:{other_user}")
                if not other_location:
                    continue
                
                distance = calculate_distance(
                    user_lat, user_lng,
                    float(other_location['latitude']),
                    float(other_location['longitude'])
                )
                
                if distance <= radius_km:
                    nearby_users.append({
                        'user_id': other_user,
                        'distance_km': round(distance, 3),
                        'location': {
                            'latitude': float(other_location['latitude']),
                            'longitude': float(other_location['longitude']),
                            'timestamp': other_location['timestamp']
                        }
                    })
        
        # Sort by distance and limit
        nearby_users.sort(key=lambda x: x['distance_km'])
        nearby_users = nearby_users[:limit]
        
        return {
            'user_id': user_id,
            'search_center': {'latitude': user_lat, 'longitude': user_lng},
            'radius_km': radius_km,
            'nearby_users': nearby_users,
            'count': len(nearby_users),
            'database': 'redis'
        }
        
    except Exception as e:
        logger.error(f"Nearby users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/location/geohash/{user_id}")
async def get_geohash_info(user_id: str):
    """Feature 5: Geospatial Indexing (Geohashing)"""
    try:
        current_location = redis_client.hgetall(f"current_location:{user_id}")
        if not current_location:
            return {
                'user_id': user_id,
                'error': 'User location not found'
            }
        
        lat = float(current_location['latitude'])
        lng = float(current_location['longitude'])
        
        # Generate geohashes at different precisions
        geohashes = {}
        for precision in range(3, 8):
            geohashes[f'precision_{precision}'] = geohash_encode(lat, lng, precision)
        
        # Get users in same cell
        current_geohash = geohashes['precision_7']
        users_in_cell = redis_client.smembers(f"geohash:{current_geohash}")
        
        return {
            'user_id': user_id,
            'location': {'latitude': lat, 'longitude': lng},
            'geohashes': geohashes,
            'current_cell': current_geohash,
            'users_in_same_cell': [u for u in users_in_cell if u != user_id],
            'cell_population': len(users_in_cell),
            'database': 'redis'
        }
        
    except Exception as e:
        logger.error(f"Geohash info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/location/share")
async def share_location(user_id: str, share_with: List[str], duration_minutes: int = 60):
    """Feature 6: Location Sharing"""
    try:
        current_location = redis_client.hgetall(f"current_location:{user_id}")
        if not current_location:
            return {
                'user_id': user_id,
                'error': 'User location not found'
            }
        
        sharing_id = str(uuid.uuid4())
        expiry_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        share_data = {
            'sharing_user': user_id,
            'shared_with': json.dumps(share_with),
            'location': json.dumps(current_location),
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expiry_time.isoformat(),
            'active': 'true'
        }
        
        # Store sharing info in Redis with expiry
        redis_client.hset(f"location_share:{sharing_id}", mapping=share_data)
        redis_client.expire(f"location_share:{sharing_id}", duration_minutes * 60)
        
        return {
            'sharing_id': sharing_id,
            'user_id': user_id,
            'shared_with': share_with,
            'expires_at': expiry_time.isoformat(),
            'share_url': f'https://maps.example.com/shared/{sharing_id}',
            'status': 'active',
            'database': 'redis'
        }
        
    except Exception as e:
        logger.error(f"Location sharing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/system/stats")
async def get_system_stats():
    """System statistics"""
    try:
        # Redis stats
        redis_info = redis_client.info()
        
        # Count users and locations
        user_count = len(redis_client.keys("current_location:*"))
        total_locations = sum(redis_client.llen(key) for key in redis_client.keys("location_history:*"))
        
        return {
            'database_stats': {
                'redis_connected_clients': redis_info.get('connected_clients', 0),
                'redis_used_memory': redis_info.get('used_memory_human', '0'),
                'redis_total_commands': redis_info.get('total_commands_processed', 0),
            },
            'application_stats': {
                'active_users': user_count,
                'total_location_records': total_locations,
                'geohash_cells': len(redis_client.keys("geohash:*"))
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🗺️ Starting Simple API Gateway with Real Databases")
    print("==================================================")
    print("🔗 Connects to:")
    print(f"   📊 Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"   🗄️  PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}")
    print("🎯 API: http://localhost:8080")
    print("📖 Docs: http://localhost:8080/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")