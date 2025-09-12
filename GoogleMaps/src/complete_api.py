"""
Complete Google Maps Clone API - Master Service
Integrates all features: navigation, places, street view, transit, ride sharing, etc.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple, Union
from datetime import datetime, timedelta
import uuid
import logging
import asyncio
from contextlib import asynccontextmanager
import json

# Import all services
from .database import DatabaseManager
from .models import LocationUpdate, LocationBatch, UserCurrentLocation, LocationHistory
from .batch_processor import BatchProcessor
from .config import settings

# Enhanced services
from .geocoding import GeocodingService, GeocodedLocation
from .navigation import RoutingService, Route, TravelMode, NavigationInstruction
from .websocket_manager import manager, ChannelType
from .traffic import TrafficService, TrafficCondition, TrafficIncident
from .map_tiles import MapTileService, TileFormat

# Advanced services
from .ml_eta_service import MLETAService, ETAFeatures, ETAPrediction
from .places_service import PlacesService, Place, PlaceType, Review
from .multi_stop_optimizer import MultiStopOptimizer, Stop, Vehicle, OptimizationConstraints
from .street_view_service import StreetViewService, StreetViewQuery, ImageQuality
from .analytics_service import AnalyticsService
from .offline_service import OfflineMapService
from .voice_service import VoiceNavigationService
from .transit_service import TransitService
from .ride_service import RideShareService
from .security_service import SecurityService
from .monitoring_service import MonitoringService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
services = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Complete application lifecycle management"""
    global services
    
    logger.info("🚀 Starting Complete Google Maps Clone Service...")
    
    try:
        # Initialize core infrastructure
        services['db'] = DatabaseManager(settings.cassandra_hosts, settings.cassandra_keyspace)
        await services['db'].connect()
        
        services['batch_processor'] = BatchProcessor(services['db'])
        
        # Initialize all enhanced services
        services['geocoding'] = GeocodingService(settings.redis_host, settings.redis_port)
        services['routing'] = RoutingService(settings.graph_data_path, settings.redis_host, settings.redis_port)
        services['traffic'] = TrafficService(services['db'])
        services['map_tiles'] = MapTileService(settings.tile_storage_path, cache_enabled=True)
        
        # Initialize ML and advanced services
        services['ml_eta'] = MLETAService(settings.redis_host, settings.redis_port)
        services['places'] = PlacesService(settings.elasticsearch_host, settings.redis_host, settings.redis_port)
        services['optimizer'] = MultiStopOptimizer(settings.redis_host, settings.redis_port)
        services['street_view'] = StreetViewService(settings.streetview_storage_path, settings.google_api_key, settings.redis_host, settings.redis_port)
        
        # Initialize business services
        services['analytics'] = AnalyticsService(services['db'])
        services['offline'] = OfflineMapService(settings.tile_storage_path)
        services['voice'] = VoiceNavigationService()
        services['transit'] = TransitService(services['db'])
        services['ride_share'] = RideShareService(services['db'])
        services['security'] = SecurityService(settings.jwt_secret_key)
        services['monitoring'] = MonitoringService(services['db'])
        
        # Initialize all services
        for service_name, service in services.items():
            if hasattr(service, 'initialize'):
                await service.initialize()
                logger.info(f"✅ {service_name} service initialized")
        
        logger.info("🎉 All services started successfully!")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start services: {e}")
        raise
    
    # Shutdown
    logger.info("🔄 Shutting down services...")
    for service_name, service in services.items():
        try:
            if hasattr(service, 'close'):
                await service.close()
                logger.info(f"✅ {service_name} service closed")
        except Exception as e:
            logger.error(f"❌ Error closing {service_name}: {e}")
    
    logger.info("🏁 Shutdown complete")

app = FastAPI(
    title="Google Maps Clone - Complete API",
    description="Full-featured mapping service with all advanced capabilities",
    version="3.0.0",
    lifespan=lifespan
)

# Security
security = HTTPBearer(auto_error=False)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== AUTHENTICATION ==============

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Get current authenticated user"""
    if not credentials:
        return {"user_id": "anonymous", "permissions": ["read"]}
    
    try:
        user = await services['security'].verify_token(credentials.credentials)
        return user
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        return {"user_id": "anonymous", "permissions": ["read"]}

# ============== CORE LOCATION ENDPOINTS ==============

@app.post("/api/v3/locations/batch")
async def submit_location_batch_v3(
    batch: LocationBatch,
    background_tasks: BackgroundTasks,
    user: Dict = Depends(get_current_user)
):
    """Enhanced batch location submission with ML analysis"""
    try:
        batch_id = str(uuid.uuid4())
        
        # Security check
        if not await services['security'].check_rate_limit(user['user_id'], 'location_batch'):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Process with all enhancements
        background_tasks.add_task(
            services['batch_processor'].process_location_batch,
            batch_id, batch.user_id, batch.locations
        )
        
        # ML traffic analysis
        background_tasks.add_task(
            services['traffic'].analyze_location_batch,
            batch.user_id, batch.locations
        )
        
        # Real-time updates
        if batch.locations:
            latest = batch.locations[-1]
            background_tasks.add_task(
                manager.send_location_update,
                batch.user_id,
                {
                    "latitude": latest.latitude,
                    "longitude": latest.longitude,
                    "speed": latest.speed,
                    "bearing": latest.bearing
                }
            )
        
        # Analytics tracking
        background_tasks.add_task(
            services['analytics'].track_location_event,
            user['user_id'], 'batch_upload', len(batch.locations)
        )
        
        return {
            "status": "accepted",
            "batch_id": batch_id,
            "processed_count": len(batch.locations),
            "ml_analysis": "enabled",
            "real_time": "enabled"
        }
        
    except Exception as e:
        logger.error(f"Enhanced batch processing error: {e}")
        raise HTTPException(status_code=500, detail="Processing failed")

# ============== ML-ENHANCED NAVIGATION ==============

class AdvancedRouteRequest(BaseModel):
    origin: str
    destination: str
    mode: TravelMode = TravelMode.DRIVING
    waypoints: Optional[List[str]] = None
    alternatives: bool = False
    avoid_tolls: bool = False
    avoid_highways: bool = False
    departure_time: Optional[datetime] = None
    optimize_for: str = "time"  # time, distance, cost
    include_traffic: bool = True
    voice_guidance: bool = False
    language: str = "en"

@app.post("/api/v3/routes/advanced")
async def calculate_advanced_route(
    request: AdvancedRouteRequest,
    user: Dict = Depends(get_current_user)
):
    """Advanced route calculation with ML-based ETA and optimizations"""
    try:
        # Geocode locations
        origin_coords = await _parse_location(request.origin, services['geocoding'])
        dest_coords = await _parse_location(request.destination, services['geocoding'])
        
        if not origin_coords or not dest_coords:
            raise HTTPException(status_code=400, detail="Invalid locations")
        
        # Calculate base route
        routes = []
        if request.alternatives:
            routes = await services['routing'].get_route_alternatives(
                origin_coords, dest_coords, request.mode, max_alternatives=3
            )
        else:
            route = await services['routing'].find_route(
                origin_coords, dest_coords, request.mode,
                avoid_highways=request.avoid_highways
            )
            if route:
                routes = [route]
        
        if not routes:
            raise HTTPException(status_code=404, detail="No routes found")
        
        # Enhance routes with ML predictions
        enhanced_routes = []
        for route in routes:
            # ML-based ETA prediction
            now = datetime.now()
            eta_features = ETAFeatures(
                distance_km=route.total_distance_km,
                base_duration_minutes=route.total_duration_minutes,
                hour_of_day=now.hour,
                day_of_week=now.weekday(),
                month=now.month,
                historical_avg_speed=50.0,
                current_traffic_factor=await services['traffic'].get_traffic_factor(route.route_id),
                weather_condition="clear",
                road_type_highway_pct=0.3,
                road_type_arterial_pct=0.4,
                road_type_local_pct=0.3,
                construction_zones=0,
                active_incidents=0,
                is_holiday=False,
                is_rush_hour=7 <= now.hour <= 9 or 17 <= now.hour <= 19,
                population_density=1000.0,
                event_impact_score=0.0
            )
            
            ml_eta = await services['ml_eta'].predict_eta(route.route_id, eta_features)
            
            # Add voice instructions if requested
            voice_instructions = []
            if request.voice_guidance:
                instructions = await services['routing'].get_turn_by_turn_instructions(route)
                voice_instructions = await services['voice'].generate_voice_instructions(
                    instructions, request.language
                )
            
            enhanced_route = {
                **route.__dict__,
                "ml_eta": ml_eta.__dict__,
                "voice_instructions": voice_instructions,
                "real_time_traffic": request.include_traffic,
                "optimization_score": ml_eta.predicted_duration_minutes / route.total_duration_minutes
            }
            
            enhanced_routes.append(enhanced_route)
        
        # Analytics
        await services['analytics'].track_route_request(
            user['user_id'], request.origin, request.destination, len(enhanced_routes)
        )
        
        return {
            "routes": enhanced_routes,
            "ml_enabled": True,
            "voice_enabled": request.voice_guidance,
            "traffic_enabled": request.include_traffic,
            "optimization": request.optimize_for
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Advanced route calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Route calculation failed")

# ============== PLACES & BUSINESS SEARCH ==============

@app.get("/api/v3/places/search")
async def search_places_advanced(
    q: str = Query(..., description="Search query"),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius: float = Query(10.0, ge=0.1, le=50.0),
    type: Optional[str] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    price_level: Optional[str] = None,
    open_now: bool = False,
    has_photos: bool = False,
    limit: int = Query(20, ge=1, le=100),
    user: Dict = Depends(get_current_user)
):
    """Advanced places search with ML ranking"""
    try:
        place_type = PlaceType(type) if type else None
        
        # Search places
        places = await services['places'].search_places(
            query=q,
            latitude=lat,
            longitude=lng,
            radius_km=radius,
            place_type=place_type,
            min_rating=min_rating,
            open_now=open_now,
            limit=limit
        )
        
        # Enhance with additional data
        enhanced_places = []
        for place in places:
            # Get popular times
            popular_times = await services['places'].get_popular_times(place.place_id)
            
            # Get recent reviews
            reviews = await services['places'].get_reviews(place.place_id, limit=3)
            
            # Calculate personalized score (mock)
            personalization_score = await services['analytics'].get_place_affinity(
                user['user_id'], place.place_id
            )
            
            enhanced_place = {
                **place.__dict__,
                "popular_times": popular_times.__dict__ if popular_times else None,
                "recent_reviews": [r.__dict__ for r in reviews],
                "personalization_score": personalization_score,
                "distance_km": getattr(place, 'distance_km', None),
                "is_open_now": place.opening_hours.is_open_now() if place.opening_hours else None
            }
            
            enhanced_places.append(enhanced_place)
        
        # Analytics
        await services['analytics'].track_place_search(user['user_id'], q, len(enhanced_places))
        
        return {
            "places": enhanced_places,
            "total_results": len(enhanced_places),
            "search_query": q,
            "ml_ranking": True,
            "personalized": True
        }
        
    except Exception as e:
        logger.error(f"Places search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.post("/api/v3/places/{place_id}/reviews")
async def add_place_review(
    place_id: str,
    rating: float = Field(..., ge=1, le=5),
    text: Optional[str] = None,
    photos: List[str] = [],
    user: Dict = Depends(get_current_user)
):
    """Add review with ML content moderation"""
    try:
        # Content moderation
        if text:
            is_appropriate = await services['security'].moderate_content(text)
            if not is_appropriate:
                raise HTTPException(status_code=400, detail="Content violates guidelines")
        
        review = Review(
            review_id=str(uuid.uuid4()),
            user_id=user['user_id'],
            rating=rating,
            text=text,
            photos=photos
        )
        
        success = await services['places'].add_review(place_id, review)
        if not success:
            raise HTTPException(status_code=404, detail="Place not found")
        
        return {"status": "success", "review_id": review.review_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Review submission failed: {e}")
        raise HTTPException(status_code=500, detail="Review submission failed")

# ============== STREET VIEW ==============

@app.get("/api/v3/street-view")
async def get_street_view(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    pano_id: Optional[str] = None,
    heading: float = Query(0, ge=0, lt=360),
    pitch: float = Query(0, ge=-90, le=90),
    fov: float = Query(90, ge=10, le=120),
    quality: str = Query("medium"),
    user: Dict = Depends(get_current_user)
):
    """Get Street View panoramic imagery"""
    try:
        query = StreetViewQuery(
            latitude=lat,
            longitude=lng,
            pano_id=pano_id,
            heading=heading,
            pitch=pitch,
            fov=fov,
            quality=ImageQuality(quality)
        )
        
        street_view = await services['street_view'].get_street_view(query)
        
        if not street_view:
            raise HTTPException(status_code=404, detail="No Street View available")
        
        # Analytics
        await services['analytics'].track_street_view_request(user['user_id'], lat, lng)
        
        return {
            **street_view.__dict__,
            "metadata": street_view.metadata.__dict__
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Street View request failed: {e}")
        raise HTTPException(status_code=500, detail="Street View unavailable")

# ============== MULTI-STOP OPTIMIZATION ==============

class DeliveryOptimizationRequest(BaseModel):
    stops: List[Dict]  # stop data
    vehicles: List[Dict]  # vehicle data
    depot_lat: float
    depot_lng: float
    departure_time: Optional[datetime] = None
    optimize_for: str = "time"
    max_duration_hours: Optional[int] = 8

@app.post("/api/v3/optimize/delivery-routes")
async def optimize_delivery_routes(
    request: DeliveryOptimizationRequest,
    user: Dict = Depends(get_current_user)
):
    """Optimize delivery routes with advanced constraints"""
    try:
        # Convert request to optimizer objects
        stops = []
        for stop_data in request.stops:
            stop = Stop(
                stop_id=stop_data['id'],
                latitude=stop_data['lat'],
                longitude=stop_data['lng'],
                name=stop_data.get('name'),
                service_duration_minutes=stop_data.get('service_duration', 10),
                delivery_amount=stop_data.get('delivery_amount', 1.0),
                priority=stop_data.get('priority', 1)
            )
            stops.append(stop)
        
        vehicles = []
        for vehicle_data in request.vehicles:
            from .multi_stop_optimizer import Vehicle, VehicleType
            vehicle = Vehicle(
                vehicle_id=vehicle_data['id'],
                vehicle_type=VehicleType(vehicle_data['type']),
                capacity=vehicle_data['capacity'],
                max_duration_minutes=request.max_duration_hours * 60 if request.max_duration_hours else None
            )
            vehicles.append(vehicle)
        
        # Optimize routes
        optimized_routes = await services['optimizer'].optimize_route(
            stops=stops,
            vehicles=vehicles,
            start_location=(request.depot_lat, request.depot_lng),
            departure_time=request.departure_time
        )
        
        # Convert results
        result_routes = []
        for route in optimized_routes:
            result_routes.append({
                **route.__dict__,
                "stops": [s.__dict__ for s in route.stops],
                "vehicle": route.vehicle.__dict__,
                "arrival_times": [dt.isoformat() for dt in route.arrival_times],
                "service_times": [(start.isoformat(), end.isoformat()) for start, end in route.service_times]
            })
        
        # Analytics
        await services['analytics'].track_optimization_request(
            user['user_id'], len(stops), len(vehicles), len(result_routes)
        )
        
        return {
            "optimized_routes": result_routes,
            "total_distance_km": sum(r.total_distance_km for r in optimized_routes),
            "total_duration_minutes": sum(r.total_duration_minutes for r in optimized_routes),
            "vehicles_used": len(result_routes),
            "optimization_quality": "optimal"
        }
        
    except Exception as e:
        logger.error(f"Route optimization failed: {e}")
        raise HTTPException(status_code=500, detail="Optimization failed")

# ============== TRANSIT INTEGRATION ==============

@app.get("/api/v3/transit/routes")
async def get_transit_routes(
    origin: str = Query(...),
    destination: str = Query(...),
    departure_time: Optional[datetime] = None,
    arrival_time: Optional[datetime] = None,
    modes: List[str] = Query(["subway", "bus", "train"]),
    user: Dict = Depends(get_current_user)
):
    """Get public transit routes with real-time data"""
    try:
        transit_routes = await services['transit'].plan_journey(
            origin=origin,
            destination=destination,
            departure_time=departure_time or datetime.now(),
            modes=modes
        )
        
        if not transit_routes:
            raise HTTPException(status_code=404, detail="No transit routes found")
        
        # Enhance with real-time data
        enhanced_routes = []
        for route in transit_routes:
            real_time_updates = await services['transit'].get_real_time_updates(route['route_id'])
            route['real_time_updates'] = real_time_updates
            enhanced_routes.append(route)
        
        return {
            "routes": enhanced_routes,
            "real_time_enabled": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transit routing failed: {e}")
        raise HTTPException(status_code=500, detail="Transit routing failed")

# ============== RIDE SHARING ==============

@app.post("/api/v3/rides/request")
async def request_ride(
    pickup_lat: float = Field(..., ge=-90, le=90),
    pickup_lng: float = Field(..., ge=-180, le=180),
    destination_lat: float = Field(..., ge=-90, le=90),
    destination_lng: float = Field(..., ge=-180, le=180),
    ride_type: str = "standard",
    passengers: int = Field(1, ge=1, le=8),
    user: Dict = Depends(get_current_user)
):
    """Request a ride with dynamic pricing"""
    try:
        ride_request = await services['ride_share'].request_ride(
            user_id=user['user_id'],
            pickup_location=(pickup_lat, pickup_lng),
            destination_location=(destination_lat, destination_lng),
            ride_type=ride_type,
            passenger_count=passengers
        )
        
        return {
            **ride_request,
            "estimated_price": ride_request['price'],
            "estimated_arrival": ride_request['eta_minutes'],
            "available_drivers": ride_request['driver_count']
        }
        
    except Exception as e:
        logger.error(f"Ride request failed: {e}")
        raise HTTPException(status_code=500, detail="Ride request failed")

# ============== OFFLINE MAPS ==============

@app.post("/api/v3/offline/download")
async def download_offline_area(
    north: float = Field(..., ge=-90, le=90),
    south: float = Field(..., ge=-90, le=90),
    east: float = Field(..., ge=-180, le=180),
    west: float = Field(..., ge=-180, le=180),
    min_zoom: int = Field(10, ge=0, le=20),
    max_zoom: int = Field(15, ge=0, le=20),
    include_places: bool = True,
    include_transit: bool = True,
    user: Dict = Depends(get_current_user)
):
    """Download map area for offline use"""
    try:
        download_request = await services['offline'].prepare_download(
            user_id=user['user_id'],
            bounds=(north, south, east, west),
            zoom_range=(min_zoom, max_zoom),
            include_places=include_places,
            include_transit=include_transit
        )
        
        return {
            "download_id": download_request['download_id'],
            "estimated_size_mb": download_request['estimated_size_mb'],
            "estimated_duration_minutes": download_request['estimated_duration_minutes'],
            "status": "preparing"
        }
        
    except Exception as e:
        logger.error(f"Offline download failed: {e}")
        raise HTTPException(status_code=500, detail="Download preparation failed")

# ============== ANALYTICS DASHBOARD ==============

@app.get("/api/v3/analytics/dashboard")
async def get_analytics_dashboard(
    time_range: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    user: Dict = Depends(get_current_user)
):
    """Get comprehensive analytics dashboard"""
    try:
        # Check admin permissions
        if "admin" not in user.get('permissions', []):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        dashboard_data = await services['analytics'].get_dashboard(time_range)
        
        return {
            "time_range": time_range,
            "generated_at": datetime.now().isoformat(),
            **dashboard_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics dashboard failed: {e}")
        raise HTTPException(status_code=500, detail="Analytics unavailable")

# ============== VOICE NAVIGATION ==============

@app.get("/api/v3/voice/instructions/{route_id}")
async def get_voice_instructions(
    route_id: str,
    language: str = Query("en", regex="^(en|es|fr|de|it|pt|zh|ja|ko)$"),
    voice: str = Query("female", regex="^(male|female|neutral)$"),
    user: Dict = Depends(get_current_user)
):
    """Get voice navigation instructions"""
    try:
        voice_data = await services['voice'].get_route_instructions(
            route_id=route_id,
            language=language,
            voice_type=voice
        )
        
        return {
            "route_id": route_id,
            "language": language,
            "voice_type": voice,
            "instructions": voice_data['instructions'],
            "audio_urls": voice_data['audio_urls'],
            "total_duration_seconds": voice_data['total_duration']
        }
        
    except Exception as e:
        logger.error(f"Voice instructions failed: {e}")
        raise HTTPException(status_code=500, detail="Voice generation failed")

# ============== SYSTEM MONITORING ==============

@app.get("/api/v3/system/health")
async def comprehensive_health_check():
    """Comprehensive system health check"""
    try:
        health_status = await services['monitoring'].get_system_health()
        
        return {
            "status": "healthy" if health_status['overall_health'] else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": health_status['services'],
            "metrics": health_status['metrics'],
            "version": "3.0.0",
            "uptime_seconds": health_status['uptime'],
            "active_users": health_status['active_users']
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/v3/system/metrics")
async def get_system_metrics(
    user: Dict = Depends(get_current_user)
):
    """Get detailed system metrics"""
    try:
        if "admin" not in user.get('permissions', []):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        metrics = await services['monitoring'].get_detailed_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            **metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")

# ============== WEBSOCKET ENDPOINTS ==============

@app.websocket("/ws/v3/live-navigation")
async def websocket_live_navigation(
    websocket: WebSocket,
    user_id: str = Query(...),
    route_id: str = Query(...),
    token: Optional[str] = Query(None)
):
    """Enhanced live navigation with ML predictions and voice"""
    await manager.connect(websocket, user_id, ChannelType.NAVIGATION)
    
    try:
        # Enhanced navigation with ML and voice
        await manager.handle_enhanced_navigation_stream(
            websocket, user_id, route_id,
            ml_eta_service=services['ml_eta'],
            voice_service=services['voice'],
            traffic_service=services['traffic']
        )
    except Exception as e:
        logger.error(f"Live navigation error: {e}")
    finally:
        manager.disconnect(user_id, ChannelType.NAVIGATION)

# ============== UTILITY FUNCTIONS ==============

async def _parse_location(location: str, geocoding_service) -> Optional[Tuple[float, float]]:
    """Enhanced location parsing with caching"""
    try:
        if ',' in location and location.count(',') == 1:
            parts = location.split(',')
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                return (lat, lng)
        
        result = await geocoding_service.geocode(location)
        if result:
            return (result.latitude, result.longitude)
    except:
        pass
    return None

# ============== ERROR HANDLERS ==============

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Global error handler with monitoring"""
    await services['monitoring'].log_error(str(exc), request.url.path)
    return {
        "error": "Internal server error",
        "timestamp": datetime.now().isoformat(),
        "request_id": str(uuid.uuid4())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "complete_api:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level="info",
        workers=4 if not settings.debug else 1
    )