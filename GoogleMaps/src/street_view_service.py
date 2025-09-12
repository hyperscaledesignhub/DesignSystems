"""
Street View Service
360° panoramic imagery and immersive street-level views
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import asyncio
import aiohttp
from pathlib import Path
import hashlib
import redis

logger = logging.getLogger(__name__)

class ImageQuality(Enum):
    LOW = "low"      # 512x256
    MEDIUM = "medium" # 1024x512
    HIGH = "high"    # 2048x1024
    ULTRA = "ultra"  # 4096x2048

class ViewType(Enum):
    STREET = "street"
    INDOOR = "indoor"
    AERIAL = "aerial"
    HISTORICAL = "historical"

@dataclass
class StreetViewMetadata:
    """Metadata for street view imagery"""
    pano_id: str
    latitude: float
    longitude: float
    heading: float  # 0-360 degrees
    pitch: float    # -90 to 90 degrees
    roll: float     # -180 to 180 degrees
    
    # Image details
    width: int
    height: int
    quality: ImageQuality
    view_type: ViewType
    
    # Location details
    address: Optional[str] = None
    place_name: Optional[str] = None
    country: Optional[str] = None
    
    # Capture details
    capture_date: Optional[datetime] = None
    camera_model: Optional[str] = None
    copyright_info: Optional[str] = None
    
    # Navigation
    links: List[str] = field(default_factory=list)  # Connected panoramas
    
@dataclass
class StreetViewImage:
    """Street view panoramic image"""
    pano_id: str
    metadata: StreetViewMetadata
    image_url: str
    thumbnail_url: Optional[str] = None
    tiles: List[str] = field(default_factory=list)  # For high-res tiled loading

@dataclass
class StreetViewQuery:
    """Query parameters for street view"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pano_id: Optional[str] = None
    heading: float = 0
    pitch: float = 0
    fov: float = 90  # Field of view
    quality: ImageQuality = ImageQuality.MEDIUM
    radius: float = 50  # Search radius in meters

class StreetViewService:
    """Street View imagery service"""
    
    def __init__(self, 
                 storage_path: str = "/tmp/streetview",
                 api_key: Optional[str] = None,
                 redis_host: str = "localhost",
                 redis_port: int = 6379):
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.api_key = api_key
        
        # Cache for metadata and images
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=False,  # For binary image data
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis cache enabled for Street View")
        except:
            logger.warning("Redis cache not available")
            self.cache_enabled = False
            self.redis_client = None
        
        # In-memory storage for demo
        self.panoramas: Dict[str, StreetViewMetadata] = {}
        self.image_index: Dict[Tuple[float, float], List[str]] = {}  # lat,lng -> pano_ids
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'images_served': 0,
            'storage_size_mb': 0
        }
    
    async def initialize(self):
        """Initialize Street View service"""
        try:
            # Load sample panoramas
            await self._load_sample_panoramas()
            
            logger.info("Street View service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Street View service: {e}")
    
    async def _load_sample_panoramas(self):
        """Load sample panoramic data"""
        sample_panoramas = [
            StreetViewMetadata(
                pano_id="pano_mv_001",
                latitude=37.4419,
                longitude=-122.1430,
                heading=90,
                pitch=0,
                roll=0,
                width=4096,
                height=2048,
                quality=ImageQuality.HIGH,
                view_type=ViewType.STREET,
                address="123 Main St, Mountain View, CA",
                place_name="Downtown Mountain View",
                country="United States",
                capture_date=datetime(2023, 6, 15),
                camera_model="Google Street View Car",
                links=["pano_mv_002", "pano_mv_003"]
            ),
            StreetViewMetadata(
                pano_id="pano_mv_002",
                latitude=37.4429,
                longitude=-122.1440,
                heading=180,
                pitch=0,
                roll=0,
                width=4096,
                height=2048,
                quality=ImageQuality.HIGH,
                view_type=ViewType.STREET,
                address="456 Castro St, Mountain View, CA",
                place_name="Castro Street",
                country="United States",
                capture_date=datetime(2023, 6, 15),
                camera_model="Google Street View Car",
                links=["pano_mv_001", "pano_mv_003"]
            ),
            StreetViewMetadata(
                pano_id="pano_sf_001",
                latitude=37.7749,
                longitude=-122.4194,
                heading=45,
                pitch=10,
                roll=0,
                width=8192,
                height=4096,
                quality=ImageQuality.ULTRA,
                view_type=ViewType.STREET,
                address="Union Square, San Francisco, CA",
                place_name="Union Square",
                country="United States",
                capture_date=datetime(2023, 8, 20),
                camera_model="Google Street View Trekker",
                links=["pano_sf_002"]
            )
        ]
        
        for pano in sample_panoramas:
            self.panoramas[pano.pano_id] = pano
            
            # Index by location
            location_key = (round(pano.latitude, 4), round(pano.longitude, 4))
            if location_key not in self.image_index:
                self.image_index[location_key] = []
            self.image_index[location_key].append(pano.pano_id)
        
        logger.info(f"Loaded {len(sample_panoramas)} sample panoramas")
    
    async def get_street_view(self, query: StreetViewQuery) -> Optional[StreetViewImage]:
        """Get street view image based on query"""
        try:
            self.stats['total_requests'] += 1
            
            # Find panorama
            pano_metadata = None
            
            if query.pano_id:
                pano_metadata = self.panoramas.get(query.pano_id)
            elif query.latitude and query.longitude:
                pano_metadata = await self._find_nearest_panorama(
                    query.latitude, query.longitude, query.radius
                )
            
            if not pano_metadata:
                return None
            
            # Check cache for rendered image
            cache_key = self._get_image_cache_key(pano_metadata.pano_id, query)
            
            if self.cache_enabled:
                cached_image = self.redis_client.get(f"sv_image:{cache_key}")
                if cached_image:
                    self.stats['cache_hits'] += 1
                    return StreetViewImage(
                        pano_id=pano_metadata.pano_id,
                        metadata=pano_metadata,
                        image_url=f"/api/v2/street-view/image/{cache_key}",
                        thumbnail_url=f"/api/v2/street-view/thumb/{cache_key}"
                    )
            
            # Generate/render street view image
            image = await self._render_street_view(pano_metadata, query)
            
            self.stats['images_served'] += 1
            return image
            
        except Exception as e:
            logger.error(f"Street view request failed: {e}")
            return None
    
    async def _find_nearest_panorama(
        self, 
        latitude: float, 
        longitude: float, 
        radius: float
    ) -> Optional[StreetViewMetadata]:
        """Find nearest panorama to given coordinates"""
        
        min_distance = float('inf')
        nearest_pano = None
        
        for pano in self.panoramas.values():
            distance = self._calculate_distance(
                latitude, longitude,
                pano.latitude, pano.longitude
            ) * 1000  # Convert to meters
            
            if distance <= radius and distance < min_distance:
                min_distance = distance
                nearest_pano = pano
        
        return nearest_pano
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in kilometers"""
        import math
        
        R = 6371  # Earth radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def _render_street_view(
        self, 
        metadata: StreetViewMetadata, 
        query: StreetViewQuery
    ) -> StreetViewImage:
        """Render street view image based on query parameters"""
        
        # In a real implementation, this would:
        # 1. Load the full 360° panorama
        # 2. Apply viewing transformation (heading, pitch, FOV)
        # 3. Render the visible portion
        # 4. Apply any filters or enhancements
        
        # For demo, create mock image URLs
        cache_key = self._get_image_cache_key(metadata.pano_id, query)
        
        # Generate image at requested quality
        width, height = self._get_dimensions(query.quality)
        
        # Create mock tiles for high-resolution images
        tiles = []
        if query.quality in [ImageQuality.HIGH, ImageQuality.ULTRA]:
            tile_size = 512
            tiles_x = width // tile_size
            tiles_y = height // tile_size
            
            for x in range(tiles_x):
                for y in range(tiles_y):
                    tiles.append(f"/api/v2/street-view/tile/{cache_key}/{x}/{y}")
        
        image = StreetViewImage(
            pano_id=metadata.pano_id,
            metadata=metadata,
            image_url=f"/api/v2/street-view/image/{cache_key}",
            thumbnail_url=f"/api/v2/street-view/thumb/{cache_key}",
            tiles=tiles
        )
        
        # Cache the rendered image metadata
        if self.cache_enabled:
            image_data = {
                'pano_id': image.pano_id,
                'image_url': image.image_url,
                'thumbnail_url': image.thumbnail_url,
                'tiles': image.tiles,
                'rendered_at': datetime.now().isoformat(),
                'query': query.__dict__
            }
            
            self.redis_client.setex(
                f"sv_image:{cache_key}",
                3600,  # 1 hour
                json.dumps(image_data)
            )
        
        return image
    
    def _get_image_cache_key(self, pano_id: str, query: StreetViewQuery) -> str:
        """Generate cache key for rendered image"""
        key_data = f"{pano_id}:{query.heading}:{query.pitch}:{query.fov}:{query.quality.value}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_dimensions(self, quality: ImageQuality) -> Tuple[int, int]:
        """Get image dimensions for quality level"""
        dimensions = {
            ImageQuality.LOW: (512, 256),
            ImageQuality.MEDIUM: (1024, 512),
            ImageQuality.HIGH: (2048, 1024),
            ImageQuality.ULTRA: (4096, 2048)
        }
        return dimensions[quality]
    
    async def get_panorama_metadata(self, pano_id: str) -> Optional[StreetViewMetadata]:
        """Get metadata for a specific panorama"""
        return self.panoramas.get(pano_id)
    
    async def get_nearby_panoramas(
        self,
        latitude: float,
        longitude: float,
        radius: float = 100
    ) -> List[StreetViewMetadata]:
        """Get all panoramas within radius"""
        
        nearby = []
        for pano in self.panoramas.values():
            distance = self._calculate_distance(
                latitude, longitude,
                pano.latitude, pano.longitude
            ) * 1000  # Convert to meters
            
            if distance <= radius:
                pano.distance_meters = distance
                nearby.append(pano)
        
        # Sort by distance
        nearby.sort(key=lambda p: getattr(p, 'distance_meters', 0))
        
        return nearby
    
    async def get_navigation_path(
        self,
        start_pano_id: str,
        end_pano_id: str
    ) -> List[str]:
        """Get navigation path between two panoramas"""
        
        # Simple breadth-first search through panorama links
        if start_pano_id == end_pano_id:
            return [start_pano_id]
        
        visited = set()
        queue = [(start_pano_id, [start_pano_id])]
        
        while queue:
            current_id, path = queue.pop(0)
            
            if current_id == end_pano_id:
                return path
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            current_pano = self.panoramas.get(current_id)
            
            if current_pano:
                for link_id in current_pano.links:
                    if link_id not in visited:
                        queue.append((link_id, path + [link_id]))
        
        return []  # No path found
    
    async def search_panoramas(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10,
        limit: int = 20
    ) -> List[StreetViewMetadata]:
        """Search panoramas by text and location"""
        
        results = []
        query_lower = query.lower()
        
        for pano in self.panoramas.values():
            # Text matching
            matches = (
                query_lower in (pano.address or "").lower() or
                query_lower in (pano.place_name or "").lower() or
                query_lower in (pano.country or "").lower()
            )
            
            if not matches:
                continue
            
            # Location filtering
            if latitude and longitude:
                distance = self._calculate_distance(
                    latitude, longitude,
                    pano.latitude, pano.longitude
                )
                if distance > radius_km:
                    continue
                pano.distance_km = distance
            
            results.append(pano)
        
        # Sort by distance if location provided
        if latitude and longitude:
            results.sort(key=lambda p: getattr(p, 'distance_km', 0))
        
        return results[:limit]
    
    async def upload_panorama(
        self,
        image_data: bytes,
        metadata: StreetViewMetadata
    ) -> bool:
        """Upload a new panorama (for user-generated content)"""
        try:
            # Validate image data
            if len(image_data) == 0:
                return False
            
            # Store image
            image_path = self.storage_path / f"{metadata.pano_id}.jpg"
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            # Store metadata
            self.panoramas[metadata.pano_id] = metadata
            
            # Update location index
            location_key = (round(metadata.latitude, 4), round(metadata.longitude, 4))
            if location_key not in self.image_index:
                self.image_index[location_key] = []
            self.image_index[location_key].append(metadata.pano_id)
            
            # Update storage stats
            self.stats['storage_size_mb'] += len(image_data) / (1024 * 1024)
            
            logger.info(f"Uploaded panorama: {metadata.pano_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload panorama: {e}")
            return False
    
    async def get_historical_views(
        self,
        latitude: float,
        longitude: float,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[StreetViewMetadata]:
        """Get historical street view images for a location"""
        
        historical_views = []
        
        for pano in self.panoramas.values():
            # Check location proximity
            distance = self._calculate_distance(
                latitude, longitude,
                pano.latitude, pano.longitude
            ) * 1000  # Convert to meters
            
            if distance > 50:  # Within 50 meters
                continue
            
            # Check date range
            if pano.capture_date:
                if start_date and pano.capture_date < start_date:
                    continue
                if end_date and pano.capture_date > end_date:
                    continue
            
            pano.distance_meters = distance
            historical_views.append(pano)
        
        # Sort by capture date (newest first)
        historical_views.sort(
            key=lambda p: p.capture_date or datetime.min,
            reverse=True
        )
        
        return historical_views
    
    async def get_service_stats(self) -> Dict:
        """Get Street View service statistics"""
        return {
            **self.stats,
            'total_panoramas': len(self.panoramas),
            'cache_enabled': self.cache_enabled,
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(self.stats['total_requests'], 1)
            ) * 100
        }
    
    async def clear_cache(self):
        """Clear Street View cache"""
        if self.cache_enabled and self.redis_client:
            keys = self.redis_client.keys("sv_*")
            if keys:
                self.redis_client.delete(*keys)
        
        logger.info("Street View cache cleared")
    
    async def close(self):
        """Cleanup Street View service"""
        if self.redis_client:
            self.redis_client.close()
        logger.info("Street View service closed")