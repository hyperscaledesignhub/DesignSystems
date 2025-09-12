import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import DCAwareRoundRobinPolicy
from cassandra.query import SimpleStatement
import math

from .models import (
    LocationUpdate, UserCurrentLocation, LocationWithTimestamp,
    DbLocationRecord, DbCurrentLocation, NearbyUser, Location, UserMode,
    db_record_to_location_with_timestamp, db_current_to_user_current_location
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages Cassandra database connections and operations for location data
    """
    
    def __init__(self, hosts: List[str], keyspace: str, username: str = None, password: str = None):
        self.hosts = hosts
        self.keyspace = keyspace
        self.username = username
        self.password = password
        self.cluster = None
        self.session = None
        
        # Prepared statements for better performance
        self.prepared_statements = {}
    
    async def connect(self):
        """Establish connection to Cassandra cluster"""
        try:
            # Setup authentication if provided
            auth_provider = None
            if self.username and self.password:
                auth_provider = PlainTextAuthProvider(
                    username=self.username,
                    password=self.password
                )
            
            # Create cluster with load balancing policy
            self.cluster = Cluster(
                self.hosts,
                auth_provider=auth_provider,
                load_balancing_policy=DCAwareRoundRobinPolicy(),
                protocol_version=4
            )
            
            # Connect to cluster
            self.session = self.cluster.connect()
            
            # Set keyspace
            self.session.set_keyspace(self.keyspace)
            
            # Prepare frequently used statements
            await self._prepare_statements()
            
            logger.info(f"Connected to Cassandra cluster: {self.hosts}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Cassandra: {e}")
            raise
    
    async def _prepare_statements(self):
        """Prepare frequently used SQL statements"""
        try:
            # Insert location statement
            self.prepared_statements['insert_location'] = self.session.prepare("""
                INSERT INTO user_locations (user_id, timestamp, latitude, longitude, 
                                          accuracy, user_mode, speed, bearing, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)
            
            # Update current location statement
            self.prepared_statements['update_current'] = self.session.prepare("""
                INSERT INTO user_current_location (user_id, latitude, longitude,
                                                 accuracy, user_mode, speed, bearing,
                                                 timestamp, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)
            
            # Get current location statement
            self.prepared_statements['get_current'] = self.session.prepare("""
                SELECT * FROM user_current_location WHERE user_id = ?
            """)
            
            # Get location history statement
            self.prepared_statements['get_history'] = self.session.prepare("""
                SELECT * FROM user_locations 
                WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """)
            
            # Insert batch metadata
            self.prepared_statements['insert_batch_meta'] = self.session.prepare("""
                INSERT INTO batch_metadata (batch_id, user_id, processed_count, 
                                          submitted_at, processed_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """)
            
            logger.info("Prepared statements created successfully")
            
        except Exception as e:
            logger.error(f"Failed to prepare statements: {e}")
            raise
    
    async def insert_location_batch(self, user_id: str, locations: List[LocationUpdate]) -> bool:
        """
        Insert a batch of location updates for a user
        """
        try:
            current_time = datetime.utcnow()
            latest_location = None
            latest_timestamp = 0
            
            # Insert all locations in the batch
            for location in locations:
                # Convert to database record
                db_record = DbLocationRecord(
                    user_id=user_id,
                    timestamp=location.timestamp,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    accuracy=location.accuracy,
                    user_mode=location.user_mode.value,
                    speed=location.speed,
                    bearing=location.bearing
                )
                
                # Execute insert
                self.session.execute(
                    self.prepared_statements['insert_location'],
                    [
                        db_record.user_id,
                        db_record.timestamp,
                        db_record.latitude,
                        db_record.longitude,
                        db_record.accuracy,
                        db_record.user_mode,
                        db_record.speed,
                        db_record.bearing,
                        db_record.created_at
                    ]
                )
                
                # Track the latest location for current location update
                if location.timestamp > latest_timestamp:
                    latest_timestamp = location.timestamp
                    latest_location = location
            
            # Update current location with the latest location from batch
            if latest_location:
                await self._update_current_location(user_id, latest_location, latest_timestamp)
            
            logger.info(f"Inserted {len(locations)} locations for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert location batch for user {user_id}: {e}")
            return False
    
    async def _update_current_location(self, user_id: str, location: LocationUpdate, timestamp: int):
        """Update the current location table"""
        try:
            self.session.execute(
                self.prepared_statements['update_current'],
                [
                    user_id,
                    location.latitude,
                    location.longitude,
                    location.accuracy,
                    location.user_mode.value,
                    location.speed,
                    location.bearing,
                    timestamp,
                    datetime.utcnow()
                ]
            )
        except Exception as e:
            logger.error(f"Failed to update current location for user {user_id}: {e}")
            raise
    
    async def get_current_location(self, user_id: str) -> Optional[UserCurrentLocation]:
        """
        Get the current location for a user
        """
        try:
            result = self.session.execute(
                self.prepared_statements['get_current'],
                [user_id]
            )
            
            row = result.one()
            if not row:
                return None
            
            # Convert to response model
            location = Location(
                latitude=row.latitude,
                longitude=row.longitude,
                accuracy=row.accuracy,
                user_mode=UserMode(row.user_mode),
                speed=row.speed,
                bearing=row.bearing
            )
            
            return UserCurrentLocation(
                user_id=row.user_id,
                location=location,
                last_updated=row.last_updated
            )
            
        except Exception as e:
            logger.error(f"Failed to get current location for user {user_id}: {e}")
            return None
    
    async def get_location_history(self, user_id: str, start_timestamp: int, 
                                 end_timestamp: int, limit: int = 100) -> List[LocationWithTimestamp]:
        """
        Get location history for a user within a time range
        """
        try:
            result = self.session.execute(
                self.prepared_statements['get_history'],
                [user_id, start_timestamp, end_timestamp, limit]
            )
            
            locations = []
            for row in result:
                location = LocationWithTimestamp(
                    latitude=row.latitude,
                    longitude=row.longitude,
                    accuracy=row.accuracy,
                    user_mode=UserMode(row.user_mode),
                    speed=row.speed,
                    bearing=row.bearing,
                    timestamp=datetime.fromtimestamp(row.timestamp)
                )
                locations.append(location)
            
            return locations
            
        except Exception as e:
            logger.error(f"Failed to get location history for user {user_id}: {e}")
            return []
    
    async def get_nearby_users(self, latitude: float, longitude: float, 
                             radius_km: float) -> List[NearbyUser]:
        """
        Get users within a specified radius (simplified implementation)
        Note: This is a basic implementation without geospatial indexing
        """
        try:
            # This is a simplified implementation
            # In production, you'd use geospatial queries or external services like Redis with GEO commands
            
            # Get recent active users (last hour)
            current_time = datetime.utcnow()
            one_hour_ago = current_time - timedelta(hours=1)
            
            # Query to get all users with recent activity
            query = SimpleStatement("""
                SELECT user_id, latitude, longitude, accuracy, user_mode, 
                       speed, bearing, last_updated
                FROM user_current_location
                WHERE last_updated >= ?
                ALLOW FILTERING
            """)
            
            result = self.session.execute(query, [one_hour_ago])
            
            nearby_users = []
            for row in result:
                # Calculate distance using Haversine formula
                distance = self._calculate_distance(
                    latitude, longitude, row.latitude, row.longitude
                )
                
                if distance <= radius_km:
                    location = Location(
                        latitude=row.latitude,
                        longitude=row.longitude,
                        accuracy=row.accuracy,
                        user_mode=UserMode(row.user_mode),
                        speed=row.speed,
                        bearing=row.bearing
                    )
                    
                    nearby_user = NearbyUser(
                        user_id=row.user_id,
                        location=location,
                        distance_km=distance,
                        last_updated=row.last_updated
                    )
                    nearby_users.append(nearby_user)
            
            # Sort by distance
            nearby_users.sort(key=lambda x: x.distance_km)
            
            return nearby_users
            
        except Exception as e:
            logger.error(f"Failed to get nearby users: {e}")
            return []
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    async def record_batch_metadata(self, batch_id: str, user_id: str, 
                                  processed_count: int, status: str = "pending"):
        """Record batch processing metadata"""
        try:
            current_time = datetime.utcnow()
            processed_at = current_time if status == "processed" else None
            
            self.session.execute(
                self.prepared_statements['insert_batch_meta'],
                [batch_id, user_id, processed_count, current_time, processed_at, status]
            )
            
        except Exception as e:
            logger.error(f"Failed to record batch metadata: {e}")
            raise
    
    async def get_location_metrics(self) -> Dict[str, Any]:
        """Get location service metrics"""
        try:
            metrics = {}
            
            # Get recent activity counts
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            # Count recent batches
            query = SimpleStatement("""
                SELECT COUNT(*) as batch_count
                FROM batch_metadata
                WHERE submitted_at >= ?
                ALLOW FILTERING
            """)
            
            result = self.session.execute(query, [one_hour_ago])
            row = result.one()
            metrics['recent_batches'] = row.batch_count if row else 0
            
            # Count active users
            query = SimpleStatement("""
                SELECT COUNT(*) as active_users
                FROM user_current_location
                WHERE last_updated >= ?
                ALLOW FILTERING
            """)
            
            result = self.session.execute(query, [one_hour_ago])
            row = result.one()
            metrics['active_users'] = row.active_users if row else 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get location metrics: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            # Simple query to check connectivity
            result = self.session.execute("SELECT now() FROM system.local")
            return result.one() is not None
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections"""
        try:
            if self.session:
                self.session.shutdown()
            if self.cluster:
                self.cluster.shutdown()
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
            raise