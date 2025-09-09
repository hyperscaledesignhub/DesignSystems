"""Shared utilities for the message queue system."""
import hashlib
import json
import asyncio
import aiohttp
import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


logger = structlog.get_logger()


def hash_key(key: str, num_partitions: int) -> int:
    """Hash a key to determine partition."""
    if not key:
        return 0
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % num_partitions


def generate_broker_id() -> str:
    """Generate a unique broker ID."""
    import socket
    import time
    hostname = socket.gethostname()
    timestamp = int(time.time() * 1000)
    return f"{hostname}-{timestamp}"


def generate_consumer_id() -> str:
    """Generate a unique consumer ID."""
    import uuid
    return str(uuid.uuid4())


async def make_http_request(
    method: str,
    url: str,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retries: int = 3
) -> Optional[Dict[str, Any]]:
    """Make HTTP request with retries."""
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    "timeout": aiohttp.ClientTimeout(total=timeout),
                    "headers": {"Content-Type": "application/json"}
                }
                
                if data:
                    kwargs["json"] = data
                
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(
                            "HTTP request failed",
                            url=url,
                            status=response.status,
                            attempt=attempt + 1
                        )
        except Exception as e:
            logger.error(
                "HTTP request error",
                url=url,
                error=str(e),
                attempt=attempt + 1
            )
            
        if attempt < retries - 1:
            await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
    
    return None


async def broadcast_to_endpoints(
    endpoints: List[str],
    path: str,
    data: Dict[str, Any],
    method: str = "POST"
) -> List[Dict[str, Any]]:
    """Broadcast request to multiple endpoints."""
    tasks = []
    for endpoint in endpoints:
        url = f"{endpoint.rstrip('/')}/{path.lstrip('/')}"
        task = make_http_request(method, url, data)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successful_results = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                "Broadcast request failed",
                endpoint=endpoints[i],
                error=str(result)
            )
        elif result is not None:
            successful_results.append(result)
    
    return successful_results


def ensure_directory(path: str) -> Path:
    """Ensure directory exists and return Path object."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def serialize_message(message: Dict[str, Any]) -> bytes:
    """Serialize message to bytes."""
    return json.dumps(message, default=str).encode('utf-8')


def deserialize_message(data: bytes) -> Dict[str, Any]:
    """Deserialize message from bytes."""
    return json.loads(data.decode('utf-8'))


def calculate_partition_for_key(key: Optional[str], num_partitions: int) -> int:
    """Calculate partition for a given key."""
    if key is None:
        # Round-robin for messages without keys
        import time
        return int(time.time() * 1000) % num_partitions
    return hash_key(key, num_partitions)


class AsyncFileWriter:
    """Async file writer for WAL."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the file exists."""
        Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
        if not Path(self.file_path).exists():
            Path(self.file_path).touch()
    
    async def append(self, data: str) -> None:
        """Append data to file."""
        import aiofiles
        async with aiofiles.open(self.file_path, 'a') as f:
            await f.write(data + '\n')
            await f.flush()
    
    async def read_lines(self, start_line: int = 0, limit: Optional[int] = None) -> List[str]:
        """Read lines from file."""
        import aiofiles
        lines = []
        try:
            async with aiofiles.open(self.file_path, 'r') as f:
                current_line = 0
                async for line in f:
                    if current_line >= start_line:
                        lines.append(line.strip())
                        if limit and len(lines) >= limit:
                            break
                    current_line += 1
        except FileNotFoundError:
            pass
        return lines


class CircuitBreaker:
    """Simple circuit breaker implementation."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).seconds >= self.timeout:
                self.state = "half-open"
                return True
            return False
        elif self.state == "half-open":
            return True
        return False
    
    def record_success(self):
        """Record successful execution."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"