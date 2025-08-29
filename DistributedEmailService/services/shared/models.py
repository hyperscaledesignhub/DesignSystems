from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EmailPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class EmailStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    READ = "read"
    ARCHIVED = "archived"
    DELETED = "deleted"
    SPAM = "spam"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"

class NotificationType(str, Enum):
    EMAIL_RECEIVED = "email_received"
    EMAIL_SENT = "email_sent"
    SPAM_DETECTED = "spam_detected"
    ATTACHMENT_UPLOADED = "attachment_uploaded"
    SYSTEM_ALERT = "system_alert"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    created_at: datetime
    is_active: bool = True
    storage_used: int = 0
    storage_limit: int = 5368709120  # 5GB default

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class EmailCreate(BaseModel):
    to_recipients: List[EmailStr]
    cc_recipients: Optional[List[EmailStr]] = []
    bcc_recipients: Optional[List[EmailStr]] = []
    subject: str
    body: str
    html_body: Optional[str] = None
    priority: EmailPriority = EmailPriority.NORMAL
    is_draft: bool = False
    attachment_ids: Optional[List[str]] = []
    labels: Optional[List[str]] = []
    scheduled_at: Optional[datetime] = None

class EmailUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    html_body: Optional[str] = None
    status: Optional[EmailStatus] = None
    labels: Optional[List[str]] = None
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None

class EmailResponse(BaseModel):
    id: str
    from_email: str
    to_recipients: List[str]
    cc_recipients: List[str]
    bcc_recipients: List[str]
    subject: str
    body: str
    html_body: Optional[str]
    status: EmailStatus
    priority: EmailPriority
    is_read: bool = False
    is_starred: bool = False
    spam_score: float = 0.0
    labels: List[str]
    attachments: List[Dict[str, Any]]
    created_at: datetime
    sent_at: Optional[datetime]
    thread_id: Optional[str]
    folder: str = "inbox"

class AttachmentCreate(BaseModel):
    filename: str
    content_type: str
    size: int
    email_id: Optional[str] = None

class AttachmentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    url: str
    uploaded_at: datetime
    email_id: Optional[str]

class NotificationCreate(BaseModel):
    user_id: str
    type: NotificationType
    title: str
    message: str
    data: Optional[Dict[str, Any]] = {}
    priority: str = "normal"

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    data: Dict[str, Any]
    is_read: bool = False
    created_at: datetime

class SpamCheckRequest(BaseModel):
    subject: str
    body: str
    from_email: str
    to_emails: List[str]
    attachments: Optional[List[str]] = []

class SpamCheckResponse(BaseModel):
    is_spam: bool
    spam_score: float
    reasons: List[str]
    confidence: float

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = {}
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

class SearchResponse(BaseModel):
    total: int
    results: List[EmailResponse]
    facets: Dict[str, Any]
    took_ms: int

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

class FolderResponse(BaseModel):
    id: str
    name: str
    parent_id: Optional[str]
    email_count: int
    unread_count: int
    color: Optional[str]
    icon: Optional[str]
    created_at: datetime

class FilterRule(BaseModel):
    name: str
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    is_active: bool = True

class EmailThread(BaseModel):
    id: str
    subject: str
    participants: List[str]
    email_count: int
    last_email_at: datetime
    is_read: bool
    labels: List[str]