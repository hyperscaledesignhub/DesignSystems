"""
Fraud Detection Service - Real-time fraud detection and risk scoring
"""
import os
import sys
import asyncio
import asyncpg
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis.asyncio as redis
import httpx
import json
import hashlib
from sklearn.ensemble import IsolationForest
import pickle

# Import tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing
tracer = setup_tracing("fraud-detection-service")

# Create FastAPI app
app = FastAPI(title="Fraud Detection Service", version="1.0.0")
instrument_fastapi(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database and Redis connections
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None

# Fraud detection model (simple for demo)
fraud_model = None

# Service URLs
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8734")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8743")

# Pydantic models
class FraudCheckRequest(BaseModel):
    payment_id: str
    user_id: str
    amount: Decimal
    currency: str = "USD"
    merchant_id: Optional[str] = None
    card_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    email: Optional[str] = None
    billing_country: Optional[str] = None
    shipping_country: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FraudCheckResponse(BaseModel):
    check_id: str
    payment_id: str
    risk_score: float  # 0-100, higher = more risky
    risk_level: str    # low, medium, high, critical
    decision: str      # approve, review, decline
    reasons: List[str]
    checked_at: datetime
    processing_time_ms: int

class FraudRule(BaseModel):
    rule_id: str
    rule_name: str
    rule_type: str  # velocity, amount, pattern, blacklist, whitelist
    priority: int
    threshold: Optional[float]
    action: str     # flag, review, block
    active: bool
    config: Dict[str, Any]

class FraudAlert(BaseModel):
    alert_id: str
    payment_id: str
    user_id: str
    alert_type: str
    severity: str
    details: Dict[str, Any]
    created_at: datetime
    status: str

async def get_db_pool():
    """Get database connection pool"""
    return db_pool

async def get_redis():
    """Get Redis client"""
    return redis_client

@app.on_event("startup")
async def startup():
    """Initialize database and Redis connections"""
    global db_pool, redis_client, fraud_model
    
    with tracer.start_as_current_span("service_startup"):
        # Connect to PostgreSQL
        db_url = os.getenv("DATABASE_URL", "postgresql://fraud_user:fraud_pass@postgres-fraud:5432/fraud_db")
        db_pool = await asyncpg.create_pool(db_url, min_size=5, max_size=20)
        
        # Initialize database schema
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fraud_checks (
                    check_id VARCHAR(50) PRIMARY KEY,
                    payment_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    amount DECIMAL(20, 2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'USD',
                    risk_score FLOAT NOT NULL,
                    risk_level VARCHAR(20) NOT NULL,
                    decision VARCHAR(20) NOT NULL,
                    reasons TEXT[],
                    ip_address VARCHAR(45),
                    device_id VARCHAR(100),
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_fraud_checks_payment ON fraud_checks(payment_id);
                CREATE INDEX IF NOT EXISTS idx_fraud_checks_user ON fraud_checks(user_id);
                CREATE INDEX IF NOT EXISTS idx_fraud_checks_risk ON fraud_checks(risk_level);
                CREATE INDEX IF NOT EXISTS idx_fraud_checks_time ON fraud_checks(checked_at);
                
                CREATE TABLE IF NOT EXISTS fraud_rules (
                    rule_id VARCHAR(50) PRIMARY KEY,
                    rule_name VARCHAR(100) NOT NULL,
                    rule_type VARCHAR(30) NOT NULL,
                    priority INTEGER DEFAULT 0,
                    threshold FLOAT,
                    action VARCHAR(20) NOT NULL,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    config JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE TABLE IF NOT EXISTS fraud_alerts (
                    alert_id VARCHAR(50) PRIMARY KEY,
                    payment_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    details JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'open',
                    resolution_notes TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_fraud_alerts_payment ON fraud_alerts(payment_id);
                CREATE INDEX IF NOT EXISTS idx_fraud_alerts_user ON fraud_alerts(user_id);
                CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts(status);
                
                CREATE TABLE IF NOT EXISTS blacklists (
                    list_id VARCHAR(50) PRIMARY KEY,
                    list_type VARCHAR(30) NOT NULL,
                    value VARCHAR(255) NOT NULL,
                    reason TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    added_by VARCHAR(50),
                    expires_at TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE
                );
                
                CREATE UNIQUE INDEX IF NOT EXISTS idx_blacklists_value ON blacklists(list_type, value) WHERE active = TRUE;
                
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id VARCHAR(50) PRIMARY KEY,
                    total_transactions INTEGER DEFAULT 0,
                    total_amount DECIMAL(20, 2) DEFAULT 0.00,
                    avg_transaction_amount DECIMAL(20, 2) DEFAULT 0.00,
                    last_transaction_date TIMESTAMP,
                    fraud_score_history FLOAT[] DEFAULT ARRAY[]::FLOAT[],
                    trusted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Insert default fraud rules
            await conn.execute("""
                INSERT INTO fraud_rules (rule_id, rule_name, rule_type, priority, threshold, action, config)
                VALUES 
                    ('RULE001', 'High Amount Transaction', 'amount', 1, 10000, 'review', 
                     '{"description": "Flag transactions over $10,000 for review"}'::jsonb),
                    ('RULE002', 'Velocity Check - Frequency', 'velocity', 2, 5, 'review',
                     '{"window_minutes": 10, "description": "More than 5 transactions in 10 minutes"}'::jsonb),
                    ('RULE003', 'Velocity Check - Amount', 'velocity', 3, 5000, 'review',
                     '{"window_minutes": 60, "description": "Total amount over $5,000 in 1 hour"}'::jsonb),
                    ('RULE004', 'New User High Value', 'pattern', 4, 1000, 'review',
                     '{"user_age_days": 1, "description": "New users with transactions over $1,000"}'::jsonb),
                    ('RULE005', 'Country Mismatch', 'pattern', 5, NULL, 'flag',
                     '{"description": "Billing and shipping countries dont match"}'::jsonb),
                    ('RULE006', 'Blacklist Check', 'blacklist', 0, NULL, 'block',
                     '{"description": "Check against blacklisted entities"}'::jsonb),
                    ('RULE007', 'Trusted User', 'whitelist', 0, NULL, 'approve',
                     '{"min_transactions": 50, "description": "Auto-approve trusted users"}'::jsonb)
                ON CONFLICT (rule_id) DO NOTHING
            """)
        
        # Connect to Redis
        redis_url = os.getenv("REDIS_URL", "redis://redis-fraud:6379")
        redis_client = await redis.from_url(redis_url, decode_responses=True)
        
        # Initialize simple fraud detection model
        fraud_model = IsolationForest(contamination=0.1, random_state=42)
        # Train with some dummy data for demo
        dummy_data = np.random.randn(100, 5)
        fraud_model.fit(dummy_data)
        
        print("✅ Fraud Detection Service started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup connections"""
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "fraud-detection-service",
        "timestamp": datetime.utcnow().isoformat()
    }

async def check_blacklist(user_id: str, ip_address: str, email: str, card_fingerprint: str) -> bool:
    """Check if any entity is blacklisted"""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT COUNT(*) as count FROM blacklists
            WHERE active = TRUE 
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            AND (
                (list_type = 'user_id' AND value = $1) OR
                (list_type = 'ip_address' AND value = $2) OR
                (list_type = 'email' AND value = $3) OR
                (list_type = 'card' AND value = $4)
            )
        """, user_id, ip_address or '', email or '', card_fingerprint or '')
        
        return result['count'] > 0

async def check_velocity(user_id: str, amount: Decimal) -> Dict[str, Any]:
    """Check transaction velocity for user"""
    # Check transaction frequency
    freq_key = f"velocity:freq:{user_id}"
    amount_key = f"velocity:amount:{user_id}"
    
    # Get recent transaction count (last 10 minutes)
    recent_count = await redis_client.get(freq_key) or 0
    recent_count = int(recent_count)
    
    # Get recent transaction amount (last hour)
    recent_amount = await redis_client.get(amount_key) or "0"
    recent_amount = Decimal(recent_amount)
    
    # Update counters
    await redis_client.incr(freq_key)
    await redis_client.expire(freq_key, 600)  # 10 minutes
    
    new_amount = recent_amount + amount
    await redis_client.setex(amount_key, 3600, str(new_amount))  # 1 hour
    
    return {
        "transaction_count_10min": recent_count + 1,
        "transaction_amount_1hr": float(new_amount),
        "velocity_score": min(100, (recent_count * 10) + (float(new_amount) / 100))
    }

async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get or create user profile for risk assessment"""
    async with db_pool.acquire() as conn:
        profile = await conn.fetchrow(
            "SELECT * FROM user_profiles WHERE user_id = $1",
            user_id
        )
        
        if not profile:
            # Create new profile
            await conn.execute("""
                INSERT INTO user_profiles (user_id, created_at)
                VALUES ($1, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO NOTHING
            """, user_id)
            
            return {
                "user_id": user_id,
                "total_transactions": 0,
                "total_amount": 0,
                "avg_transaction_amount": 0,
                "is_new": True,
                "trusted": False
            }
        
        return {
            "user_id": profile['user_id'],
            "total_transactions": profile['total_transactions'],
            "total_amount": float(profile['total_amount']),
            "avg_transaction_amount": float(profile['avg_transaction_amount']),
            "is_new": profile['total_transactions'] < 5,
            "trusted": profile['trusted']
        }

def calculate_risk_score(
    amount: float,
    velocity_data: Dict[str, Any],
    user_profile: Dict[str, Any],
    is_blacklisted: bool,
    country_mismatch: bool
) -> tuple[float, List[str]]:
    """Calculate risk score and identify risk factors"""
    risk_score = 0.0
    reasons = []
    
    # Blacklist check (immediate high risk)
    if is_blacklisted:
        risk_score += 90
        reasons.append("Entity found in blacklist")
    
    # Amount-based risk
    if amount > 10000:
        risk_score += 30
        reasons.append("High transaction amount")
    elif amount > 5000:
        risk_score += 20
        reasons.append("Elevated transaction amount")
    elif amount > 1000:
        risk_score += 10
    
    # Velocity-based risk
    if velocity_data['transaction_count_10min'] > 5:
        risk_score += 25
        reasons.append("High transaction frequency")
    elif velocity_data['transaction_count_10min'] > 3:
        risk_score += 15
        reasons.append("Elevated transaction frequency")
    
    if velocity_data['transaction_amount_1hr'] > 5000:
        risk_score += 20
        reasons.append("High cumulative amount in short time")
    
    # User profile-based risk
    if user_profile['is_new']:
        if amount > 1000:
            risk_score += 25
            reasons.append("New user with high-value transaction")
        else:
            risk_score += 10
            reasons.append("New user")
    
    if user_profile['trusted']:
        risk_score = max(0, risk_score - 30)
        if risk_score < 30:
            reasons = ["Trusted user"]
    
    # Pattern-based risk
    if country_mismatch:
        risk_score += 15
        reasons.append("Billing and shipping country mismatch")
    
    # Anomaly detection (simplified)
    if user_profile['avg_transaction_amount'] > 0:
        deviation = abs(amount - user_profile['avg_transaction_amount']) / user_profile['avg_transaction_amount']
        if deviation > 5:
            risk_score += 20
            reasons.append("Significant deviation from typical amount")
        elif deviation > 3:
            risk_score += 10
            reasons.append("Unusual transaction amount for user")
    
    # Cap at 100
    risk_score = min(100, risk_score)
    
    if not reasons:
        reasons = ["No risk factors detected"]
    
    return risk_score, reasons

@app.post("/api/v1/fraud/check", response_model=FraudCheckResponse)
async def check_fraud(
    request: FraudCheckRequest,
    background_tasks: BackgroundTasks,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Perform real-time fraud check on a payment"""
    start_time = datetime.utcnow()
    
    with tracer.start_as_current_span("check_fraud", attributes=create_span_attributes(
        payment_id=request.payment_id,
        user_id=request.user_id,
        amount=str(request.amount)
    )):
        check_id = f"CHK{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        # Parallel checks
        is_blacklisted = await check_blacklist(
            request.user_id,
            request.ip_address,
            request.email,
            request.card_fingerprint
        )
        
        velocity_data = await check_velocity(request.user_id, request.amount)
        user_profile = await get_user_profile(request.user_id)
        
        # Check for country mismatch
        country_mismatch = False
        if request.billing_country and request.shipping_country:
            country_mismatch = request.billing_country != request.shipping_country
        
        # Calculate risk score
        risk_score, reasons = calculate_risk_score(
            float(request.amount),
            velocity_data,
            user_profile,
            is_blacklisted,
            country_mismatch
        )
        
        # Determine risk level and decision
        if risk_score >= 80:
            risk_level = "critical"
            decision = "decline"
        elif risk_score >= 60:
            risk_level = "high"
            decision = "review"
        elif risk_score >= 30:
            risk_level = "medium"
            decision = "review"
        else:
            risk_level = "low"
            decision = "approve"
        
        # Override for blacklisted entities
        if is_blacklisted:
            decision = "decline"
            risk_level = "critical"
        
        # Override for trusted users
        if user_profile['trusted'] and risk_score < 30:
            decision = "approve"
            risk_level = "low"
        
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Store fraud check result
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO fraud_checks 
                (check_id, payment_id, user_id, amount, currency, risk_score, risk_level, 
                 decision, reasons, ip_address, device_id, processing_time_ms, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, check_id, request.payment_id, request.user_id, request.amount, request.currency,
                risk_score, risk_level, decision, reasons, request.ip_address, request.device_id,
                processing_time_ms, json.dumps(request.metadata or {}))
            
            # Update user profile
            await conn.execute("""
                UPDATE user_profiles 
                SET total_transactions = total_transactions + 1,
                    total_amount = total_amount + $1,
                    avg_transaction_amount = (total_amount + $1) / (total_transactions + 1),
                    last_transaction_date = CURRENT_TIMESTAMP,
                    fraud_score_history = array_append(fraud_score_history, $2),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $3
            """, request.amount, risk_score, request.user_id)
        
        # Create alert for high-risk transactions
        if risk_level in ["high", "critical"]:
            background_tasks.add_task(
                create_fraud_alert,
                request.payment_id,
                request.user_id,
                risk_level,
                reasons
            )
        
        # Cache the result
        await redis_client.setex(
            f"fraud_check:{request.payment_id}",
            3600,
            json.dumps({
                "check_id": check_id,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "decision": decision
            })
        )
        
        return FraudCheckResponse(
            check_id=check_id,
            payment_id=request.payment_id,
            risk_score=risk_score,
            risk_level=risk_level,
            decision=decision,
            reasons=reasons,
            checked_at=datetime.utcnow(),
            processing_time_ms=processing_time_ms
        )

async def create_fraud_alert(payment_id: str, user_id: str, severity: str, reasons: List[str]):
    """Create a fraud alert for investigation"""
    alert_id = f"ALERT{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO fraud_alerts 
            (alert_id, payment_id, user_id, alert_type, severity, details, status)
            VALUES ($1, $2, $3, 'automatic_detection', $4, $5, 'open')
        """, alert_id, payment_id, user_id, severity, json.dumps({"reasons": reasons}))
    
    # Send notification
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/v1/notifications",
                json={
                    "type": "fraud_alert",
                    "recipient": "fraud-team@payment-system.com",
                    "subject": f"Fraud Alert: {severity.upper()} risk transaction",
                    "data": {
                        "alert_id": alert_id,
                        "payment_id": payment_id,
                        "user_id": user_id,
                        "severity": severity,
                        "reasons": reasons
                    }
                },
                headers=get_trace_headers()
            )
    except Exception as e:
        print(f"Failed to send fraud alert notification: {e}")

@app.get("/api/v1/fraud/checks/{payment_id}")
async def get_fraud_check(
    payment_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get fraud check result for a payment"""
    with tracer.start_as_current_span("get_fraud_check", attributes=create_span_attributes(
        payment_id=payment_id
    )):
        # Try cache first
        cached = await redis_client.get(f"fraud_check:{payment_id}")
        if cached:
            return json.loads(cached)
        
        # Query database
        async with db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM fraud_checks WHERE payment_id = $1 ORDER BY checked_at DESC LIMIT 1",
                payment_id
            )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fraud check not found"
            )
        
        return {
            "check_id": result['check_id'],
            "payment_id": result['payment_id'],
            "risk_score": result['risk_score'],
            "risk_level": result['risk_level'],
            "decision": result['decision'],
            "reasons": result['reasons'],
            "checked_at": result['checked_at'].isoformat()
        }

@app.post("/api/v1/fraud/blacklist")
async def add_to_blacklist(
    list_type: str,
    value: str,
    reason: str,
    expires_in_days: Optional[int] = None,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Add an entity to the blacklist"""
    with tracer.start_as_current_span("add_to_blacklist", attributes=create_span_attributes(
        list_type=list_type,
        value=value
    )):
        list_id = f"BL{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        expires_at = None
        
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        async with db.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO blacklists (list_id, list_type, value, reason, expires_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, list_id, list_type, value, reason, expires_at)
                
                return {
                    "list_id": list_id,
                    "status": "added",
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
            except asyncpg.UniqueViolationError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Entity already blacklisted"
                )

@app.delete("/api/v1/fraud/blacklist")
async def remove_from_blacklist(
    list_type: str,
    value: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Remove an entity from the blacklist"""
    with tracer.start_as_current_span("remove_from_blacklist", attributes=create_span_attributes(
        list_type=list_type,
        value=value
    )):
        async with db.acquire() as conn:
            result = await conn.execute("""
                UPDATE blacklists 
                SET active = FALSE 
                WHERE list_type = $1 AND value = $2 AND active = TRUE
            """, list_type, value)
            
            if result == "UPDATE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Entity not found in blacklist"
                )
            
            return {"status": "removed"}

@app.get("/api/v1/fraud/alerts", response_model=List[FraudAlert])
async def get_fraud_alerts(
    status: Optional[str] = None,
    limit: int = 50,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get fraud alerts"""
    with tracer.start_as_current_span("get_fraud_alerts"):
        query = "SELECT * FROM fraud_alerts"
        params = []
        
        if status:
            query += " WHERE status = $1"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        async with db.acquire() as conn:
            results = await conn.fetch(query, *params)
        
        return [
            FraudAlert(
                alert_id=row['alert_id'],
                payment_id=row['payment_id'],
                user_id=row['user_id'],
                alert_type=row['alert_type'],
                severity=row['severity'],
                details=json.loads(row['details']),
                created_at=row['created_at'],
                status=row['status']
            )
            for row in results
        ]

@app.post("/api/v1/fraud/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution_notes: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Resolve a fraud alert"""
    with tracer.start_as_current_span("resolve_alert", attributes=create_span_attributes(
        alert_id=alert_id
    )):
        async with db.acquire() as conn:
            result = await conn.execute("""
                UPDATE fraud_alerts 
                SET status = 'resolved',
                    resolved_at = CURRENT_TIMESTAMP,
                    resolution_notes = $1
                WHERE alert_id = $2 AND status = 'open'
            """, resolution_notes, alert_id)
            
            if result == "UPDATE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Alert not found or already resolved"
                )
        
        return {"status": "resolved", "alert_id": alert_id}

@app.get("/api/v1/fraud/stats")
async def get_fraud_stats(
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get fraud detection statistics"""
    with tracer.start_as_current_span("get_fraud_stats"):
        async with db.acquire() as conn:
            # Overall stats
            overall = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_checks,
                    AVG(risk_score) as avg_risk_score,
                    COUNT(CASE WHEN decision = 'approve' THEN 1 END) as approved,
                    COUNT(CASE WHEN decision = 'review' THEN 1 END) as reviewed,
                    COUNT(CASE WHEN decision = 'decline' THEN 1 END) as declined,
                    AVG(processing_time_ms) as avg_processing_time
                FROM fraud_checks
                WHERE checked_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """)
            
            # Risk distribution
            risk_dist = await conn.fetch("""
                SELECT 
                    risk_level,
                    COUNT(*) as count,
                    AVG(risk_score) as avg_score
                FROM fraud_checks
                WHERE checked_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
                GROUP BY risk_level
            """)
            
            # Alert stats
            alerts = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_alerts,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_alerts,
                    COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_alerts
                FROM fraud_alerts
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """)
            
            # Blacklist stats
            blacklist = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT value) as blacklisted_entities,
                    COUNT(CASE WHEN list_type = 'user_id' THEN 1 END) as blacklisted_users,
                    COUNT(CASE WHEN list_type = 'ip_address' THEN 1 END) as blacklisted_ips,
                    COUNT(CASE WHEN list_type = 'card' THEN 1 END) as blacklisted_cards
                FROM blacklists
                WHERE active = TRUE
            """)
        
        return {
            "checks_24h": {
                "total": overall['total_checks'],
                "approved": overall['approved'],
                "reviewed": overall['reviewed'],
                "declined": overall['declined'],
                "avg_risk_score": float(overall['avg_risk_score'] or 0),
                "avg_processing_time_ms": float(overall['avg_processing_time'] or 0)
            },
            "risk_distribution": {
                row['risk_level']: {
                    "count": row['count'],
                    "avg_score": float(row['avg_score'])
                }
                for row in risk_dist
            },
            "alerts_24h": {
                "total": alerts['total_alerts'],
                "open": alerts['open_alerts'],
                "resolved": alerts['resolved_alerts'],
                "critical": alerts['critical_alerts']
            },
            "blacklist": {
                "total_entities": blacklist['blacklisted_entities'],
                "users": blacklist['blacklisted_users'],
                "ip_addresses": blacklist['blacklisted_ips'],
                "cards": blacklist['blacklisted_cards']
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8742)