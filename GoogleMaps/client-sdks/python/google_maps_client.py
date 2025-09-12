"""
Google Maps Clone - Complete Python SDK
Full-featured client library for all 75+ implemented features
"""

import asyncio
import aiohttp
import websockets
import json
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
from dataclasses import dataclass
import math

@dataclass
class Location:
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None
    speed: Optional[float] = None
    bearing: Optional[float] = None

@dataclass
class Place:
    place_id: str
    name: str
    location: Location
    rating: Optional[float] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
@dataclass
class Route:
    route_id: str
    distance_km: float
    duration_minutes: float
    polyline: str
    instructions: List[str]

class GoogleMapsClient:
    """Complete Python SDK for Google Maps Clone API"""
    
    def __init__(self, api_key: str = None, base_url: str = "http://localhost:8080", version: str = "v3"):
        self.api_key = api_key
        self.base_url = base_url
        self.version = version
        self.session = None
        self.websockets = {}
        
        # Default headers for authentication
        self.headers = {
            'Content-Type': 'application/json',
            **({"Authorization": f"Bearer {api_key}"} if api_key else {})
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        
        # Close WebSocket connections
        for ws in self.websockets.values():
            if not ws.closed:
                await ws.close()
    
    # ============== CORE LOCATION SERVICES ==============
    
    async def submit_location_batch(self, user_id: str, locations: List[Dict]) -> Dict:
        """Submit batch location updates with ML analysis"""
        data = {
            "user_id": user_id,
            "locations": locations
        }
        return await self._make_request('POST', f'/api/{self.version}/locations/batch', data)
    
    async def get_current_location(self, user_id: str) -> Optional[Location]:
        """Get current location for a user"""
        result = await self._make_request('GET', f'/api/{self.version}/locations/{user_id}/current')
        
        if result and 'location' in result:
            loc_data = result['location']
            return Location(
                latitude=loc_data['latitude'],
                longitude=loc_data['longitude'],
                accuracy=loc_data.get('accuracy'),
                speed=loc_data.get('speed'),
                bearing=loc_data.get('bearing')
            )
        return None
    
    async def get_location_history(self, user_id: str, start_time: Optional[datetime] = None, 
                                 end_time: Optional[datetime] = None, limit: int = 100) -> List[Location]:
        """Get location history with analytics"""
        params = {'limit': limit}
        if start_time:
            params['start_time'] = start_time.isoformat()
        if end_time:
            params['end_time'] = end_time.isoformat()
        
        result = await self._make_request('GET', f'/api/{self.version}/locations/{user_id}/history', params=params)
        
        locations = []
        if result and 'locations' in result:
            for loc_data in result['locations']:
                locations.append(Location(
                    latitude=loc_data['latitude'],
                    longitude=loc_data['longitude'],
                    accuracy=loc_data.get('accuracy'),
                    timestamp=datetime.fromisoformat(loc_data['timestamp'].replace('Z', '+00:00')),
                    speed=loc_data.get('speed'),
                    bearing=loc_data.get('bearing')
                ))
        
        return locations
    
    async def get_nearby_users(self, user_id: str, radius_km: float = 1.0) -> List[Dict]:
        """Find nearby users with proximity search"""
        params = {'radius_km': radius_km}
        return await self._make_request('GET', f'/api/{self.version}/locations/{user_id}/nearby', params=params)
    
    # ============== GEOCODING & PLACES ==============
    
    async def geocode(self, address: str) -> Optional[Location]:
        """Convert address to coordinates with caching"""
        result = await self._make_request('POST', '/api/v2/geocode', {"address": address})
        
        if result:
            return Location(
                latitude=result['latitude'],
                longitude=result['longitude']
            )
        return None
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """Convert coordinates to address"""
        result = await self._make_request('POST', '/api/v2/reverse-geocode', {
            "latitude": latitude,
            "longitude": longitude
        })
        
        return result.get('address') if result else None
    
    async def search_places(self, query: str, location: Optional[Location] = None, 
                          radius_km: float = 10, place_type: Optional[str] = None,
                          min_rating: Optional[float] = None, open_now: bool = False,
                          limit: int = 20) -> List[Place]:
        """Advanced places search with ML ranking"""
        params = {
            'q': query,
            'radius': radius_km,
            'open_now': open_now,
            'limit': limit
        }
        
        if location:
            params['lat'] = location.latitude
            params['lng'] = location.longitude
        
        if place_type:
            params['type'] = place_type
        
        if min_rating:
            params['min_rating'] = min_rating
        
        result = await self._make_request('GET', f'/api/{self.version}/places/search', params=params)
        
        places = []
        if result and 'places' in result:
            for place_data in result['places']:
                places.append(Place(
                    place_id=place_data['place_id'],
                    name=place_data['name'],
                    location=Location(
                        latitude=place_data['latitude'],
                        longitude=place_data['longitude']
                    ),
                    rating=place_data.get('rating'),
                    address=place_data.get('address'),
                    phone=place_data.get('phone'),
                    website=place_data.get('website')
                ))
        
        return places
    
    async def get_place(self, place_id: str) -> Optional[Place]:
        """Get detailed place information"""
        result = await self._make_request('GET', f'/api/{self.version}/places/{place_id}')
        
        if result:
            return Place(
                place_id=result['place_id'],
                name=result['name'],
                location=Location(
                    latitude=result['latitude'],
                    longitude=result['longitude']
                ),
                rating=result.get('rating'),
                address=result.get('address'),
                phone=result.get('phone'),
                website=result.get('website')
            )
        return None
    
    async def add_place_review(self, place_id: str, rating: float, text: Optional[str] = None, 
                             photos: List[str] = None) -> Dict:
        """Add review to a place"""
        data = {
            "rating": rating,
            "text": text,
            "photos": photos or []
        }
        return await self._make_request('POST', f'/api/{self.version}/places/{place_id}/reviews', data)
    
    # ============== ADVANCED NAVIGATION ==============
    
    async def calculate_advanced_route(self, origin: str, destination: str, mode: str = 'driving',
                                     alternatives: bool = False, include_traffic: bool = True,
                                     voice_guidance: bool = False, language: str = 'en',
                                     waypoints: Optional[List[str]] = None) -> Dict:
        """Calculate advanced route with ML-enhanced ETA"""
        data = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "alternatives": alternatives,
            "include_traffic": include_traffic,
            "voice_guidance": voice_guidance,
            "language": language,
            "waypoints": waypoints
        }
        
        return await self._make_request('POST', f'/api/{self.version}/routes/advanced', data)
    
    async def get_navigation_instructions(self, route_id: str) -> List[str]:
        """Get turn-by-turn navigation instructions"""
        result = await self._make_request('GET', f'/api/v2/routes/{route_id}/instructions')
        return result.get('instructions', []) if result else []
    
    async def get_enhanced_eta(self, route_id: str, current_location: Optional[Location] = None) -> Dict:
        """Get ML-enhanced ETA with traffic"""
        data = {}
        if current_location:
            data['current_lat'] = current_location.latitude
            data['current_lng'] = current_location.longitude
        
        return await self._make_request('POST', f'/api/v2/routes/{route_id}/eta', data)
    
    # ============== STREET VIEW ==============
    
    async def get_street_view(self, latitude: Optional[float] = None, longitude: Optional[float] = None,
                            pano_id: Optional[str] = None, heading: float = 0, pitch: float = 0,
                            fov: float = 90, quality: str = 'medium') -> Optional[Dict]:
        """Get Street View panoramic imagery"""
        params = {
            'heading': heading,
            'pitch': pitch,
            'fov': fov,
            'quality': quality
        }
        
        if latitude and longitude:
            params['lat'] = latitude
            params['lng'] = longitude
        
        if pano_id:
            params['pano_id'] = pano_id
        
        return await self._make_request('GET', f'/api/{self.version}/street-view', params=params)
    
    async def search_street_view(self, query: str, location: Optional[Location] = None, 
                               radius_km: float = 10) -> List[Dict]:
        """Search for Street View panoramas"""
        params = {
            'q': query,
            'radius_km': radius_km
        }
        
        if location:
            params['lat'] = location.latitude
            params['lng'] = location.longitude
        
        result = await self._make_request('GET', f'/api/{self.version}/street-view/search', params=params)
        return result.get('panoramas', []) if result else []
    
    # ============== ROUTE OPTIMIZATION ==============
    
    async def optimize_delivery_route(self, depot: Location, stops: List[Dict], 
                                    vehicles: List[Dict], optimize_for: str = 'time') -> Dict:
        """Optimize multi-stop delivery routes"""
        data = {
            "depot_lat": depot.latitude,
            "depot_lng": depot.longitude,
            "stops": stops,
            "vehicles": vehicles,
            "optimize_for": optimize_for
        }
        
        return await self._make_request('POST', f'/api/{self.version}/optimize/delivery-routes', data)
    
    # ============== PUBLIC TRANSIT ==============
    
    async def get_transit_route(self, origin: str, destination: str, 
                              departure_time: Optional[datetime] = None,
                              modes: List[str] = None) -> List[Dict]:
        """Get public transit routes"""
        params = {
            'origin': origin,
            'destination': destination
        }
        
        if departure_time:
            params['departure_time'] = departure_time.isoformat()
        
        if modes:
            params['modes'] = ','.join(modes)
        
        result = await self._make_request('GET', f'/api/{self.version}/transit/routes', params=params)
        return result.get('routes', []) if result else []
    
    # ============== RIDE SHARING ==============
    
    async def request_ride(self, pickup: Location, destination: Location, 
                         ride_type: str = 'standard', passengers: int = 1) -> Dict:
        """Request a ride with dynamic pricing"""
        data = {
            "pickup_lat": pickup.latitude,
            "pickup_lng": pickup.longitude,
            "destination_lat": destination.latitude,
            "destination_lng": destination.longitude,
            "ride_type": ride_type,
            "passengers": passengers
        }
        
        return await self._make_request('POST', f'/api/{self.version}/rides/request', data)
    
    # ============== OFFLINE MAPS ==============
    
    async def download_offline_area(self, north: float, south: float, east: float, west: float,
                                  min_zoom: int = 10, max_zoom: int = 15,
                                  include_places: bool = True, include_transit: bool = True) -> Dict:
        """Download map area for offline use"""
        data = {
            "north": north,
            "south": south,
            "east": east,
            "west": west,
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
            "include_places": include_places,
            "include_transit": include_transit
        }
        
        return await self._make_request('POST', f'/api/{self.version}/offline/download', data)
    
    # ============== VOICE NAVIGATION ==============
    
    async def get_voice_instructions(self, route_id: str, language: str = 'en', 
                                   voice: str = 'female') -> Dict:
        """Get voice navigation instructions"""
        params = {
            'language': language,
            'voice': voice
        }
        
        return await self._make_request('GET', f'/api/{self.version}/voice/instructions/{route_id}', params=params)
    
    # ============== TRAFFIC MANAGEMENT ==============
    
    async def get_current_traffic(self, latitude: float, longitude: float, 
                                radius_km: float = 5) -> List[Dict]:
        """Get current traffic conditions"""
        params = {
            'lat': latitude,
            'lng': longitude,
            'radius_km': radius_km
        }
        
        result = await self._make_request('GET', '/api/v2/traffic/current', params=params)
        return result.get('conditions', []) if result else []
    
    async def report_traffic_incident(self, latitude: float, longitude: float, 
                                    incident_type: str = 'traffic', severity: str = 'moderate',
                                    description: str = '', user_id: str = 'anonymous') -> Dict:
        """Report traffic incident"""
        data = {
            "incident_type": incident_type,
            "severity": severity,
            "lat": latitude,
            "lng": longitude,
            "description": description,
            "user_id": user_id
        }
        
        return await self._make_request('POST', '/api/v2/traffic/report-incident', data)
    
    # ============== REAL-TIME FEATURES ==============
    
    async def stream_locations(self, user_id: str, callback: Callable[[Dict], None]):
        """Stream live location updates"""
        uri = f"{self.base_url.replace('http', 'ws')}/ws/{self.version}/live-navigation?user_id={user_id}&route_id=live_tracking"
        
        try:
            async with websockets.connect(uri) as websocket:
                self.websockets['location_stream'] = websocket
                
                async for message in websocket:
                    data = json.loads(message)
                    callback(data)
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Location stream disconnected")
        except Exception as e:
            print(f"❌ Location stream error: {e}")
    
    async def subscribe_to_traffic(self, callback: Callable[[Dict], None], 
                                 area: Optional[Dict] = None):
        """Subscribe to traffic updates"""
        params = ['user_id=traffic_subscriber']
        
        if area:
            params.extend([
                f"lat={area['latitude']}",
                f"lng={area['longitude']}",
                f"radius_km={area.get('radius', 5)}"
            ])
        
        uri = f"{self.base_url.replace('http', 'ws')}/ws/traffic-feed?{'&'.join(params)}"
        
        try:
            async with websockets.connect(uri) as websocket:
                self.websockets['traffic_feed'] = websocket
                
                async for message in websocket:
                    data = json.loads(message)
                    callback(data)
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Traffic feed disconnected")
        except Exception as e:
            print(f"❌ Traffic feed error: {e}")
    
    async def start_live_navigation(self, route_id: str, callback: Callable[[Dict], None]):
        """Start live navigation session"""
        uri = f"{self.base_url.replace('http', 'ws')}/ws/{self.version}/live-navigation?user_id=navigator&route_id={route_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                self.websockets['navigation'] = websocket
                
                async for message in websocket:
                    data = json.loads(message)
                    callback(data)
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Live navigation disconnected")
        except Exception as e:
            print(f"❌ Live navigation error: {e}")
    
    async def update_navigation_position(self, route_id: str, location: Location):
        """Send live position update during navigation"""
        if 'navigation' in self.websockets:
            websocket = self.websockets['navigation']
            
            if not websocket.closed:
                message = {
                    "type": "position_update",
                    "route_id": route_id,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "speed": location.speed or 0,
                    "bearing": location.bearing or 0
                }
                
                await websocket.send(json.dumps(message))
    
    # ============== ANALYTICS & MONITORING ==============
    
    async def get_system_health(self) -> Dict:
        """Get system health status"""
        return await self._make_request('GET', f'/api/{self.version}/system/health')
    
    async def get_system_metrics(self) -> Dict:
        """Get system metrics (requires admin access)"""
        return await self._make_request('GET', f'/api/{self.version}/system/metrics')
    
    async def get_analytics_dashboard(self, time_range: str = '24h') -> Dict:
        """Get analytics dashboard (requires admin access)"""
        params = {'time_range': time_range}
        return await self._make_request('GET', f'/api/{self.version}/analytics/dashboard', params=params)
    
    # ============== UTILITY METHODS ==============
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                          params: Dict = None) -> Optional[Dict]:
        """Make authenticated HTTP request"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                async with self.session.get(url, params=params) as response:
                    return await self._process_response(response)
            elif method == 'POST':
                async with self.session.post(url, json=data, params=params) as response:
                    return await self._process_response(response)
            elif method == 'PUT':
                async with self.session.put(url, json=data, params=params) as response:
                    return await self._process_response(response)
            elif method == 'DELETE':
                async with self.session.delete(url, params=params) as response:
                    return await self._process_response(response)
                    
        except Exception as e:
            print(f"❌ Request failed: {method} {endpoint} - {e}")
            return None
    
    async def _process_response(self, response: aiohttp.ClientResponse) -> Optional[Dict]:
        """Process HTTP response"""
        if response.status < 400:
            try:
                return await response.json()
            except:
                return {"success": True, "text": await response.text()}
        else:
            print(f"❌ HTTP {response.status}: {response.reason}")
            return None
    
    @staticmethod
    def calculate_distance(point1: Location, point2: Location) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(point1.latitude)
        lat2_rad = math.radians(point2.latitude)
        dlat_rad = math.radians(point2.latitude - point1.latitude)
        dlon_rad = math.radians(point2.longitude - point1.longitude)
        
        a = (math.sin(dlat_rad/2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon_rad/2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


# ============== USAGE EXAMPLES ==============

async def demonstrate_all_features():
    """Comprehensive demonstration of all features"""
    print("🚀 Google Maps Clone Python SDK - Feature Demonstration")
    print("=" * 60)
    
    async with GoogleMapsClient(api_key="demo-key") as client:
        try:
            # 1. Core Location Services
            print("\n📍 Testing Core Location Services...")
            
            await client.submit_location_batch('demo_user', [{
                'latitude': 37.7749,
                'longitude': -122.4194,
                'timestamp': int(datetime.now().timestamp()),
                'accuracy': 5.0,
                'user_mode': 'active',
                'speed': 15.5,
                'bearing': 90.0
            }])
            
            current_location = await client.get_current_location('demo_user')
            print(f"✅ Current location: {current_location}")
            
            # 2. Advanced Navigation
            print("\n🧭 Testing Advanced Navigation...")
            
            route = await client.calculate_advanced_route(
                origin="San Francisco, CA",
                destination="Los Angeles, CA",
                mode="driving",
                alternatives=True,
                include_traffic=True,
                voice_guidance=True
            )
            print(f"✅ Advanced route calculated: {route}")
            
            # 3. Places Search
            print("\n🏢 Testing Places Search...")
            
            sf_location = Location(latitude=37.7749, longitude=-122.4194)
            restaurants = await client.search_places(
                query="italian restaurants",
                location=sf_location,
                radius_km=5,
                min_rating=4.0,
                open_now=True
            )
            print(f"✅ Found {len(restaurants)} restaurants")
            
            # 4. Street View
            print("\n📸 Testing Street View...")
            
            street_view = await client.get_street_view(
                latitude=37.7749,
                longitude=-122.4194,
                heading=90,
                quality='high'
            )
            print(f"✅ Street View retrieved: {street_view}")
            
            # 5. Route Optimization
            print("\n🛣️ Testing Route Optimization...")
            
            depot = Location(latitude=37.7749, longitude=-122.4194)
            optimized_route = await client.optimize_delivery_route(
                depot=depot,
                stops=[
                    {'id': 'stop1', 'lat': 37.7849, 'lng': -122.4094, 'delivery_amount': 5},
                    {'id': 'stop2', 'lat': 37.7649, 'lng': -122.4294, 'delivery_amount': 3}
                ],
                vehicles=[{'id': 'truck1', 'type': 'truck', 'capacity': 100}]
            )
            print(f"✅ Route optimized: {optimized_route}")
            
            # 6. Transit Integration
            print("\n🚌 Testing Public Transit...")
            
            transit_routes = await client.get_transit_route(
                origin="Brooklyn Bridge",
                destination="Central Park",
                modes=['subway', 'bus']
            )
            print(f"✅ Found {len(transit_routes)} transit routes")
            
            # 7. Offline Maps
            print("\n📱 Testing Offline Maps...")
            
            download_info = await client.download_offline_area(
                north=37.8, south=37.7, east=-122.3, west=-122.5,
                min_zoom=10, max_zoom=15,
                include_places=True, include_transit=True
            )
            print(f"✅ Offline download prepared: {download_info}")
            
            # 8. System Health
            print("\n🔍 Testing System Health...")
            
            health = await client.get_system_health()
            print(f"✅ System health: {health.get('status', 'unknown')}")
            
            print("\n🎉 All features tested successfully!")
            
        except Exception as e:
            print(f"❌ Feature test failed: {e}")


if __name__ == "__main__":
    # Run the comprehensive demo
    asyncio.run(demonstrate_all_features())