#!/usr/bin/env python3
"""
Centralized logging utilities for the distributed database system
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

# Try to import config, but provide defaults if not available
try:
    from config.yaml_config import yaml_config
    CONFIG_AVAILABLE = True
except (ImportError, FileNotFoundError):
    CONFIG_AVAILABLE = False
    # Default logging configuration
    DEFAULT_LOGGING_CONFIG = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S'
    }

def setup_logging(node_id: Optional[str] = None, log_level: Optional[str] = None) -> logging.Logger:
    """
    Setup centralized logging for the distributed database system.
    
    Args:
        node_id: Optional node ID to include in log filename
        log_level: Optional log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Get logging configuration from config file
    logging_config = yaml_config.get_logging_config()
    
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level_str = logging_config.get('level', 'INFO')
        level = getattr(logging, level_str.upper(), logging.INFO)
    
    # Create timestamp for log files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create log filename
    if node_id:
        log_filename = f"{logs_dir}/{node_id}_{timestamp}.log"
        error_log_filename = f"{logs_dir}/{node_id}_{timestamp}_error.log"
    else:
        log_filename = f"{logs_dir}/system_{timestamp}.log"
        error_log_filename = f"{logs_dir}/system_{timestamp}_error.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler for all logs (with rotation)
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # File handler for error logs only
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_filename,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Console handler for INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Create and return a logger for the calling module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {logging.getLevelName(level)}")
    logger.info(f"Log files: {log_filename}, {error_log_filename}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def log_node_startup(node_id: str, host: str, port: int, data_dir: Optional[str] = None):
    """
    Log node startup information.
    
    Args:
        node_id: Node identifier
        host: Host address
        port: Port number
        data_dir: Optional data directory
    """
    logger = get_logger(__name__)
    logger.info(f"🚀 Starting node {node_id} on {host}:{port}")
    if data_dir:
        logger.info(f"📁 Data directory: {data_dir}")
    logger.info(f"🔧 Node configuration loaded successfully")

def log_node_shutdown(node_id: str):
    """
    Log node shutdown information.
    
    Args:
        node_id: Node identifier
    """
    logger = get_logger(__name__)
    logger.info(f"🛑 Shutting down node {node_id}")

def log_cluster_event(event_type: str, details: str, node_id: Optional[str] = None):
    """
    Log cluster-related events.
    
    Args:
        event_type: Type of event (join, leave, sync, etc.)
        details: Event details
        node_id: Optional node identifier
    """
    logger = get_logger(__name__)
    if node_id:
        logger.info(f"🔗 [{event_type.upper()}] Node {node_id}: {details}")
    else:
        logger.info(f"🔗 [{event_type.upper()}] {details}")

def log_anti_entropy_event(event_type: str, details: str, node_id: Optional[str] = None):
    """
    Log anti-entropy related events.
    
    Args:
        event_type: Type of anti-entropy event
        details: Event details
        node_id: Optional node identifier
    """
    logger = get_logger(__name__)
    if node_id:
        logger.info(f"🔄 [ANTI-ENTROPY] Node {node_id} - {event_type}: {details}")
    else:
        logger.info(f"🔄 [ANTI-ENTROPY] {event_type}: {details}")

def log_persistence_event(event_type: str, details: str, node_id: Optional[str] = None):
    """
    Log persistence related events.
    
    Args:
        event_type: Type of persistence event
        details: Event details
        node_id: Optional node identifier
    """
    logger = get_logger(__name__)
    if node_id:
        logger.info(f"💾 [PERSISTENCE] Node {node_id} - {event_type}: {details}")
    else:
        logger.info(f"💾 [PERSISTENCE] {event_type}: {details}")

def log_hash_ring_event(event_type: str, details: str, node_id: Optional[str] = None):
    """
    Log hash ring related events.
    
    Args:
        event_type: Type of hash ring event
        details: Event details
        node_id: Optional node identifier
    """
    logger = get_logger(__name__)
    if node_id:
        logger.info(f"🔗 [HASH_RING] Node {node_id} - {event_type}: {details}")
    else:
        logger.info(f"🔗 [HASH_RING] {event_type}: {details}")

def log_error(error_type: str, error_message: str, node_id: Optional[str] = None, exception: Optional[Exception] = None):
    """
    Log error events.
    
    Args:
        error_type: Type of error
        error_message: Error message
        node_id: Optional node identifier
        exception: Optional exception object
    """
    logger = get_logger(__name__)
    if node_id:
        logger.error(f"❌ [{error_type.upper()}] Node {node_id}: {error_message}")
    else:
        logger.error(f"❌ [{error_type.upper()}] {error_message}")
    
    if exception:
        logger.exception(f"Exception details for {error_type}")

def log_performance(operation: str, duration: float, node_id: Optional[str] = None, additional_info: Optional[str] = None):
    """
    Log performance metrics.
    
    Args:
        operation: Operation name
        duration: Duration in seconds
        node_id: Optional node identifier
        additional_info: Optional additional information
    """
    logger = get_logger(__name__)
    if node_id:
        logger.info(f"⚡ [PERF] Node {node_id} - {operation}: {duration:.3f}s")
    else:
        logger.info(f"⚡ [PERF] {operation}: {duration:.3f}s")
    
    if additional_info:
        logger.info(f"   Additional info: {additional_info}") 