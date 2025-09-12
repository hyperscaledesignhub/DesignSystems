"""
Places & POI Management System
Comprehensive business listings, reviews, and point-of-interest management
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
import json
import asyncio
from elasticsearch import AsyncElasticsearch
import redis
import uuid
from decimal import Decimal

logger = logging.getLogger(__name__)

class PlaceType(Enum):
    RESTAURANT = "restaurant"
    GAS_STATION = "gas_station"
    HOSPITAL = "hospital"
    SCHOOL = "school"
    HOTEL = "hotel"
    SHOPPING = "shopping"
    BANK = "bank"
    ATM = "atm"
    PHARMACY = "pharmacy"
    PARK = "park"
    MUSEUM = "museum"
    THEATER = "theater"
    GYM = "gym"
    BEAUTY_SALON = "beauty_salon"
    CAR_REPAIR = "car_repair"
    GROCERY = "grocery"
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    OTHER = "other"

class PriceLevel(Enum):
    FREE = 0
    INEXPENSIVE = 1
    MODERATE = 2
    EXPENSIVE = 3
    VERY_EXPENSIVE = 4

@dataclass
class OpeningHours:
    """Represents opening hours for a business"""
    monday: Optional[Tuple[time, time]] = None
    tuesday: Optional[Tuple[time, time]] = None
    wednesday: Optional[Tuple[time, time]] = None
    thursday: Optional[Tuple[time, time]] = None
    friday: Optional[Tuple[time, time]] = None
    saturday: Optional[Tuple[time, time]] = None
    sunday: Optional[Tuple[time, time]] = None
    
    def is_open_now(self) -> bool:
        """Check if place is currently open"""
        now = datetime.now()
        day_name = now.strftime('%A').lower()
        current_time = now.time()
        
        hours = getattr(self, day_name)
        if not hours:
            return False
        
        open_time, close_time = hours
        if close_time < open_time:  # Crosses midnight
            return current_time >= open_time or current_time <= close_time
        else:
            return open_time <= current_time <= close_time

@dataclass
class Review:
    """User review for a place"""
    review_id: str
    user_id: str
    rating: float  # 1-5 stars
    text: Optional[str]
    photos: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    helpful_votes: int = 0
    reported: bool = False

@dataclass
class Place:
    """Complete place/POI information"""
    place_id: str
    name: str
    latitude: float
    longitude: float
    place_type: PlaceType
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    
    # Business details
    opening_hours: Optional[OpeningHours] = None
    price_level: Optional[PriceLevel] = None
    rating: float = 0.0
    review_count: int = 0
    
    # Rich content
    photos: List[str] = field(default_factory=list)
    description: Optional[str] = None
    amenities: List[str] = field(default_factory=list)
    
    # Metadata
    verified: bool = False
    permanently_closed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Analytics
    view_count: int = 0
    search_count: int = 0
    directions_count: int = 0

@dataclass
class PopularTimes:
    """Popular times data for a place"""
    place_id: str
    monday: List[int] = field(default_factory=lambda: [0] * 24)
    tuesday: List[int] = field(default_factory=lambda: [0] * 24)
    wednesday: List[int] = field(default_factory=lambda: [0] * 24)
    thursday: List[int] = field(default_factory=lambda: [0] * 24)
    friday: List[int] = field(default_factory=lambda: [0] * 24)
    saturday: List[int] = field(default_factory=lambda: [0] * 24)
    sunday: List[int] = field(default_factory=lambda: [0] * 24)
    
    def get_current_popularity(self) -> int:
        """Get current popularity (0-100)"""
        now = datetime.now()
        day_name = now.strftime('%A').lower()
        hour = now.hour
        
        popularity_data = getattr(self, day_name)
        return popularity_data[hour] if hour < len(popularity_data) else 0

class PlacesService:
    """Comprehensive Places and POI management service"""
    
    def __init__(self, 
                 elasticsearch_host: str = "localhost:9200",
                 redis_host: str = "localhost",
                 redis_port: int = 6379):
        
        # Initialize Elasticsearch for search
        self.es_client = None
        self.es_index = "places"
        
        # Initialize Redis for caching
        self.redis_client = None
        self.cache_enabled = False
        
        # In-memory storage for demo (would use PostgreSQL in production)
        self.places_db: Dict[str, Place] = {}
        self.reviews_db: Dict[str, List[Review]] = {}
        self.popular_times_db: Dict[str, PopularTimes] = {}
        
        # Search analytics
        self.search_analytics = {}
        
    async def initialize(self):
        """Initialize the places service"""
        try:
            # Initialize Elasticsearch
            try:
                self.es_client = AsyncElasticsearch([{"host": "localhost", "port": 9200}])
                await self._setup_elasticsearch_index()
                logger.info("Elasticsearch connected for places search")
            except:
                logger.warning("Elasticsearch not available, using in-memory search")
            
            # Initialize Redis cache
            try:
                self.redis_client = redis.Redis(
                    host="localhost",
                    port=6379,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                self.redis_client.ping()
                self.cache_enabled = True
                logger.info("Redis cache connected for places service")
            except:
                logger.warning("Redis cache not available")
            
            # Load sample data
            await self._load_sample_places()
            
            logger.info("Places service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize places service: {e}")
    
    async def _setup_elasticsearch_index(self):
        """Setup Elasticsearch index for places"""
        mapping = {
            "mappings": {
                "properties": {
                    "place_id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "location": {"type": "geo_point"},
                    "place_type": {"type": "keyword"},
                    "address": {"type": "text"},
                    "rating": {"type": "float"},
                    "price_level": {"type": "integer"},
                    "amenities": {"type": "keyword"},
                    "description": {"type": "text"},
                    "verified": {"type": "boolean"},
                    "permanently_closed": {"type": "boolean"}
                }
            }
        }
        
        if await self.es_client.indices.exists(index=self.es_index):
            await self.es_client.indices.delete(index=self.es_index)
        
        await self.es_client.indices.create(index=self.es_index, body=mapping)
    
    async def _load_sample_places(self):
        """Load sample places for demonstration"""
        sample_places = [
            Place(
                place_id="place_1",
                name="The Coffee Bean",
                latitude=37.4419,
                longitude=-122.1430,
                place_type=PlaceType.RESTAURANT,
                address="123 Main St, Mountain View, CA",
                phone="+1-650-555-0123",
                website="https://coffeebean.com",
                opening_hours=OpeningHours(
                    monday=(time(7, 0), time(22, 0)),
                    tuesday=(time(7, 0), time(22, 0)),
                    wednesday=(time(7, 0), time(22, 0)),
                    thursday=(time(7, 0), time(22, 0)),
                    friday=(time(7, 0), time(23, 0)),
                    saturday=(time(8, 0), time(23, 0)),
                    sunday=(time(8, 0), time(21, 0))
                ),
                price_level=PriceLevel.MODERATE,
                rating=4.2,
                review_count=156,
                amenities=["wifi", "outdoor_seating", "takeout"],
                description="Cozy coffee shop with great atmosphere",
                verified=True
            ),
            Place(
                place_id="place_2",
                name="Chevron Gas Station",
                latitude=37.4429,
                longitude=-122.1440,
                place_type=PlaceType.GAS_STATION,
                address="456 El Camino Real, Mountain View, CA",
                phone="+1-650-555-0456",
                opening_hours=OpeningHours(
                    monday=(time(0, 0), time(23, 59)),
                    tuesday=(time(0, 0), time(23, 59)),
                    wednesday=(time(0, 0), time(23, 59)),
                    thursday=(time(0, 0), time(23, 59)),
                    friday=(time(0, 0), time(23, 59)),
                    saturday=(time(0, 0), time(23, 59)),
                    sunday=(time(0, 0), time(23, 59))
                ),
                rating=3.8,
                review_count=45,
                amenities=["atm", "car_wash", "convenience_store"],
                verified=True
            ),
            Place(
                place_id="place_3",
                name="Whole Foods Market",
                latitude=37.4409,
                longitude=-122.1420,
                place_type=PlaceType.GROCERY,
                address="789 Castro St, Mountain View, CA",
                phone="+1-650-555-0789",
                website="https://wholefoods.com",
                opening_hours=OpeningHours(
                    monday=(time(8, 0), time(22, 0)),
                    tuesday=(time(8, 0), time(22, 0)),
                    wednesday=(time(8, 0), time(22, 0)),
                    thursday=(time(8, 0), time(22, 0)),
                    friday=(time(8, 0), time(22, 0)),
                    saturday=(time(8, 0), time(22, 0)),
                    sunday=(time(9, 0), time(21, 0))
                ),
                price_level=PriceLevel.EXPENSIVE,
                rating=4.5,
                review_count=312,
                amenities=["parking", "organic", "prepared_foods", "wifi"],
                description="Premium organic grocery store",
                verified=True
            )
        ]
        
        for place in sample_places:
            await self.add_place(place)
            
            # Add sample popular times
            popular_times = PopularTimes(
                place_id=place.place_id,
                monday=[10, 15, 20, 25, 30, 35, 45, 60, 70, 75, 80, 85, 90, 85, 80, 75, 70, 65, 60, 55, 45, 35, 25, 15],
                tuesday=[10, 15, 20, 25, 30, 35, 45, 60, 70, 75, 80, 85, 90, 85, 80, 75, 70, 65, 60, 55, 45, 35, 25, 15],
                wednesday=[10, 15, 20, 25, 30, 35, 45, 60, 70, 75, 80, 85, 90, 85, 80, 75, 70, 65, 60, 55, 45, 35, 25, 15],
                thursday=[10, 15, 20, 25, 30, 35, 45, 60, 70, 75, 80, 85, 90, 85, 80, 75, 70, 65, 60, 55, 45, 35, 25, 15],
                friday=[15, 20, 25, 30, 35, 40, 50, 65, 75, 80, 85, 90, 95, 90, 85, 80, 75, 70, 65, 60, 50, 40, 30, 20],
                saturday=[20, 25, 30, 35, 40, 45, 55, 70, 80, 85, 90, 95, 100, 95, 90, 85, 80, 75, 70, 65, 55, 45, 35, 25],
                sunday=[15, 20, 25, 30, 35, 40, 50, 65, 75, 80, 85, 90, 95, 90, 85, 80, 75, 70, 65, 60, 50, 40, 30, 20]
            )
            self.popular_times_db[place.place_id] = popular_times
        
        logger.info(f"Loaded {len(sample_places)} sample places")
    
    async def add_place(self, place: Place) -> bool:
        """Add a new place to the system"""
        try:
            # Store in database
            self.places_db[place.place_id] = place
            
            # Index in Elasticsearch
            if self.es_client:
                doc = {
                    "place_id": place.place_id,
                    "name": place.name,
                    "location": {"lat": place.latitude, "lon": place.longitude},
                    "place_type": place.place_type.value,
                    "address": place.address,
                    "rating": place.rating,
                    "price_level": place.price_level.value if place.price_level else None,
                    "amenities": place.amenities,
                    "description": place.description,
                    "verified": place.verified,
                    "permanently_closed": place.permanently_closed
                }
                
                await self.es_client.index(
                    index=self.es_index,
                    id=place.place_id,
                    body=doc
                )
            
            # Invalidate cache
            if self.cache_enabled:
                self.redis_client.delete(f"place:{place.place_id}")
            
            logger.info(f"Added place: {place.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add place: {e}")
            return False
    
    async def get_place(self, place_id: str) -> Optional[Place]:
        """Get a place by ID"""
        try:
            # Check cache first
            if self.cache_enabled:
                cached = self.redis_client.get(f"place:{place_id}")
                if cached:
                    data = json.loads(cached)
                    return Place(**data)
            
            # Get from database
            place = self.places_db.get(place_id)
            if place:
                # Increment view count
                place.view_count += 1
                
                # Cache the result
                if self.cache_enabled:
                    self.redis_client.setex(
                        f"place:{place_id}",
                        3600,  # 1 hour
                        json.dumps(place.__dict__, default=str)
                    )
                
                return place
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get place {place_id}: {e}")
            return None
    
    async def search_places(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        place_type: Optional[PlaceType] = None,
        min_rating: Optional[float] = None,
        price_level: Optional[PriceLevel] = None,
        open_now: bool = False,
        limit: int = 20
    ) -> List[Place]:
        """Search for places with various filters"""
        try:
            # Use Elasticsearch if available
            if self.es_client:
                return await self._elasticsearch_search(
                    query, latitude, longitude, radius_km,
                    place_type, min_rating, price_level, open_now, limit
                )
            else:
                return await self._memory_search(
                    query, latitude, longitude, radius_km,
                    place_type, min_rating, price_level, open_now, limit
                )
                
        except Exception as e:
            logger.error(f"Place search failed: {e}")
            return []
    
    async def _elasticsearch_search(
        self,
        query: str,
        latitude: Optional[float],
        longitude: Optional[float],
        radius_km: float,
        place_type: Optional[PlaceType],
        min_rating: Optional[float],
        price_level: Optional[PriceLevel],
        open_now: bool,
        limit: int
    ) -> List[Place]:
        """Search using Elasticsearch"""
        try:
            must_clauses = []
            filter_clauses = []
            
            # Text search
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["name^2", "description", "address"]
                    }
                })
            
            # Geographic search
            if latitude and longitude:
                filter_clauses.append({
                    "geo_distance": {
                        "distance": f"{radius_km}km",
                        "location": {"lat": latitude, "lon": longitude}
                    }
                })
            
            # Type filter
            if place_type:
                filter_clauses.append({
                    "term": {"place_type": place_type.value}
                })
            
            # Rating filter
            if min_rating:
                filter_clauses.append({
                    "range": {"rating": {"gte": min_rating}}
                })
            
            # Price level filter
            if price_level:
                filter_clauses.append({
                    "term": {"price_level": price_level.value}
                })
            
            # Status filters
            filter_clauses.extend([
                {"term": {"permanently_closed": False}}
            ])
            
            # Build query
            search_query = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses
                    }
                },
                "sort": []
            }
            
            # Add geographic sorting if location provided
            if latitude and longitude:
                search_query["sort"].append({
                    "_geo_distance": {
                        "location": {"lat": latitude, "lon": longitude},
                        "order": "asc",
                        "unit": "km"
                    }
                })
            else:
                # Sort by rating and relevance
                search_query["sort"].extend([
                    {"rating": {"order": "desc"}},
                    {"_score": {"order": "desc"}}
                ])
            
            search_query["size"] = limit
            
            # Execute search
            response = await self.es_client.search(
                index=self.es_index,
                body=search_query
            )
            
            # Convert results to Place objects
            results = []
            for hit in response["hits"]["hits"]:
                place_id = hit["_id"]
                place = await self.get_place(place_id)
                if place:
                    # Filter by opening hours if required
                    if open_now and place.opening_hours:
                        if not place.opening_hours.is_open_now():
                            continue
                    
                    # Add distance information
                    if "sort" in hit and latitude and longitude:
                        place.distance_km = hit["sort"][0]
                    
                    results.append(place)
            
            # Track search analytics
            await self._track_search(query, place_type, len(results))
            
            return results
            
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            return []
    
    async def _memory_search(
        self,
        query: str,
        latitude: Optional[float],
        longitude: Optional[float],
        radius_km: float,
        place_type: Optional[PlaceType],
        min_rating: Optional[float],
        price_level: Optional[PriceLevel],
        open_now: bool,
        limit: int
    ) -> List[Place]:
        """Simple in-memory search (fallback)"""
        results = []
        
        for place in self.places_db.values():
            # Skip closed places
            if place.permanently_closed:
                continue
            
            # Type filter
            if place_type and place.place_type != place_type:
                continue
            
            # Rating filter
            if min_rating and place.rating < min_rating:
                continue
            
            # Price level filter
            if price_level and place.price_level != price_level:
                continue
            
            # Opening hours filter
            if open_now and place.opening_hours:
                if not place.opening_hours.is_open_now():
                    continue
            
            # Text search (simple contains)
            if query:
                query_lower = query.lower()
                if not (
                    query_lower in place.name.lower() or
                    query_lower in (place.description or "").lower() or
                    query_lower in place.address.lower()
                ):
                    continue
            
            # Distance filter
            if latitude and longitude:
                distance = self._calculate_distance(
                    latitude, longitude,
                    place.latitude, place.longitude
                )
                if distance > radius_km:
                    continue
                place.distance_km = distance
            
            results.append(place)
            
            # Increment search count
            place.search_count += 1
        
        # Sort results
        if latitude and longitude:
            results.sort(key=lambda p: p.distance_km)
        else:
            results.sort(key=lambda p: p.rating, reverse=True)
        
        return results[:limit]
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        import math
        
        R = 6371  # Earth radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def add_review(self, place_id: str, review: Review) -> bool:
        """Add a review for a place"""
        try:
            if place_id not in self.reviews_db:
                self.reviews_db[place_id] = []
            
            self.reviews_db[place_id].append(review)
            
            # Update place rating
            place = self.places_db.get(place_id)
            if place:
                reviews = self.reviews_db[place_id]
                total_rating = sum(r.rating for r in reviews)
                place.rating = total_rating / len(reviews)
                place.review_count = len(reviews)
                place.updated_at = datetime.now()
                
                # Update in Elasticsearch
                if self.es_client:
                    await self.es_client.update(
                        index=self.es_index,
                        id=place_id,
                        body={"doc": {"rating": place.rating}}
                    )
            
            # Invalidate cache
            if self.cache_enabled:
                self.redis_client.delete(f"place:{place_id}")
                self.redis_client.delete(f"reviews:{place_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add review: {e}")
            return False
    
    async def get_reviews(self, place_id: str, limit: int = 10, offset: int = 0) -> List[Review]:
        """Get reviews for a place"""
        try:
            # Check cache
            cache_key = f"reviews:{place_id}:{limit}:{offset}"
            if self.cache_enabled:
                cached = self.redis_client.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return [Review(**r) for r in data]
            
            reviews = self.reviews_db.get(place_id, [])
            
            # Sort by creation date (newest first)
            reviews.sort(key=lambda r: r.created_at, reverse=True)
            
            result = reviews[offset:offset + limit]
            
            # Cache result
            if self.cache_enabled:
                self.redis_client.setex(
                    cache_key,
                    1800,  # 30 minutes
                    json.dumps([r.__dict__ for r in result], default=str)
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get reviews: {e}")
            return []
    
    async def get_popular_times(self, place_id: str) -> Optional[PopularTimes]:
        """Get popular times for a place"""
        return self.popular_times_db.get(place_id)
    
    async def update_popular_times(self, place_id: str, visit_data: Dict):
        """Update popular times based on visit data"""
        try:
            if place_id not in self.popular_times_db:
                self.popular_times_db[place_id] = PopularTimes(place_id=place_id)
            
            popular_times = self.popular_times_db[place_id]
            
            # Update based on visit data (simplified)
            day = visit_data.get('day', 'monday')
            hour = visit_data.get('hour', 12)
            
            if hasattr(popular_times, day) and 0 <= hour < 24:
                current_data = getattr(popular_times, day)
                current_data[hour] = min(100, current_data[hour] + 1)
            
        except Exception as e:
            logger.error(f"Failed to update popular times: {e}")
    
    async def get_place_photos(self, place_id: str) -> List[str]:
        """Get photos for a place"""
        place = await self.get_place(place_id)
        return place.photos if place else []
    
    async def add_place_photo(self, place_id: str, photo_url: str) -> bool:
        """Add a photo to a place"""
        try:
            place = self.places_db.get(place_id)
            if place:
                place.photos.append(photo_url)
                place.updated_at = datetime.now()
                
                # Invalidate cache
                if self.cache_enabled:
                    self.redis_client.delete(f"place:{place_id}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to add photo: {e}")
            return False
    
    async def _track_search(self, query: str, place_type: Optional[PlaceType], result_count: int):
        """Track search analytics"""
        try:
            key = f"search:{query}:{place_type.value if place_type else 'all'}"
            if key not in self.search_analytics:
                self.search_analytics[key] = {
                    'count': 0,
                    'total_results': 0,
                    'first_seen': datetime.now(),
                    'last_seen': datetime.now()
                }
            
            stats = self.search_analytics[key]
            stats['count'] += 1
            stats['total_results'] += result_count
            stats['last_seen'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to track search: {e}")
    
    async def get_trending_searches(self, limit: int = 10) -> List[Dict]:
        """Get trending search terms"""
        # Sort by search count
        trending = sorted(
            self.search_analytics.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        return [
            {
                'query': key.split(':')[1],
                'type': key.split(':')[2],
                'search_count': stats['count'],
                'avg_results': stats['total_results'] / stats['count'] if stats['count'] > 0 else 0
            }
            for key, stats in trending[:limit]
        ]
    
    async def close(self):
        """Cleanup places service"""
        if self.es_client:
            await self.es_client.close()
        if self.redis_client:
            self.redis_client.close()
        logger.info("Places service closed")