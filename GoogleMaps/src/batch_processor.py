import asyncio
import logging
from typing import List
from datetime import datetime

from .models import LocationUpdate
from .database import DatabaseManager

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    Handles batch processing of location updates
    """
    
    def __init__(self, db_manager: DatabaseManager, max_retries: int = 3):
        self.db_manager = db_manager
        self.max_retries = max_retries
        self.processing_queue = asyncio.Queue()
        self.stats = {
            'total_batches_processed': 0,
            'total_locations_processed': 0,
            'failed_batches': 0,
            'last_processed_at': None
        }
    
    async def process_location_batch(self, batch_id: str, user_id: str, locations: List[LocationUpdate]):
        """
        Process a batch of location updates
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Processing batch {batch_id} for user {user_id} with {len(locations)} locations")
            
            # Record batch metadata as pending
            await self.db_manager.record_batch_metadata(
                batch_id, user_id, len(locations), "pending"
            )
            
            # Validate and clean locations
            valid_locations = self._validate_locations(locations)
            
            if not valid_locations:
                logger.warning(f"No valid locations in batch {batch_id}")
                await self.db_manager.record_batch_metadata(
                    batch_id, user_id, 0, "failed"
                )
                return False
            
            # Insert locations with retry logic
            success = await self._insert_with_retry(user_id, valid_locations)
            
            if success:
                # Update batch metadata as processed
                await self.db_manager.record_batch_metadata(
                    batch_id, user_id, len(valid_locations), "processed"
                )
                
                # Update stats
                self.stats['total_batches_processed'] += 1
                self.stats['total_locations_processed'] += len(valid_locations)
                self.stats['last_processed_at'] = datetime.utcnow()
                
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Successfully processed batch {batch_id} in {processing_time:.2f}s")
                
                return True
            else:
                # Mark as failed
                await self.db_manager.record_batch_metadata(
                    batch_id, user_id, 0, "failed"
                )
                self.stats['failed_batches'] += 1
                
                logger.error(f"Failed to process batch {batch_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {e}")
            
            # Mark as failed
            try:
                await self.db_manager.record_batch_metadata(
                    batch_id, user_id, 0, "failed"
                )
            except:
                pass  # Don't fail on metadata update error
            
            self.stats['failed_batches'] += 1
            return False
    
    def _validate_locations(self, locations: List[LocationUpdate]) -> List[LocationUpdate]:
        """
        Validate and clean location data
        """
        valid_locations = []
        
        for location in locations:
            try:
                # Basic validation (Pydantic should handle most of this)
                if self._is_valid_location(location):
                    valid_locations.append(location)
                else:
                    logger.warning(f"Invalid location data: {location}")
            except Exception as e:
                logger.warning(f"Error validating location: {e}")
                continue
        
        # Remove duplicates based on timestamp
        valid_locations = self._remove_duplicate_timestamps(valid_locations)
        
        # Sort by timestamp to ensure chronological order
        valid_locations.sort(key=lambda x: x.timestamp)
        
        return valid_locations
    
    def _is_valid_location(self, location: LocationUpdate) -> bool:
        """
        Validate individual location update
        """
        # Check latitude bounds
        if not (-90 <= location.latitude <= 90):
            return False
        
        # Check longitude bounds
        if not (-180 <= location.longitude <= 180):
            return False
        
        # Check timestamp is reasonable (not too far in past/future)
        current_time = int(datetime.utcnow().timestamp())
        time_diff = abs(current_time - location.timestamp)
        
        # Allow up to 7 days in the past or 5 minutes in the future
        if time_diff > 7 * 24 * 3600 and location.timestamp < current_time:  # Past
            return False
        if time_diff > 300 and location.timestamp > current_time:  # Future
            return False
        
        # Check accuracy if provided
        if location.accuracy is not None and location.accuracy < 0:
            return False
        
        # Check speed if provided
        if location.speed is not None and location.speed < 0:
            return False
        
        # Check bearing if provided
        if location.bearing is not None and not (0 <= location.bearing <= 360):
            return False
        
        return True
    
    def _remove_duplicate_timestamps(self, locations: List[LocationUpdate]) -> List[LocationUpdate]:
        """
        Remove locations with duplicate timestamps, keeping the last one
        """
        timestamp_map = {}
        
        for location in locations:
            timestamp_map[location.timestamp] = location
        
        return list(timestamp_map.values())
    
    async def _insert_with_retry(self, user_id: str, locations: List[LocationUpdate]) -> bool:
        """
        Insert locations with retry logic
        """
        for attempt in range(self.max_retries):
            try:
                success = await self.db_manager.insert_location_batch(user_id, locations)
                
                if success:
                    return True
                else:
                    logger.warning(f"Insert attempt {attempt + 1} failed for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Insert attempt {attempt + 1} error for user {user_id}: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s...
                await asyncio.sleep(wait_time)
        
        logger.error(f"Failed to insert locations for user {user_id} after {self.max_retries} attempts")
        return False
    
    def get_stats(self) -> dict:
        """
        Get processing statistics
        """
        return self.stats.copy()
    
    async def process_delayed_batches(self):
        """
        Process any batches that might have been delayed or failed
        This could be run as a background task
        """
        try:
            # Implementation would query for batches with status 'pending' 
            # that are older than a certain threshold and retry them
            logger.info("Checking for delayed batches...")
            
            # This is a placeholder for the actual implementation
            # You would query the batch_metadata table for old pending batches
            # and reprocess them
            
        except Exception as e:
            logger.error(f"Error processing delayed batches: {e}")
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Cleanup old location data (can be run as a scheduled task)
        """
        try:
            logger.info(f"Starting cleanup of location data older than {days_to_keep} days")
            
            # Calculate cutoff timestamp
            cutoff_time = datetime.utcnow().timestamp() - (days_to_keep * 24 * 3600)
            
            # This would implement the actual cleanup logic
            # For Cassandra, you might use TTL on the table or manual deletion
            
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

class BatchValidator:
    """
    Additional validation utilities for batch processing
    """
    
    @staticmethod
    def validate_batch_size(locations: List[LocationUpdate], max_size: int = 100) -> bool:
        """Validate batch size is within limits"""
        return 1 <= len(locations) <= max_size
    
    @staticmethod
    def validate_time_sequence(locations: List[LocationUpdate]) -> bool:
        """Validate that locations are in chronological order"""
        timestamps = [loc.timestamp for loc in locations]
        return timestamps == sorted(timestamps)
    
    @staticmethod
    def detect_anomalies(locations: List[LocationUpdate]) -> List[str]:
        """
        Detect potential anomalies in location data
        Returns list of warning messages
        """
        warnings = []
        
        if len(locations) < 2:
            return warnings
        
        for i in range(1, len(locations)):
            prev_loc = locations[i-1]
            curr_loc = locations[i]
            
            # Check for impossible speed
            time_diff = curr_loc.timestamp - prev_loc.timestamp
            if time_diff > 0:
                # Calculate distance (simplified)
                lat_diff = abs(curr_loc.latitude - prev_loc.latitude)
                lon_diff = abs(curr_loc.longitude - prev_loc.longitude)
                
                # Rough distance calculation (not accurate for large distances)
                distance_deg = (lat_diff ** 2 + lon_diff ** 2) ** 0.5
                distance_km = distance_deg * 111  # Rough conversion
                
                speed_kmh = (distance_km / time_diff) * 3600
                
                # Flag if speed > 300 km/h (unrealistic for ground transport)
                if speed_kmh > 300:
                    warnings.append(
                        f"Unrealistic speed detected: {speed_kmh:.1f} km/h "
                        f"between timestamps {prev_loc.timestamp} and {curr_loc.timestamp}"
                    )
            
            # Check for duplicate coordinates
            if (prev_loc.latitude == curr_loc.latitude and 
                prev_loc.longitude == curr_loc.longitude and
                time_diff > 600):  # Same location for > 10 minutes
                warnings.append(
                    f"Extended stationary period detected at "
                    f"({curr_loc.latitude}, {curr_loc.longitude})"
                )
        
        return warnings