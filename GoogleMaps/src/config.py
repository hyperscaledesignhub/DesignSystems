import os
from typing import List
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """
    
    # Service configuration
    service_name: str = "location-service"
    service_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8765, env="PORT")  # Changed from 8080
    workers: int = Field(default=1, env="WORKERS")
    
    # Database configuration
    cassandra_hosts: str = Field(default="localhost", env="CASSANDRA_HOSTS")
    cassandra_port: int = Field(default=9042, env="CASSANDRA_PORT")  # Use actual Cassandra port
    cassandra_keyspace: str = Field(default="location_service", env="CASSANDRA_KEYSPACE")
    cassandra_username: str = Field(default="", env="CASSANDRA_USERNAME")
    cassandra_password: str = Field(default="", env="CASSANDRA_PASSWORD")
    
    # Connection pool settings
    cassandra_max_connections: int = Field(default=10, env="CASSANDRA_MAX_CONNECTIONS")
    cassandra_request_timeout: int = Field(default=30, env="CASSANDRA_REQUEST_TIMEOUT")
    
    # Batch processing configuration
    max_batch_size: int = Field(default=100, env="MAX_BATCH_SIZE")
    batch_timeout_seconds: int = Field(default=30, env="BATCH_TIMEOUT_SECONDS")
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    
    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=1000, env="RATE_LIMIT_RPM")
    rate_limit_burst: int = Field(default=100, env="RATE_LIMIT_BURST")
    
    # Data retention
    location_data_retention_days: int = Field(default=90, env="LOCATION_RETENTION_DAYS")
    batch_metadata_retention_days: int = Field(default=30, env="BATCH_METADATA_RETENTION_DAYS")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Monitoring and metrics
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9876, env="METRICS_PORT")  # Changed from 9090
    health_check_interval: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")
    
    # Security
    enable_auth: bool = Field(default=False, env="ENABLE_AUTH")
    jwt_secret_key: str = Field(default="your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # CORS settings
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Location validation settings
    max_location_age_seconds: int = Field(default=604800, env="MAX_LOCATION_AGE")  # 7 days
    max_future_location_seconds: int = Field(default=300, env="MAX_FUTURE_LOCATION")  # 5 minutes
    min_accuracy_meters: float = Field(default=0.0, env="MIN_ACCURACY_METERS")
    max_accuracy_meters: float = Field(default=10000.0, env="MAX_ACCURACY_METERS")
    max_speed_kmh: float = Field(default=300.0, env="MAX_SPEED_KMH")
    
    # Geospatial settings
    default_nearby_radius_km: float = Field(default=1.0, env="DEFAULT_NEARBY_RADIUS")
    max_nearby_radius_km: float = Field(default=50.0, env="MAX_NEARBY_RADIUS")
    max_nearby_users: int = Field(default=100, env="MAX_NEARBY_USERS")
    
    # Background task settings
    cleanup_schedule_hours: int = Field(default=24, env="CLEANUP_SCHEDULE_HOURS")
    metrics_collection_interval: int = Field(default=300, env="METRICS_INTERVAL")  # 5 minutes
    
    # Error handling
    max_error_retries: int = Field(default=3, env="MAX_ERROR_RETRIES")
    error_retry_delay_seconds: int = Field(default=1, env="ERROR_RETRY_DELAY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    
    def get_cassandra_config(self) -> dict:
        """Get Cassandra configuration as a dictionary"""
        hosts = [self.cassandra_hosts] if isinstance(self.cassandra_hosts, str) else self.cassandra_hosts
        return {
            'hosts': hosts,
            'port': self.cassandra_port,
            'keyspace': self.cassandra_keyspace,
            'username': self.cassandra_username,
            'password': self.cassandra_password,
            'max_connections': self.cassandra_max_connections,
            'request_timeout': self.cassandra_request_timeout
        }
    
    def get_logging_config(self) -> dict:
        """Get logging configuration"""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': self.log_format
                },
                'json': {
                    'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
                    'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
                }
            },
            'handlers': {
                'default': {
                    'level': self.log_level,
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout'
                }
            },
            'loggers': {
                '': {
                    'handlers': ['default'],
                    'level': self.log_level,
                    'propagate': False
                },
                'uvicorn': {
                    'handlers': ['default'],
                    'level': self.log_level,
                    'propagate': False
                },
                'cassandra': {
                    'handlers': ['default'],
                    'level': 'WARNING',  # Reduce Cassandra driver verbosity
                    'propagate': False
                }
            }
        }

# Create global settings instance
settings = Settings()

# Environment-specific configurations
class DevelopmentSettings(Settings):
    debug: bool = True
    log_level: str = "DEBUG"
    cassandra_hosts: str = "localhost"
    enable_auth: bool = False

class ProductionSettings(Settings):
    debug: bool = False
    log_level: str = "INFO"
    enable_auth: bool = True
    workers: int = 4
    # Production settings would typically come from environment variables

class TestSettings(Settings):
    debug: bool = True
    log_level: str = "DEBUG"
    cassandra_keyspace: str = "location_service_test"
    max_batch_size: int = 10
    enable_auth: bool = False

def get_settings() -> Settings:
    """
    Get settings based on environment
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()

# Update global settings based on environment
settings = get_settings()