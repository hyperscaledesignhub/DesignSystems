"""
Traffic Service for real-time traffic management
Handles traffic conditions, incidents, and speed analysis
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json

logger = logging.getLogger(__name__)

class TrafficSeverity(Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    SEVERE = "severe"
    BLOCKED = "blocked"

@dataclass
class TrafficCondition:
    """Represents traffic condition on a road segment"""
    segment_id: str
    severity: TrafficSeverity
    speed_kmh: float
    normal_speed_kmh: float
    delay_minutes: float
    timestamp: datetime
    
@dataclass 
class TrafficIncident:
    """Represents a traffic incident"""
    incident_id: str
    type: str  # accident, construction, event, etc.
    severity: str
    location: Tuple[float, float]
    description: Optional[str]
    reporter_id: str
    timestamp: datetime
    cleared: bool = False

class TrafficService:
    """Service for traffic data management and analysis"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.active_incidents: Dict[str, TrafficIncident] = {}
        self.traffic_conditions: Dict[str, TrafficCondition] = {}
        self.speed_aggregations: Dict[str, List[float]] = {}
        
    async def initialize(self):
        """Initialize traffic service"""
        # Load historical traffic patterns
        # Initialize ML models for prediction
        logger.info("Traffic service initialized")
    
    async def analyze_location_batch(self, user_id: str, locations: List):
        """Analyze location batch for traffic patterns"""
        try:
            if len(locations) < 2:
                return
            
            # Calculate speeds between consecutive points
            for i in range(1, len(locations)):
                prev = locations[i-1]
                curr = locations[i]
                
                # Calculate speed
                time_diff = curr.timestamp - prev.timestamp
                if time_diff > 0:
                    # Simplified speed calculation
                    speed = curr.speed if hasattr(curr, 'speed') else 0
                    
                    # Aggregate speed data by geohash
                    geohash = self._get_geohash(curr.latitude, curr.longitude)
                    if geohash not in self.speed_aggregations:
                        self.speed_aggregations[geohash] = []
                    self.speed_aggregations[geohash].append(speed)
                    
                    # Update traffic conditions if significant change
                    await self._update_traffic_conditions(geohash, speed)
                    
        except Exception as e:
            logger.error(f"Traffic analysis error: {e}")
    
    async def _update_traffic_conditions(self, segment_id: str, current_speed: float):
        """Update traffic conditions for a segment"""
        # Get normal speed for this segment (from historical data)
        normal_speed = 50  # km/h default
        
        # Calculate severity based on speed reduction
        speed_ratio = current_speed / normal_speed if normal_speed > 0 else 1
        
        if speed_ratio > 0.8:
            severity = TrafficSeverity.LIGHT
        elif speed_ratio > 0.6:
            severity = TrafficSeverity.MODERATE
        elif speed_ratio > 0.4:
            severity = TrafficSeverity.HEAVY
        elif speed_ratio > 0.2:
            severity = TrafficSeverity.SEVERE
        else:
            severity = TrafficSeverity.BLOCKED
        
        # Calculate delay
        delay_minutes = (1 - speed_ratio) * 10  # Simplified calculation
        
        condition = TrafficCondition(
            segment_id=segment_id,
            severity=severity,
            speed_kmh=current_speed,
            normal_speed_kmh=normal_speed,
            delay_minutes=delay_minutes,
            timestamp=datetime.now()
        )
        
        self.traffic_conditions[segment_id] = condition
    
    async def get_area_traffic(self, lat: float, lng: float, radius_km: float) -> List[Dict]:
        """Get traffic conditions in an area"""
        conditions = []
        
        # Get conditions within radius (simplified)
        for segment_id, condition in self.traffic_conditions.items():
            # Check if within radius (simplified - would use proper distance calc)
            conditions.append({
                "segment_id": segment_id,
                "severity": condition.severity.value,
                "speed_kmh": condition.speed_kmh,
                "delay_minutes": condition.delay_minutes
            })
        
        return conditions
    
    async def report_incident(self, incident: TrafficIncident):
        """Report a new traffic incident"""
        self.active_incidents[incident.incident_id] = incident
        
        # Update affected segments
        affected_geohash = self._get_geohash(
            incident.location[0], 
            incident.location[1]
        )
        
        # Mark severe traffic in affected area
        await self._update_traffic_conditions(affected_geohash, 10)  # Very slow
        
        logger.info(f"Incident reported: {incident.incident_id}")
    
    async def get_traffic_factor(self, route_id: str) -> float:
        """Get traffic factor for a route (1.0 = normal, >1.0 = delays)"""
        # Simplified - would analyze all segments in route
        # For demo, return random factor
        import random
        return 1.0 + (random.random() * 0.5)  # 1.0 to 1.5
    
    async def get_overall_traffic_summary(self) -> Dict:
        """Get overall traffic summary"""
        summary = {
            "total_incidents": len(self.active_incidents),
            "active_incidents": len([i for i in self.active_incidents.values() if not i.cleared]),
            "conditions": {
                "light": 0,
                "moderate": 0,
                "heavy": 0,
                "severe": 0,
                "blocked": 0
            }
        }
        
        for condition in self.traffic_conditions.values():
            summary["conditions"][condition.severity.value] += 1
        
        return summary
    
    def _get_geohash(self, lat: float, lng: float, precision: int = 7) -> str:
        """Simple geohash generation"""
        # Simplified implementation
        return f"gh_{int(lat*1000)}_{int(lng*1000)}"
    
    async def close(self):
        """Cleanup traffic service"""
        logger.info("Traffic service closed")