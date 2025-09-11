from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import re
import math

@dataclass
class MetricPoint:
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime
    
    def __post_init__(self):
        """Validate and sanitize data after initialization."""
        self.name = self._sanitize_metric_name(self.name)
        self.value = self._validate_metric_value(self.value)
        self.labels = self._sanitize_labels(self.labels)
        self.timestamp = self._validate_timestamp(self.timestamp)
    
    def _sanitize_metric_name(self, name: str) -> str:
        """Sanitize metric name to prevent injection attacks."""
        if not isinstance(name, str):
            raise ValueError("Metric name must be a string")
        
        # Remove any potentially dangerous characters
        sanitized = re.sub(r'[^\w\.-]', '_', name)
        
        # Ensure reasonable length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        if not sanitized:
            raise ValueError("Metric name cannot be empty")
        
        return sanitized
    
    def _validate_metric_value(self, value: float) -> float:
        """Validate metric value."""
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValueError("Metric value must be numeric")
        
        # Check for invalid float values
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Metric value cannot be NaN or infinity")
        
        return float(value)
    
    def _sanitize_labels(self, labels: Dict[str, str]) -> Dict[str, str]:
        """Sanitize label keys and values."""
        if not isinstance(labels, dict):
            raise ValueError("Labels must be a dictionary")
        
        sanitized_labels = {}
        for key, value in labels.items():
            # Sanitize key
            if not isinstance(key, str):
                continue
            
            sanitized_key = re.sub(r'[^\w\.-]', '_', key)[:50]  # Limit key length
            
            # Sanitize value
            if not isinstance(value, str):
                value = str(value)
            
            sanitized_value = str(value)[:100]  # Limit value length
            
            if sanitized_key and sanitized_value:
                sanitized_labels[sanitized_key] = sanitized_value
        
        # Limit number of labels
        if len(sanitized_labels) > 20:
            # Keep first 20 labels
            sanitized_labels = dict(list(sanitized_labels.items())[:20])
        
        return sanitized_labels
    
    def _validate_timestamp(self, timestamp: datetime) -> datetime:
        """Validate timestamp."""
        if not isinstance(timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")
        
        # Check if timestamp is reasonable (not too far in past/future)
        now = datetime.utcnow()
        max_age = 86400 * 30  # 30 days
        max_future = 3600  # 1 hour
        
        if (now - timestamp).total_seconds() > max_age:
            raise ValueError("Timestamp is too old")
        
        if (timestamp - now).total_seconds() > max_future:
            raise ValueError("Timestamp is too far in the future")
        
        return timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricPoint':
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        required_fields = ["name", "value", "timestamp"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Required field '{field}' is missing")
        
        try:
            timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            raise ValueError("Invalid timestamp format")
        
        return cls(
            name=data["name"],
            value=data["value"],
            labels=data.get("labels", {}),
            timestamp=timestamp
        )

@dataclass
class MetricsBatch:
    metrics: List[MetricPoint]
    source_host: str
    collection_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": [m.to_dict() for m in self.metrics],
            "source_host": self.source_host,
            "collection_time": self.collection_time.isoformat()
        }

class AlertSeverity(Enum):
    LOW = "low"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertState(Enum):
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"

@dataclass
class AlertRule:
    name: str
    metric_name: str
    threshold: float
    duration_minutes: int
    severity: AlertSeverity
    message: str
    labels: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "duration_minutes": self.duration_minutes,
            "severity": self.severity.value,
            "message": self.message,
            "labels": self.labels or {}
        }

@dataclass
class Alert:
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    state: AlertState
    severity: AlertSeverity
    message: str
    labels: Dict[str, str]
    started_at: datetime
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "state": self.state.value,
            "severity": self.severity.value,
            "message": self.message,
            "labels": self.labels,
            "started_at": self.started_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }