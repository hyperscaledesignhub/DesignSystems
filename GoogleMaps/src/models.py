from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

class UserMode(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BACKGROUND = "background"

class LocationUpdate(BaseModel):
    """Single location update from client"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    timestamp: int = Field(..., description="Unix timestamp in seconds")
    accuracy: Optional[float] = Field(None, ge=0, description="Location accuracy in meters")
    user_mode: UserMode = Field(default=UserMode.ACTIVE, description="User activity mode")
    speed: Optional[float] = Field(None, ge=0, description="Speed in meters per second")
    bearing: Optional[float] = Field(None, ge=0, le=360, description="Direction of travel in degrees")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        # Ensure timestamp is not too far in the future or past
        current_time = int(datetime.utcnow().timestamp())
        max_future = current_time + 300  # 5 minutes in future
        min_past = current_time - 86400 * 7  # 7 days in past
        
        if v > max_future:
            raise ValueError('Timestamp cannot be more than 5 minutes in the future')
        if v < min_past:
            raise ValueError('Timestamp cannot be more than 7 days in the past')
        
        return v

class LocationBatch(BaseModel):
    """Batch of location updates from a single user"""
    user_id: str = Field(..., min_length=1, max_length=100, description="Unique user identifier")
    locations: List[LocationUpdate] = Field(..., min_items=1, max_items=100, description="List of location updates")
    
    @validator('locations')
    def validate_locations_chronological(cls, v):
        # Ensure locations are in chronological order
        timestamps = [loc.timestamp for loc in v]
        if timestamps != sorted(timestamps):
            raise ValueError('Location updates must be in chronological order')
        return v

class Location(BaseModel):
    """Location data without timestamp"""
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    user_mode: UserMode = UserMode.ACTIVE
    speed: Optional[float] = None
    bearing: Optional[float] = None

class LocationWithTimestamp(Location):
    """Location with timestamp for historical data"""
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserCurrentLocation(BaseModel):
    """Current location response for a user"""
    user_id: str
    location: Location
    last_updated: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class LocationHistory(BaseModel):
    """Location history response"""
    user_id: str
    locations: List[LocationWithTimestamp]
    total_count: int
    start_time: datetime
    end_time: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BatchMetadata(BaseModel):
    """Metadata for tracking batch processing"""
    batch_id: str
    user_id: str
    processed_count: int
    submitted_at: datetime
    processed_at: Optional[datetime] = None
    status: str  # 'pending', 'processed', 'failed'

class LocationMetric(BaseModel):
    """Metrics for monitoring location service"""
    metric_date: datetime
    hour: int
    metric_name: str
    metric_value: int

class NearbyUser(BaseModel):
    """Nearby user information"""
    user_id: str
    location: Location
    distance_km: float
    last_updated: datetime

class ServiceHealth(BaseModel):
    """Service health status"""
    status: str
    timestamp: datetime
    service: str
    version: str
    database_healthy: bool
    
class BatchProcessingResponse(BaseModel):
    """Response for batch processing request"""
    status: str
    batch_id: str
    processed_count: int
    message: str

# Database models (for internal use)
class DbLocationRecord:
    """Database record for location data"""
    def __init__(self, user_id: str, timestamp: int, latitude: float, longitude: float,
                 accuracy: Optional[float] = None, user_mode: str = "active",
                 speed: Optional[float] = None, bearing: Optional[float] = None):
        self.user_id = user_id
        self.timestamp = timestamp
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.user_mode = user_mode
        self.speed = speed
        self.bearing = bearing
        self.created_at = datetime.utcnow()

class DbCurrentLocation:
    """Database record for current location"""
    def __init__(self, user_id: str, latitude: float, longitude: float,
                 accuracy: Optional[float] = None, user_mode: str = "active",
                 speed: Optional[float] = None, bearing: Optional[float] = None,
                 timestamp: int = None):
        self.user_id = user_id
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.user_mode = user_mode
        self.speed = speed
        self.bearing = bearing
        self.timestamp = timestamp or int(datetime.utcnow().timestamp())
        self.last_updated = datetime.utcnow()

# Utility functions for model conversion
def location_update_to_db_record(user_id: str, location: LocationUpdate) -> DbLocationRecord:
    """Convert LocationUpdate to database record"""
    return DbLocationRecord(
        user_id=user_id,
        timestamp=location.timestamp,
        latitude=location.latitude,
        longitude=location.longitude,
        accuracy=location.accuracy,
        user_mode=location.user_mode.value,
        speed=location.speed,
        bearing=location.bearing
    )

def db_record_to_location_with_timestamp(record) -> LocationWithTimestamp:
    """Convert database record to LocationWithTimestamp"""
    return LocationWithTimestamp(
        latitude=record.latitude,
        longitude=record.longitude,
        accuracy=record.accuracy,
        user_mode=UserMode(record.user_mode),
        speed=record.speed,
        bearing=record.bearing,
        timestamp=datetime.fromtimestamp(record.timestamp)
    )

def db_current_to_user_current_location(record) -> UserCurrentLocation:
    """Convert database current location to UserCurrentLocation"""
    location = Location(
        latitude=record.latitude,
        longitude=record.longitude,
        accuracy=record.accuracy,
        user_mode=UserMode(record.user_mode),
        speed=record.speed,
        bearing=record.bearing
    )
    
    return UserCurrentLocation(
        user_id=record.user_id,
        location=location,
        last_updated=record.last_updated
    )