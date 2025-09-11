import os
from typing import Dict, Any

class Config:
    # Service Discovery
    ETCD_HOST = os.getenv("ETCD_HOST", "localhost")
    ETCD_PORT = int(os.getenv("ETCD_PORT", "2379"))
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9293")
    KAFKA_TOPIC_METRICS = os.getenv("KAFKA_TOPIC_METRICS", "metrics-raw")
    KAFKA_TOPIC_ALERTS = os.getenv("KAFKA_TOPIC_ALERTS", "alerts")
    
    # InfluxDB Configuration
    INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8026")
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "admin-token")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "metrics-org")
    INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "metrics")
    
    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    
    # Service Ports
    METRICS_COLLECTOR_PORT = int(os.getenv("METRICS_COLLECTOR_PORT", "9847"))
    QUERY_SERVICE_PORT = int(os.getenv("QUERY_SERVICE_PORT", "7539"))
    ALERT_MANAGER_PORT = int(os.getenv("ALERT_MANAGER_PORT", "6428"))
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5317"))
    DATA_CONSUMER_PORT = int(os.getenv("DATA_CONSUMER_PORT", "4692"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # SMTP Configuration for alerts
    SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "alerts@metrics.local")
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {k: v for k, v in cls.__dict__.items() if not k.startswith('_')}

# Service-specific configurations
class MetricsCollectorConfig(Config):
    COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "30"))  # seconds
    METRICS_ENDPOINT = os.getenv("METRICS_ENDPOINT", "/metrics")
    
class DataConsumerConfig(Config):
    CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "metrics-writers")
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
    FLUSH_INTERVAL = int(os.getenv("FLUSH_INTERVAL", "10"))  # seconds
    
class QueryServiceConfig(Config):
    CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # seconds
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    
class AlertManagerConfig(Config):
    EVALUATION_INTERVAL = int(os.getenv("EVALUATION_INTERVAL", "60"))  # seconds
    ALERT_RULES_PATH = os.getenv("ALERT_RULES_PATH", "/app/rules.yaml")