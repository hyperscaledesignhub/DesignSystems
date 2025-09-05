"""
Shared data models for microservices communication
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class URLRequest(BaseModel):
    """Request to process a URL"""
    url: str
    priority: int = Field(default=5, ge=0, le=10)
    crawl_delay: float = Field(default=1.0, ge=0)
    depth: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class URLBatch(BaseModel):
    """Batch of URLs for processing"""
    urls: List[URLRequest]
    batch_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class DownloadRequest(BaseModel):
    """Request to download content"""
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(default=30)
    retry_count: int = Field(default=3)


class DownloadResponse(BaseModel):
    """Downloaded content response"""
    url: str
    content: str
    status_code: int
    headers: Dict[str, str]
    download_time: float
    success: bool
    error: Optional[str] = None


class ParseRequest(BaseModel):
    """Request to parse HTML content"""
    url: str
    content: str
    extract_metadata: bool = True


class ParseResponse(BaseModel):
    """Parsed content response"""
    url: str
    title: Optional[str]
    text: str
    links: List[str]
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class DeduplicationRequest(BaseModel):
    """Request to check content duplication"""
    content: str
    url: str
    content_hash: Optional[str] = None


class DeduplicationResponse(BaseModel):
    """Deduplication check response"""
    is_duplicate: bool
    content_hash: str
    similarity_score: Optional[float] = None
    similar_urls: List[str] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    """Request to extract URLs from content"""
    url: str
    html_content: str
    base_url: Optional[str] = None


class ExtractResponse(BaseModel):
    """Extracted URLs response"""
    source_url: str
    extracted_urls: List[str]
    internal_urls: List[str]
    external_urls: List[str]
    total_count: int


class StorageRequest(BaseModel):
    """Request to store content"""
    url: str
    content: str
    content_type: str = "text/html"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StorageResponse(BaseModel):
    """Storage operation response"""
    url: str
    storage_path: str
    content_id: str
    success: bool
    error: Optional[str] = None


class CrawlStatus(BaseModel):
    """Overall crawl status"""
    crawl_id: str
    status: str
    pages_processed: int
    pages_queued: int
    duplicates_found: int
    errors_count: int
    start_time: datetime
    elapsed_time: float
    
    
class ServiceHealth(BaseModel):
    """Service health check response"""
    service_name: str
    status: ServiceStatus
    uptime: float
    version: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.now)