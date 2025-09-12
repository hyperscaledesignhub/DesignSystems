"""
Enhanced Google Maps Clone API with Advanced Features
Includes geocoding, navigation, real-time updates, and traffic management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import uuid
import logging
import asyncio
from contextlib import asynccontextmanager

# Import existing services
from .database import DatabaseManager
from .models import LocationUpdate, LocationBatch, UserCurrentLocation, LocationHistory
from .batch_processor import BatchProcessor
from .config import settings

# Import new services
from .geocoding import GeocodingService, GeocodedLocation
from .navigation import RoutingService, Route, TravelMode, NavigationInstruction
from .websocket_manager import manager, ChannelType
from .traffic import TrafficService, TrafficCondition, TrafficIncident
from .map_tiles import MapTileService, TileFormat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
db_manager = None
batch_processor = None
geocoding_service = None
routing_service = None
traffic_service = None
map_tile_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    global db_manager, batch_processor, geocoding_service, routing_service, traffic_service, map_tile_service
    
    logger.info("Starting Enhanced Google Maps Service...")
    
    # Initialize core services
    db_manager = DatabaseManager(settings.cassandra_hosts, settings.cassandra_keyspace)
    await db_manager.connect()
    
    batch_processor = BatchProcessor(db_manager)
    
    # Initialize new services
    geocoding_service = GeocodingService(
        cache_host=settings.redis_host,
        cache_port=settings.redis_port
    )
    
    routing_service = RoutingService(
        graph_data_path=settings.graph_data_path,
        cache_host=settings.redis_host,
        cache_port=settings.redis_port
    )
    
    traffic_service = TrafficService(db_manager)
    await traffic_service.initialize()
    
    map_tile_service = MapTileService(
        tile_storage_path=settings.tile_storage_path,
        cache_enabled=True
    )
    
    logger.info("All services started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    if db_manager:
        await db_manager.close()
    if traffic_service:
        await traffic_service.close()
    logger.info("Shutdown complete")

app = FastAPI(
    title="Google Maps Clone API",
    description="Complete mapping service with navigation, geocoding, and real-time features",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== GEOCODING ENDPOINTS ==============

@app.post("/api/v2/geocode")
async def geocode_address(
    address: str = Field(..., description="Address to geocode"),
    geocoding: GeocodingService = Depends(lambda: geocoding_service)
):
    """Convert address to coordinates"""
    try:
        result = await geocoding.geocode(address)
        if not result:
            raise HTTPException(status_code=404, detail="Address not found")
        return result.__dict__
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        raise HTTPException(status_code=500, detail="Geocoding failed")

@app.post("/api/v2/reverse-geocode")
async def reverse_geocode(
    latitude: float = Field(..., ge=-90, le=90),
    longitude: float = Field(..., ge=-180, le=180),
    geocoding: GeocodingService = Depends(lambda: geocoding_service)
):
    """Convert coordinates to address"""
    try:
        result = await geocoding.reverse_geocode(latitude, longitude)
        if not result:
            raise HTTPException(status_code=404, detail="Location not found")
        return result.__dict__
    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}")
        raise HTTPException(status_code=500, detail="Reverse geocoding failed")

@app.get("/api/v2/places/nearby")
async def find_nearby_places(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: int = Query(1000, ge=100, le=50000),
    place_type: Optional[str] = None,
    geocoding: GeocodingService = Depends(lambda: geocoding_service)
):
    """Find nearby places of interest"""
    try:
        places = await geocoding.find_nearby_places(
            latitude, longitude, radius_meters, place_type
        )
        return {"places": places, "count": len(places)}
    except Exception as e:
        logger.error(f"Places search error: {e}")
        raise HTTPException(status_code=500, detail="Places search failed")

# ============== NAVIGATION ENDPOINTS ==============

class RouteRequest(BaseModel):
    origin: str  # Address or "lat,lng"
    destination: str
    mode: TravelMode = TravelMode.DRIVING
    waypoints: Optional[List[str]] = None
    alternatives: bool = False
    avoid_tolls: bool = False
    avoid_highways: bool = False

@app.post("/api/v2/routes/calculate")
async def calculate_route(
    request: RouteRequest,
    geocoding: GeocodingService = Depends(lambda: geocoding_service),
    routing: RoutingService = Depends(lambda: routing_service)
):
    """Calculate route between origin and destination"""
    try:
        # Geocode origin and destination if needed
        origin_coords = await _parse_location(request.origin, geocoding)
        dest_coords = await _parse_location(request.destination, geocoding)
        
        if not origin_coords or not dest_coords:
            raise HTTPException(status_code=400, detail="Invalid origin or destination")
        
        # Calculate route
        if request.alternatives:
            routes = await routing.get_route_alternatives(
                origin_coords, dest_coords, request.mode
            )
            return {"routes": [r.__dict__ for r in routes]}
        else:
            route = await routing.find_route(
                origin_coords, dest_coords, request.mode,
                avoid_highways=request.avoid_highways
            )
            if not route:
                raise HTTPException(status_code=404, detail="No route found")
            return route.__dict__
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Route calculation error: {e}")
        raise HTTPException(status_code=500, detail="Route calculation failed")

async def _parse_location(location: str, geocoding: GeocodingService) -> Optional[Tuple[float, float]]:
    """Parse location string (address or coordinates)"""
    try:
        # Check if it's coordinates
        if ',' in location:
            parts = location.split(',')
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                return (lat, lng)
        
        # Otherwise, geocode the address
        result = await geocoding.geocode(location)
        if result:
            return (result.latitude, result.longitude)
    except:
        pass
    return None

@app.get("/api/v2/routes/{route_id}/instructions")
async def get_navigation_instructions(
    route_id: str,
    routing: RoutingService = Depends(lambda: routing_service)
):
    """Get turn-by-turn navigation instructions"""
    # In production, retrieve route from cache/database
    # For demo, return sample instructions
    return {
        "route_id": route_id,
        "instructions": [
            {
                "step": 1,
                "text": "Head north on Market St",
                "distance_m": 200,
                "duration_s": 45
            },
            {
                "step": 2,
                "text": "Turn right onto 2nd St",
                "distance_m": 500,
                "duration_s": 120
            }
        ]
    }

@app.post("/api/v2/routes/{route_id}/eta")
async def calculate_eta(
    route_id: str,
    current_lat: Optional[float] = None,
    current_lng: Optional[float] = None,
    routing: RoutingService = Depends(lambda: routing_service),
    traffic: TrafficService = Depends(lambda: traffic_service)
):
    """Calculate ETA with traffic consideration"""
    try:
        # Get traffic factor
        traffic_factor = await traffic.get_traffic_factor(route_id)
        
        # Calculate ETA (simplified for demo)
        eta_info = {
            "route_id": route_id,
            "eta": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "duration_minutes": 30 * traffic_factor,
            "traffic_condition": "moderate" if traffic_factor > 1.2 else "light",
            "last_updated": datetime.now().isoformat()
        }
        
        return eta_info
        
    except Exception as e:
        logger.error(f"ETA calculation error: {e}")
        raise HTTPException(status_code=500, detail="ETA calculation failed")

# ============== REAL-TIME WEBSOCKET ENDPOINTS ==============

@app.websocket("/ws/location-stream")
async def websocket_location_stream(
    websocket: WebSocket,
    user_id: str = Query(...),
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time location streaming"""
    # Validate token in production
    await manager.connect(websocket, user_id, ChannelType.LOCATION)
    try:
        await manager.handle_location_stream(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        manager.disconnect(user_id, ChannelType.LOCATION)

@app.websocket("/ws/navigation-updates")
async def websocket_navigation(
    websocket: WebSocket,
    user_id: str = Query(...),
    route_id: str = Query(...),
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for navigation updates"""
    await manager.connect(websocket, user_id, ChannelType.NAVIGATION)
    try:
        await manager.handle_navigation_stream(websocket, user_id, route_id)
    except Exception as e:
        logger.error(f"Navigation WebSocket error for user {user_id}: {e}")
    finally:
        manager.disconnect(user_id, ChannelType.NAVIGATION)

@app.websocket("/ws/traffic-feed")
async def websocket_traffic(
    websocket: WebSocket,
    user_id: str = Query(...),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: float = Query(5.0)
):
    """WebSocket endpoint for real-time traffic updates"""
    await manager.connect(websocket, user_id, ChannelType.TRAFFIC)
    
    area_bounds = None
    if lat and lng:
        area_bounds = {
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km
        }
    
    try:
        await manager.handle_traffic_stream(websocket, user_id, area_bounds)
    except Exception as e:
        logger.error(f"Traffic WebSocket error for user {user_id}: {e}")
    finally:
        manager.disconnect(user_id, ChannelType.TRAFFIC)

# ============== TRAFFIC ENDPOINTS ==============

@app.get("/api/v2/traffic/current")
async def get_current_traffic(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(5.0, ge=0.1, le=50),
    traffic: TrafficService = Depends(lambda: traffic_service)
):
    """Get current traffic conditions in an area"""
    try:
        conditions = await traffic.get_area_traffic(lat, lng, radius_km)
        return {
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "conditions": conditions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Traffic query error: {e}")
        raise HTTPException(status_code=500, detail="Traffic query failed")

@app.post("/api/v2/traffic/report-incident")
async def report_traffic_incident(
    incident_type: str = Field(..., description="Type of incident"),
    severity: str = Field("moderate", description="Severity level"),
    lat: float = Field(..., ge=-90, le=90),
    lng: float = Field(..., ge=-180, le=180),
    description: Optional[str] = None,
    user_id: str = Field(...),
    traffic: TrafficService = Depends(lambda: traffic_service),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Report a traffic incident"""
    try:
        incident = TrafficIncident(
            incident_id=str(uuid.uuid4()),
            type=incident_type,
            severity=severity,
            location=(lat, lng),
            description=description,
            reporter_id=user_id,
            timestamp=datetime.now()
        )
        
        # Store incident
        await traffic.report_incident(incident)
        
        # Broadcast to nearby users in background
        background_tasks.add_task(
            manager.broadcast_traffic_update,
            {"incident": incident.__dict__},
            None
        )
        
        return {
            "status": "reported",
            "incident_id": incident.incident_id
        }
        
    except Exception as e:
        logger.error(f"Incident reporting error: {e}")
        raise HTTPException(status_code=500, detail="Failed to report incident")

# ============== MAP TILE ENDPOINTS ==============

@app.get("/api/v2/tiles/{z}/{x}/{y}")
async def get_map_tile(
    z: int = Field(..., ge=0, le=20, description="Zoom level"),
    x: int = Field(..., ge=0, description="Tile X coordinate"),
    y: int = Field(..., ge=0, description="Tile Y coordinate"),
    style: str = Query("default", description="Map style"),
    format: TileFormat = Query(TileFormat.VECTOR, description="Tile format"),
    tiles: MapTileService = Depends(lambda: map_tile_service)
):
    """Get a map tile at specified coordinates"""
    try:
        tile_data = await tiles.get_tile(z, x, y, style, format)
        if not tile_data:
            raise HTTPException(status_code=404, detail="Tile not found")
        
        # Return tile with appropriate content type
        content_type = "application/x-protobuf" if format == TileFormat.VECTOR else "image/png"
        return {
            "tile": tile_data,
            "content_type": content_type,
            "cache_control": "public, max-age=86400"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tile serving error: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve tile")

@app.post("/api/v2/tiles/download-area")
async def download_map_area(
    north: float = Field(..., ge=-90, le=90),
    south: float = Field(..., ge=-90, le=90),
    east: float = Field(..., ge=-180, le=180),
    west: float = Field(..., ge=-180, le=180),
    min_zoom: int = Field(10, ge=0, le=20),
    max_zoom: int = Field(15, ge=0, le=20),
    tiles: MapTileService = Depends(lambda: map_tile_service),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Download map tiles for offline use"""
    try:
        download_id = str(uuid.uuid4())
        
        # Start download in background
        background_tasks.add_task(
            tiles.prepare_offline_package,
            download_id,
            (north, south, east, west),
            min_zoom,
            max_zoom
        )
        
        return {
            "download_id": download_id,
            "status": "preparing",
            "estimated_size_mb": tiles.estimate_download_size(
                (north, south, east, west),
                min_zoom,
                max_zoom
            )
        }
        
    except Exception as e:
        logger.error(f"Offline download error: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare download")

# ============== EXISTING LOCATION ENDPOINTS (Enhanced) ==============

@app.post("/api/v2/locations/batch")
async def submit_location_batch_v2(
    batch: LocationBatch,
    background_tasks: BackgroundTasks,
    processor: BatchProcessor = Depends(lambda: batch_processor),
    traffic: TrafficService = Depends(lambda: traffic_service)
):
    """Enhanced batch location submission with traffic analysis"""
    try:
        # Process batch as before
        batch_id = str(uuid.uuid4())
        
        background_tasks.add_task(
            processor.process_location_batch,
            batch_id,
            batch.user_id,
            batch.locations
        )
        
        # Analyze for traffic patterns
        background_tasks.add_task(
            traffic.analyze_location_batch,
            batch.user_id,
            batch.locations
        )
        
        # Broadcast live location if user has subscribers
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
        
        return {
            "status": "accepted",
            "batch_id": batch_id,
            "processed_count": len(batch.locations)
        }
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        raise HTTPException(status_code=500, detail="Batch processing failed")

# ============== GEOSPATIAL SEARCH ==============

@app.get("/api/v2/locations/geohash/{geohash}")
async def get_users_in_geohash(
    geohash: str,
    precision: int = Query(7, ge=1, le=12),
    include_neighbors: bool = Query(False),
    db: DatabaseManager = Depends(lambda: db_manager),
    geocoding: GeocodingService = Depends(lambda: geocoding_service)
):
    """Get users within a geohash cell"""
    try:
        # Decode geohash to coordinates
        lat, lng = geocoding.decode_geohash(geohash[:precision])
        
        users = []
        
        # Get users in main cell
        cell_users = await db.get_users_in_area(lat, lng, precision)
        users.extend(cell_users)
        
        # Include neighboring cells if requested
        if include_neighbors:
            neighbors = geocoding.get_geohash_neighbors(geohash[:precision])
            for neighbor_hash in neighbors:
                n_lat, n_lng = geocoding.decode_geohash(neighbor_hash)
                neighbor_users = await db.get_users_in_area(n_lat, n_lng, precision)
                users.extend(neighbor_users)
        
        return {
            "geohash": geohash[:precision],
            "center": {"lat": lat, "lng": lng},
            "users": users,
            "count": len(users),
            "include_neighbors": include_neighbors
        }
        
    except Exception as e:
        logger.error(f"Geohash search error: {e}")
        raise HTTPException(status_code=500, detail="Geohash search failed")

# ============== METRICS & MONITORING ==============

@app.get("/api/v2/metrics/system")
async def get_system_metrics(
    db: DatabaseManager = Depends(lambda: db_manager),
    traffic: TrafficService = Depends(lambda: traffic_service)
):
    """Get comprehensive system metrics"""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "location_service": await db.get_location_metrics(),
            "active_connections": {
                "location_streams": len(manager.active_connections[ChannelType.LOCATION]),
                "navigation_sessions": len(manager.navigation_sessions),
                "traffic_subscribers": len(manager.active_connections[ChannelType.TRAFFIC])
            },
            "traffic_conditions": await traffic.get_overall_traffic_summary(),
            "api_version": "2.0.0"
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

# ============== HEALTH CHECK ==============

@app.get("/api/v2/health")
async def health_check_v2(
    db: DatabaseManager = Depends(lambda: db_manager)
):
    """Enhanced health check"""
    try:
        checks = {
            "database": await db.health_check(),
            "geocoding": geocoding_service is not None,
            "routing": routing_service is not None,
            "traffic": traffic_service is not None,
            "websocket": len(manager.active_connections) >= 0,
            "tiles": map_tile_service is not None
        }
        
        all_healthy = all(checks.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": checks,
            "version": "2.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "enhanced_main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level="info"
    )