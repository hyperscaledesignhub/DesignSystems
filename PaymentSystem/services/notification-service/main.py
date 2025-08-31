"""
Notification Service - Handles email, SMS, and webhook notifications
"""
import os
import sys
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import httpx
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aio_pika
from collections import defaultdict

# Import tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing
tracer = setup_tracing("notification-service")

# Create FastAPI app
app = FastAPI(title="Notification Service", version="1.0.0")
instrument_fastapi(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database and RabbitMQ connections
db_pool: Optional[asyncpg.Pool] = None
rabbitmq_connection: Optional[aio_pika.Connection] = None
rabbitmq_channel: Optional[aio_pika.Channel] = None

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
    
    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_text(message)
                except:
                    pass
    
    async def broadcast(self, message: str):
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()

# Pydantic models
class NotificationRequest(BaseModel):
    type: str  # email, sms, webhook, push, in_app
    recipient: str
    subject: Optional[str] = None
    template: Optional[str] = None
    data: Dict[str, Any]
    priority: str = "normal"  # low, normal, high, critical
    schedule_at: Optional[datetime] = None
    retry_count: int = 3

class NotificationResponse(BaseModel):
    notification_id: str
    status: str
    created_at: datetime
    scheduled_at: Optional[datetime]

class NotificationStatus(BaseModel):
    notification_id: str
    type: str
    recipient: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime]
    failed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int

class NotificationTemplate(BaseModel):
    template_id: str
    name: str
    type: str
    subject: Optional[str]
    body: str
    variables: List[str]
    active: bool

class WebhookConfig(BaseModel):
    webhook_id: str
    url: str
    events: List[str]
    active: bool
    secret: Optional[str]
    headers: Optional[Dict[str, str]]

async def get_db_pool():
    """Get database connection pool"""
    return db_pool

@app.on_event("startup")
async def startup():
    """Initialize database and message queue connections"""
    global db_pool, rabbitmq_connection, rabbitmq_channel
    
    with tracer.start_as_current_span("service_startup"):
        # Connect to PostgreSQL
        db_url = os.getenv("DATABASE_URL", "postgresql://notification_user:notification_pass@postgres-notification:5432/notification_db")
        db_pool = await asyncpg.create_pool(db_url, min_size=5, max_size=20)
        
        # Initialize database schema
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id VARCHAR(50) PRIMARY KEY,
                    type VARCHAR(20) NOT NULL,
                    recipient VARCHAR(255) NOT NULL,
                    subject VARCHAR(255),
                    content TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    priority VARCHAR(20) DEFAULT 'normal',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scheduled_at TIMESTAMP,
                    sent_at TIMESTAMP,
                    failed_at TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
                CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient);
                CREATE INDEX IF NOT EXISTS idx_notifications_scheduled ON notifications(scheduled_at) WHERE scheduled_at IS NOT NULL;
                
                CREATE TABLE IF NOT EXISTS notification_templates (
                    template_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    type VARCHAR(20) NOT NULL,
                    subject VARCHAR(255),
                    body TEXT NOT NULL,
                    variables TEXT[],
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS webhook_configs (
                    webhook_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(50),
                    url VARCHAR(500) NOT NULL,
                    events TEXT[] NOT NULL,
                    active BOOLEAN DEFAULT TRUE,
                    secret VARCHAR(255),
                    headers JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered_at TIMESTAMP,
                    failure_count INTEGER DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_webhooks_user ON webhook_configs(user_id);
                CREATE INDEX IF NOT EXISTS idx_webhooks_events ON webhook_configs USING GIN(events);
                
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    user_id VARCHAR(50) PRIMARY KEY,
                    email_enabled BOOLEAN DEFAULT TRUE,
                    sms_enabled BOOLEAN DEFAULT TRUE,
                    push_enabled BOOLEAN DEFAULT TRUE,
                    webhook_enabled BOOLEAN DEFAULT TRUE,
                    quiet_hours_start TIME,
                    quiet_hours_end TIME,
                    preferred_channels TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Insert default templates
            await conn.execute("""
                INSERT INTO notification_templates (template_id, name, type, subject, body, variables)
                VALUES 
                    ('TPL001', 'payment_success', 'email', 'Payment Successful', 
                     'Your payment of {{amount}} {{currency}} has been processed successfully. Transaction ID: {{transaction_id}}',
                     ARRAY['amount', 'currency', 'transaction_id']),
                    ('TPL002', 'payment_failed', 'email', 'Payment Failed',
                     'Your payment of {{amount}} {{currency}} has failed. Reason: {{reason}}. Please try again.',
                     ARRAY['amount', 'currency', 'reason']),
                    ('TPL003', 'payment_refund', 'email', 'Refund Processed',
                     'Your refund of {{amount}} {{currency}} has been processed. It will be credited within 3-5 business days.',
                     ARRAY['amount', 'currency']),
                    ('TPL004', 'fraud_alert', 'email', 'Suspicious Activity Detected',
                     'We detected suspicious activity on your account. Transaction {{transaction_id}} has been flagged for review.',
                     ARRAY['transaction_id']),
                    ('TPL005', 'wallet_low_balance', 'email', 'Low Wallet Balance',
                     'Your wallet balance is low. Current balance: {{balance}} {{currency}}. Consider topping up.',
                     ARRAY['balance', 'currency']),
                    ('TPL006', 'payment_reminder', 'sms',  NULL,
                     'Payment reminder: {{amount}} {{currency}} due on {{due_date}}. Pay now to avoid late fees.',
                     ARRAY['amount', 'currency', 'due_date'])
                ON CONFLICT (template_id) DO NOTHING
            """)
        
        # Connect to RabbitMQ
        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
        try:
            rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            rabbitmq_channel = await rabbitmq_connection.channel()
            
            # Declare notification queue
            await rabbitmq_channel.declare_queue("notifications", durable=True)
            
            # Start consuming messages
            queue = await rabbitmq_channel.get_queue("notifications")
            await queue.consume(process_notification_message)
            
            print("✅ Connected to RabbitMQ")
        except Exception as e:
            print(f"⚠️ RabbitMQ connection failed: {e}")
        
        print("✅ Notification Service started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup connections"""
    if db_pool:
        await db_pool.close()
    if rabbitmq_connection:
        await rabbitmq_connection.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "notification-service",
        "timestamp": datetime.utcnow().isoformat()
    }

async def process_notification_message(message: aio_pika.IncomingMessage):
    """Process notification messages from RabbitMQ"""
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            await send_notification_internal(
                data['type'],
                data['recipient'],
                data.get('subject'),
                data.get('template'),
                data['data'],
                data.get('priority', 'normal')
            )
        except Exception as e:
            print(f"Error processing notification message: {e}")

def render_template(template: str, variables: Dict[str, Any]) -> str:
    """Simple template rendering"""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result

async def send_email(recipient: str, subject: str, body: str) -> bool:
    """Send email notification (mock implementation)"""
    # In production, integrate with real email service (SendGrid, SES, etc.)
    print(f"📧 Sending email to {recipient}")
    print(f"   Subject: {subject}")
    print(f"   Body: {body[:100]}...")
    
    # Simulate email sending
    await asyncio.sleep(0.1)
    return True

async def send_sms(recipient: str, message: str) -> bool:
    """Send SMS notification (mock implementation)"""
    # In production, integrate with real SMS service (Twilio, etc.)
    print(f"📱 Sending SMS to {recipient}")
    print(f"   Message: {message}")
    
    # Simulate SMS sending
    await asyncio.sleep(0.1)
    return True

async def send_webhook(url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
    """Send webhook notification"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=data,
                headers=headers or {},
                timeout=10.0
            )
            return response.status_code in [200, 201, 202, 204]
    except Exception as e:
        print(f"Webhook failed: {e}")
        return False

async def send_notification_internal(
    notification_type: str,
    recipient: str,
    subject: Optional[str],
    template_name: Optional[str],
    data: Dict[str, Any],
    priority: str = "normal"
) -> str:
    """Internal function to send notifications"""
    notification_id = f"NTF{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    
    async with db_pool.acquire() as conn:
        # Get template if specified
        content = ""
        if template_name:
            template = await conn.fetchrow(
                "SELECT * FROM notification_templates WHERE name = $1 AND active = TRUE",
                template_name
            )
            if template:
                content = render_template(template['body'], data)
                if not subject and template['subject']:
                    subject = render_template(template['subject'], data)
        else:
            content = data.get('message', '')
        
        # Check user preferences
        preferences = await conn.fetchrow(
            "SELECT * FROM notification_preferences WHERE user_id = $1",
            data.get('user_id', recipient)
        )
        
        # Store notification
        await conn.execute("""
            INSERT INTO notifications 
            (notification_id, type, recipient, subject, content, status, priority, metadata)
            VALUES ($1, $2, $3, $4, $5, 'sending', $6, $7)
        """, notification_id, notification_type, recipient, subject, content, priority, json.dumps(data))
        
        # Send based on type
        success = False
        error_message = None
        
        try:
            if notification_type == 'email':
                if not preferences or preferences['email_enabled']:
                    success = await send_email(recipient, subject or "Notification", content)
            elif notification_type == 'sms':
                if not preferences or preferences['sms_enabled']:
                    success = await send_sms(recipient, content)
            elif notification_type == 'webhook':
                if not preferences or preferences['webhook_enabled']:
                    # Get webhook configs
                    webhooks = await conn.fetch(
                        "SELECT * FROM webhook_configs WHERE user_id = $1 AND active = TRUE",
                        data.get('user_id', '')
                    )
                    for webhook in webhooks:
                        if data.get('event_type') in webhook['events']:
                            success = await send_webhook(
                                webhook['url'],
                                data,
                                json.loads(webhook['headers'])
                            )
            elif notification_type == 'in_app':
                # Send via WebSocket
                await manager.send_personal_message(
                    json.dumps({
                        "notification_id": notification_id,
                        "type": "in_app",
                        "subject": subject,
                        "content": content,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }),
                    recipient
                )
                success = True
            else:
                error_message = f"Unknown notification type: {notification_type}"
        except Exception as e:
            error_message = str(e)
            success = False
        
        # Update notification status
        if success:
            await conn.execute("""
                UPDATE notifications 
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP 
                WHERE notification_id = $1
            """, notification_id)
        else:
            await conn.execute("""
                UPDATE notifications 
                SET status = 'failed', 
                    failed_at = CURRENT_TIMESTAMP,
                    error_message = $2 
                WHERE notification_id = $1
            """, notification_id, error_message)
    
    return notification_id

@app.post("/api/v1/notifications", response_model=NotificationResponse)
async def send_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Send a notification"""
    with tracer.start_as_current_span("send_notification", attributes=create_span_attributes(
        type=request.type,
        recipient=request.recipient,
        priority=request.priority
    )):
        if request.schedule_at and request.schedule_at > datetime.utcnow():
            # Schedule for later
            notification_id = f"NTF{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            
            async with db.acquire() as conn:
                await conn.execute("""
                    INSERT INTO notifications 
                    (notification_id, type, recipient, subject, content, status, priority, scheduled_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, 'scheduled', $6, $7, $8)
                """, notification_id, request.type, request.recipient, request.subject,
                    request.data.get('message', ''), request.priority, request.schedule_at,
                    json.dumps(request.data))
            
            return NotificationResponse(
                notification_id=notification_id,
                status="scheduled",
                created_at=datetime.utcnow(),
                scheduled_at=request.schedule_at
            )
        else:
            # Send immediately in background
            background_tasks.add_task(
                send_notification_internal,
                request.type,
                request.recipient,
                request.subject,
                request.template,
                request.data,
                request.priority
            )
            
            notification_id = f"NTF{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            
            return NotificationResponse(
                notification_id=notification_id,
                status="queued",
                created_at=datetime.utcnow(),
                scheduled_at=None
            )

@app.get("/api/v1/notifications/{notification_id}", response_model=NotificationStatus)
async def get_notification_status(
    notification_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get notification status"""
    with tracer.start_as_current_span("get_notification_status", attributes=create_span_attributes(
        notification_id=notification_id
    )):
        async with db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM notifications WHERE notification_id = $1",
                notification_id
            )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return NotificationStatus(
            notification_id=result['notification_id'],
            type=result['type'],
            recipient=result['recipient'],
            status=result['status'],
            created_at=result['created_at'],
            sent_at=result['sent_at'],
            failed_at=result['failed_at'],
            error_message=result['error_message'],
            retry_count=result['retry_count']
        )

@app.post("/api/v1/webhooks")
async def register_webhook(
    config: WebhookConfig,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Register a webhook for notifications"""
    with tracer.start_as_current_span("register_webhook", attributes=create_span_attributes(
        url=config.url,
        events=",".join(config.events)
    )):
        webhook_id = f"WHK{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO webhook_configs 
                (webhook_id, url, events, active, secret, headers)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, webhook_id, config.url, config.events, config.active,
                config.secret, json.dumps(config.headers or {}))
        
        return {
            "webhook_id": webhook_id,
            "status": "registered",
            "url": config.url,
            "events": config.events
        }

@app.delete("/api/v1/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Delete a webhook"""
    with tracer.start_as_current_span("delete_webhook", attributes=create_span_attributes(
        webhook_id=webhook_id
    )):
        async with db.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM webhook_configs WHERE webhook_id = $1",
                webhook_id
            )
            
            if result == "DELETE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Webhook not found"
                )
        
        return {"status": "deleted"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)

@app.get("/api/v1/notifications/stats")
async def get_notification_stats(
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get notification statistics"""
    with tracer.start_as_current_span("get_notification_stats"):
        async with db.acquire() as conn:
            # Overall stats
            overall = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_notifications,
                    COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as scheduled
                FROM notifications
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """)
            
            # By type
            by_type = await conn.fetch("""
                SELECT 
                    type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM notifications
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
                GROUP BY type
            """)
            
            # Webhooks
            webhooks = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_webhooks,
                    COUNT(CASE WHEN active = TRUE THEN 1 END) as active_webhooks,
                    COUNT(CASE WHEN failure_count > 3 THEN 1 END) as failing_webhooks
                FROM webhook_configs
            """)
        
        return {
            "last_24h": {
                "total": overall['total_notifications'],
                "sent": overall['sent'],
                "failed": overall['failed'],
                "pending": overall['pending'],
                "scheduled": overall['scheduled']
            },
            "by_type": {
                row['type']: {
                    "total": row['count'],
                    "sent": row['sent'],
                    "failed": row['failed']
                }
                for row in by_type
            },
            "webhooks": {
                "total": webhooks['total_webhooks'],
                "active": webhooks['active_webhooks'],
                "failing": webhooks['failing_webhooks']
            },
            "websocket_connections": len(manager.active_connections)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8743)