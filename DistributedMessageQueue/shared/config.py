"""Shared configuration for all services."""
import os
from typing import List


class Config:
    """Base configuration class."""
    
    # Service ports - Using unfamiliar high ports
    BROKER_PORT = int(os.getenv("BROKER_PORT", "47283"))
    PRODUCER_PORT = int(os.getenv("PRODUCER_PORT", "52917"))
    CONSUMER_PORT = int(os.getenv("CONSUMER_PORT", "38694"))
    COORDINATOR_PORT = int(os.getenv("COORDINATOR_PORT", "61325"))
    GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "45871"))
    MONITORING_PORT = int(os.getenv("MONITORING_PORT", "33428"))
    
    # Service discovery
    COORDINATOR_HOST = os.getenv("COORDINATOR_HOST", "localhost")
    BROKER_HOSTS = os.getenv("BROKER_HOSTS", "localhost:47283").split(",")
    
    # Storage settings
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    MAX_SEGMENT_SIZE = int(os.getenv("MAX_SEGMENT_SIZE", "1073741824"))  # 1GB
    RETENTION_MS = int(os.getenv("RETENTION_MS", "604800000"))  # 7 days
    
    # Replication settings
    REPLICATION_FACTOR = int(os.getenv("REPLICATION_FACTOR", "3"))
    MIN_IN_SYNC_REPLICAS = int(os.getenv("MIN_IN_SYNC_REPLICAS", "2"))
    
    # Producer settings
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
    BATCH_TIMEOUT_MS = int(os.getenv("BATCH_TIMEOUT_MS", "100"))
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    
    # Consumer settings
    FETCH_TIMEOUT_MS = int(os.getenv("FETCH_TIMEOUT_MS", "5000"))
    AUTO_COMMIT_INTERVAL_MS = int(os.getenv("AUTO_COMMIT_INTERVAL_MS", "1000"))
    
    # Coordinator settings
    HEARTBEAT_INTERVAL_MS = int(os.getenv("HEARTBEAT_INTERVAL_MS", "10000"))
    SESSION_TIMEOUT_MS = int(os.getenv("SESSION_TIMEOUT_MS", "30000"))
    REBALANCE_TIMEOUT_MS = int(os.getenv("REBALANCE_TIMEOUT_MS", "60000"))
    
    # API Gateway settings
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    REQUEST_TIMEOUT_MS = int(os.getenv("REQUEST_TIMEOUT_MS", "30000"))
    
    # Monitoring settings
    METRICS_RETENTION_HOURS = int(os.getenv("METRICS_RETENTION_HOURS", "24"))
    SCRAPE_INTERVAL_MS = int(os.getenv("SCRAPE_INTERVAL_MS", "15000"))
    
    # Redis (optional for coordinator persistence)
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    USE_REDIS = os.getenv("USE_REDIS", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_broker_endpoints(cls) -> List[str]:
        """Get list of broker endpoints."""
        return [f"http://{host}" for host in cls.BROKER_HOSTS]
    
    @classmethod
    def get_coordinator_endpoint(cls) -> str:
        """Get coordinator endpoint."""
        return f"http://{cls.COORDINATOR_HOST}:{cls.COORDINATOR_PORT}"