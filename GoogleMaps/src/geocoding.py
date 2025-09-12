"""
Geocoding and Reverse Geocoding Service
Converts between addresses and coordinates
"""

import logging
import math
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import hashlib
import redis
import json

logger = logging.getLogger(__name__)

@dataclass
class GeocodedLocation:
    """Represents a geocoded location with address and coordinates"""
    address: str
    latitude: float
    longitude: float
    place_id: str
    display_name: str
    country: str
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    
class GeocodingService:
    """
    Service for geocoding (address to coordinates) and 
    reverse geocoding (coordinates to address)
    """
    
    def __init__(self, cache_host: str = "localhost", cache_port: int = 6379):
        """Initialize geocoding service with caching"""
        # Initialize geocoder (using OpenStreetMap's Nominatim)
        self.geocoder = Nominatim(user_agent="google-maps-clone")
        
        # Initialize Redis cache for geocoding results
        try:
            self.cache = redis.Redis(
                host=cache_host, 
                port=cache_port, 
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.cache.ping()
            self.cache_enabled = True
            logger.info("Geocoding cache connected")
        except:
            logger.warning("Geocoding cache unavailable, running without cache")
            self.cache_enabled = False
            self.cache = None
    
    def _get_cache_key(self, query: str, query_type: str = "geocode") -> str:
        """Generate cache key for a query"""
        hash_input = f"{query_type}:{query}".encode()
        return f"geo:{hashlib.md5(hash_input).hexdigest()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get cached result"""
        if not self.cache_enabled:
            return None
        
        try:
            cached = self.cache.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict, ttl: int = 86400):
        """Save result to cache with TTL (default 24 hours)"""
        if not self.cache_enabled:
            return
        
        try:
            self.cache.setex(
                cache_key,
                ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    async def geocode(self, address: str) -> Optional[GeocodedLocation]:
        """
        Convert address to coordinates
        
        Args:
            address: Street address or place name
            
        Returns:
            GeocodedLocation object or None if not found
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(address, "geocode")
            cached = self._get_from_cache(cache_key)
            
            if cached:
                logger.info(f"Geocoding cache hit for: {address}")
                return GeocodedLocation(**cached)
            
            # Query geocoding service
            location = self.geocoder.geocode(address, addressdetails=True)
            
            if not location:
                logger.warning(f"No results for address: {address}")
                return None
            
            # Extract address components
            addr_details = location.raw.get('address', {})
            
            result = GeocodedLocation(
                address=address,
                latitude=location.latitude,
                longitude=location.longitude,
                place_id=str(location.raw.get('place_id', '')),
                display_name=location.raw.get('display_name', ''),
                country=addr_details.get('country', ''),
                city=addr_details.get('city') or addr_details.get('town'),
                state=addr_details.get('state'),
                postal_code=addr_details.get('postcode')
            )
            
            # Cache the result
            self._save_to_cache(cache_key, result.__dict__)
            
            logger.info(f"Geocoded address: {address} -> ({result.latitude}, {result.longitude})")
            return result
            
        except Exception as e:
            logger.error(f"Geocoding error for {address}: {e}")
            return None
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GeocodedLocation]:
        """
        Convert coordinates to address
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            GeocodedLocation object or None if not found
        """
        try:
            # Check cache first
            coords_str = f"{latitude:.6f},{longitude:.6f}"
            cache_key = self._get_cache_key(coords_str, "reverse")
            cached = self._get_from_cache(cache_key)
            
            if cached:
                logger.info(f"Reverse geocoding cache hit for: {coords_str}")
                return GeocodedLocation(**cached)
            
            # Query reverse geocoding service
            location = self.geocoder.reverse(
                (latitude, longitude),
                addressdetails=True
            )
            
            if not location:
                logger.warning(f"No results for coordinates: {coords_str}")
                return None
            
            # Extract address components
            addr_details = location.raw.get('address', {})
            
            result = GeocodedLocation(
                address=location.address,
                latitude=latitude,
                longitude=longitude,
                place_id=str(location.raw.get('place_id', '')),
                display_name=location.raw.get('display_name', ''),
                country=addr_details.get('country', ''),
                city=addr_details.get('city') or addr_details.get('town'),
                state=addr_details.get('state'),
                postal_code=addr_details.get('postcode')
            )
            
            # Cache the result
            self._save_to_cache(cache_key, result.__dict__)
            
            logger.info(f"Reverse geocoded: {coords_str} -> {result.address}")
            return result
            
        except Exception as e:
            logger.error(f"Reverse geocoding error for ({latitude}, {longitude}): {e}")
            return None
    
    async def batch_geocode(self, addresses: List[str]) -> List[Optional[GeocodedLocation]]:
        """
        Geocode multiple addresses
        
        Args:
            addresses: List of addresses to geocode
            
        Returns:
            List of GeocodedLocation objects (None for failed geocoding)
        """
        results = []
        for address in addresses:
            result = await self.geocode(address)
            results.append(result)
        
        return results
    
    async def find_nearby_places(
        self, 
        latitude: float, 
        longitude: float, 
        radius_meters: int = 1000,
        place_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Find nearby places of interest
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_meters: Search radius in meters
            place_type: Type of places to search (restaurant, gas_station, etc.)
            
        Returns:
            List of nearby places with details
        """
        try:
            # This is a simplified implementation
            # In production, you'd use Google Places API or similar
            
            nearby_places = []
            
            # Reverse geocode to get area information
            center_location = await self.reverse_geocode(latitude, longitude)
            
            if center_location:
                # Add mock nearby places (in production, query actual POI database)
                nearby_places.append({
                    'name': f"Place near {center_location.city or 'location'}",
                    'latitude': latitude + 0.001,
                    'longitude': longitude + 0.001,
                    'distance_meters': 100,
                    'type': place_type or 'general',
                    'address': center_location.address
                })
            
            return nearby_places
            
        except Exception as e:
            logger.error(f"Error finding nearby places: {e}")
            return []
    
    def calculate_distance(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate distance between two points in kilometers
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    
    def generate_geohash(self, latitude: float, longitude: float, precision: int = 7) -> str:
        """
        Generate geohash for coordinates
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            precision: Geohash precision (default 7 ~ 150m x 150m)
            
        Returns:
            Geohash string
        """
        # Base32 alphabet for geohash
        base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
        
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        
        geohash = []
        bits = 0
        bit = 0
        even_bit = True
        
        while len(geohash) < precision:
            if even_bit:
                mid = (lon_range[0] + lon_range[1]) / 2
                if longitude > mid:
                    bits |= (1 << (4 - bit))
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if latitude > mid:
                    bits |= (1 << (4 - bit))
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            
            even_bit = not even_bit
            
            if bit < 4:
                bit += 1
            else:
                geohash.append(base32[bits])
                bits = 0
                bit = 0
        
        return ''.join(geohash)
    
    def decode_geohash(self, geohash: str) -> Tuple[float, float]:
        """
        Decode geohash to coordinates
        
        Args:
            geohash: Geohash string
            
        Returns:
            Tuple of (latitude, longitude)
        """
        base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
        
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]
        
        even_bit = True
        
        for c in geohash:
            idx = base32.index(c)
            
            for i in range(4, -1, -1):
                bit = (idx >> i) & 1
                
                if even_bit:
                    mid = (lon_range[0] + lon_range[1]) / 2
                    if bit == 1:
                        lon_range[0] = mid
                    else:
                        lon_range[1] = mid
                else:
                    mid = (lat_range[0] + lat_range[1]) / 2
                    if bit == 1:
                        lat_range[0] = mid
                    else:
                        lat_range[1] = mid
                
                even_bit = not even_bit
        
        latitude = (lat_range[0] + lat_range[1]) / 2
        longitude = (lon_range[0] + lon_range[1]) / 2
        
        return latitude, longitude
    
    def get_geohash_neighbors(self, geohash: str) -> List[str]:
        """
        Get neighboring geohashes (8 surrounding cells)
        
        Args:
            geohash: Center geohash
            
        Returns:
            List of 8 neighboring geohashes
        """
        # Simplified implementation - in production use proper neighbor finding algorithm
        lat, lon = self.decode_geohash(geohash)
        
        # Approximate cell size based on geohash length
        cell_size = 0.01 / (2 ** (len(geohash) - 2))
        
        neighbors = []
        for dlat in [-cell_size, 0, cell_size]:
            for dlon in [-cell_size, 0, cell_size]:
                if dlat == 0 and dlon == 0:
                    continue  # Skip center cell
                
                neighbor_hash = self.generate_geohash(
                    lat + dlat,
                    lon + dlon,
                    len(geohash)
                )
                neighbors.append(neighbor_hash)
        
        return neighbors