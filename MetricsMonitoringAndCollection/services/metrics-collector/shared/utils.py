import logging
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import psutil
from functools import wraps
from shared.models import MetricPoint

def setup_logging(service_name: str, log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=f'%(asctime)s - {service_name} - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(service_name)

def get_system_metrics(hostname: str) -> list[MetricPoint]:
    """Collect basic system metrics."""
    now = datetime.utcnow()
    metrics = []
    
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    metrics.append(MetricPoint(
        name="cpu.usage",
        value=cpu_percent,
        labels={"host": hostname, "metric_type": "system"},
        timestamp=now
    ))
    
    # Memory metrics
    memory = psutil.virtual_memory()
    metrics.append(MetricPoint(
        name="memory.usage_percent",
        value=memory.percent,
        labels={"host": hostname, "metric_type": "system"},
        timestamp=now
    ))
    
    metrics.append(MetricPoint(
        name="memory.available_bytes",
        value=memory.available,
        labels={"host": hostname, "metric_type": "system"},
        timestamp=now
    ))
    
    # Disk metrics
    disk = psutil.disk_usage('/')
    disk_percent = (disk.used / disk.total) * 100
    metrics.append(MetricPoint(
        name="disk.usage_percent",
        value=disk_percent,
        labels={"host": hostname, "metric_type": "system", "mount": "/"},
        timestamp=now
    ))
    
    # Network metrics
    net_io = psutil.net_io_counters()
    metrics.append(MetricPoint(
        name="network.bytes_sent",
        value=net_io.bytes_sent,
        labels={"host": hostname, "metric_type": "system"},
        timestamp=now
    ))
    
    metrics.append(MetricPoint(
        name="network.bytes_recv",
        value=net_io.bytes_recv,
        labels={"host": hostname, "metric_type": "system"},
        timestamp=now
    ))
    
    return metrics

def serialize_metric(metric: MetricPoint) -> str:
    """Serialize a metric point to JSON string."""
    return json.dumps(metric.to_dict())

def deserialize_metric(data: str) -> MetricPoint:
    """Deserialize JSON string to metric point."""
    return MetricPoint.from_dict(json.loads(data))

class HealthChecker:
    def __init__(self):
        self.checks = {}
    
    def add_check(self, name: str, check_func):
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, Any]:
        results = {"healthy": True, "checks": {}}
        
        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                results["checks"][name] = {"status": "ok", "result": result}
            except Exception as e:
                results["checks"][name] = {"status": "error", "error": str(e)}
                results["healthy"] = False
        
        return results

async def retry_async(func, max_retries: int = 3, delay: float = 1.0):
    """Retry an async function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(delay * (2 ** attempt))

def validate_metric_data(data: Dict[str, Any]) -> bool:
    """Validate metric data structure."""
    try:
        # Check required fields
        required_fields = ["name", "value", "timestamp"]
        if not all(field in data for field in required_fields):
            return False
        
        # Validate data types
        if not isinstance(data["name"], str) or len(data["name"]) == 0:
            return False
        
        if not isinstance(data["value"], (int, float)):
            return False
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return False
        
        # Validate labels if present
        if "labels" in data:
            if not isinstance(data["labels"], dict):
                return False
            # Check label values are strings
            for key, value in data["labels"].items():
                if not isinstance(key, str) or not isinstance(value, str):
                    return False
        
        return True
    except Exception:
        return False

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        break
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        break
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def safe_get_system_metrics(hostname: str) -> List[MetricPoint]:
    """Safely collect system metrics with error handling."""
    metrics = []
    now = datetime.utcnow()
    
    try:
        # CPU metrics with error handling
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            if 0 <= cpu_percent <= 100:  # Validate range
                metrics.append(MetricPoint(
                    name="cpu.usage",
                    value=cpu_percent,
                    labels={"host": hostname, "metric_type": "system"},
                    timestamp=now
                ))
        except Exception as e:
            logging.warning(f"Failed to collect CPU metrics: {e}")
        
        # Memory metrics with error handling
        try:
            memory = psutil.virtual_memory()
            if hasattr(memory, 'percent') and hasattr(memory, 'available'):
                if 0 <= memory.percent <= 100:
                    metrics.append(MetricPoint(
                        name="memory.usage_percent",
                        value=memory.percent,
                        labels={"host": hostname, "metric_type": "system"},
                        timestamp=now
                    ))
                
                if memory.available >= 0:
                    metrics.append(MetricPoint(
                        name="memory.available_bytes",
                        value=memory.available,
                        labels={"host": hostname, "metric_type": "system"},
                        timestamp=now
                    ))
        except Exception as e:
            logging.warning(f"Failed to collect memory metrics: {e}")
        
        # Disk metrics with error handling
        try:
            disk = psutil.disk_usage('/')
            if hasattr(disk, 'used') and hasattr(disk, 'total') and disk.total > 0:
                disk_percent = (disk.used / disk.total) * 100
                if 0 <= disk_percent <= 100:
                    metrics.append(MetricPoint(
                        name="disk.usage_percent",
                        value=disk_percent,
                        labels={"host": hostname, "metric_type": "system", "mount": "/"},
                        timestamp=now
                    ))
        except Exception as e:
            logging.warning(f"Failed to collect disk metrics: {e}")
        
        # Network metrics with error handling
        try:
            net_io = psutil.net_io_counters()
            if hasattr(net_io, 'bytes_sent') and hasattr(net_io, 'bytes_recv'):
                if net_io.bytes_sent >= 0:
                    metrics.append(MetricPoint(
                        name="network.bytes_sent",
                        value=net_io.bytes_sent,
                        labels={"host": hostname, "metric_type": "system"},
                        timestamp=now
                    ))
                
                if net_io.bytes_recv >= 0:
                    metrics.append(MetricPoint(
                        name="network.bytes_recv",
                        value=net_io.bytes_recv,
                        labels={"host": hostname, "metric_type": "system"},
                        timestamp=now
                    ))
        except Exception as e:
            logging.warning(f"Failed to collect network metrics: {e}")
        
    except Exception as e:
        logging.error(f"Critical error in metrics collection: {e}")
    
    return metrics

# Alias for backward compatibility
get_system_metrics = safe_get_system_metrics

class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
    
    def is_allowed(self) -> bool:
        """Check if request is allowed."""
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        
        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False