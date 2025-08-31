"""
Reconciliation Service - Handles payment reconciliation and settlement
"""
import os
import sys
import asyncio
import asyncpg
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import json

# Import tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing
tracer = setup_tracing("reconciliation-service")

# Create FastAPI app
app = FastAPI(title="Reconciliation Service", version="1.0.0")
instrument_fastapi(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

# Service URLs
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8734")
LEDGER_SERVICE_URL = os.getenv("LEDGER_SERVICE_URL", "http://ledger-service:8736")
PSP_GATEWAY_URL = os.getenv("PSP_GATEWAY_URL", "http://psp-gateway:8738")
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet-service:8740")

# Pydantic models
class ReconciliationRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    reconciliation_type: str = "daily"  # daily, weekly, monthly
    psp_id: Optional[str] = None

class ReconciliationResult(BaseModel):
    reconciliation_id: str
    start_date: datetime
    end_date: datetime
    status: str
    total_transactions: int
    matched_transactions: int
    unmatched_transactions: int
    total_amount: Decimal
    discrepancy_amount: Decimal
    created_at: datetime
    completed_at: Optional[datetime]
    report_url: Optional[str]

class DiscrepancyRecord(BaseModel):
    discrepancy_id: str
    reconciliation_id: str
    transaction_id: str
    psp_reference: Optional[str]
    internal_amount: Decimal
    psp_amount: Optional[Decimal]
    discrepancy_type: str  # missing_in_psp, missing_internal, amount_mismatch, status_mismatch
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]

class SettlementBatch(BaseModel):
    batch_id: str
    psp_id: str
    settlement_date: datetime
    total_amount: Decimal
    transaction_count: int
    status: str
    created_at: datetime
    processed_at: Optional[datetime]

async def get_db_pool():
    """Get database connection pool"""
    return db_pool

@app.on_event("startup")
async def startup():
    """Initialize database connection"""
    global db_pool
    
    with tracer.start_as_current_span("service_startup"):
        # Connect to PostgreSQL
        db_url = os.getenv("DATABASE_URL", "postgresql://reconciliation_user:reconciliation_pass@postgres-reconciliation:5432/reconciliation_db")
        db_pool = await asyncpg.create_pool(db_url, min_size=5, max_size=20)
        
        # Initialize database schema
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reconciliations (
                    reconciliation_id VARCHAR(50) PRIMARY KEY,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    reconciliation_type VARCHAR(20) NOT NULL,
                    psp_id VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'pending',
                    total_transactions INTEGER DEFAULT 0,
                    matched_transactions INTEGER DEFAULT 0,
                    unmatched_transactions INTEGER DEFAULT 0,
                    total_amount DECIMAL(20, 2) DEFAULT 0.00,
                    discrepancy_amount DECIMAL(20, 2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    report_url TEXT,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_reconciliations_date ON reconciliations(start_date, end_date);
                CREATE INDEX IF NOT EXISTS idx_reconciliations_status ON reconciliations(status);
                
                CREATE TABLE IF NOT EXISTS discrepancies (
                    discrepancy_id VARCHAR(50) PRIMARY KEY,
                    reconciliation_id VARCHAR(50) REFERENCES reconciliations(reconciliation_id),
                    transaction_id VARCHAR(100) NOT NULL,
                    psp_reference VARCHAR(100),
                    internal_amount DECIMAL(20, 2) NOT NULL,
                    psp_amount DECIMAL(20, 2),
                    discrepancy_type VARCHAR(30) NOT NULL,
                    status VARCHAR(20) DEFAULT 'unresolved',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolution_notes TEXT,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_discrepancies_reconciliation ON discrepancies(reconciliation_id);
                CREATE INDEX IF NOT EXISTS idx_discrepancies_status ON discrepancies(status);
                
                CREATE TABLE IF NOT EXISTS settlement_batches (
                    batch_id VARCHAR(50) PRIMARY KEY,
                    psp_id VARCHAR(50) NOT NULL,
                    settlement_date TIMESTAMP NOT NULL,
                    total_amount DECIMAL(20, 2) NOT NULL,
                    transaction_count INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    transaction_ids TEXT[],
                    metadata JSONB DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_settlements_date ON settlement_batches(settlement_date);
                CREATE INDEX IF NOT EXISTS idx_settlements_status ON settlement_batches(status);
                
                CREATE TABLE IF NOT EXISTS reconciliation_rules (
                    rule_id VARCHAR(50) PRIMARY KEY,
                    rule_name VARCHAR(100) NOT NULL,
                    rule_type VARCHAR(30) NOT NULL,
                    threshold_amount DECIMAL(20, 2),
                    auto_resolve BOOLEAN DEFAULT FALSE,
                    priority INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    config JSONB DEFAULT '{}'::jsonb
                );
            """)
            
            # Insert default reconciliation rules
            await conn.execute("""
                INSERT INTO reconciliation_rules (rule_id, rule_name, rule_type, threshold_amount, auto_resolve, priority)
                VALUES 
                    ('RULE001', 'Small Amount Auto-Resolve', 'amount_threshold', 1.00, true, 1),
                    ('RULE002', 'Duplicate Detection', 'duplicate_check', NULL, false, 2),
                    ('RULE003', 'Status Mismatch Alert', 'status_check', NULL, false, 3)
                ON CONFLICT (rule_id) DO NOTHING
            """)
        
        print("✅ Reconciliation Service started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup connections"""
    if db_pool:
        await db_pool.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "reconciliation-service",
        "timestamp": datetime.utcnow().isoformat()
    }

async def fetch_internal_transactions(start_date: datetime, end_date: datetime, psp_id: Optional[str] = None):
    """Fetch transactions from internal payment service"""
    with tracer.start_as_current_span("fetch_internal_transactions"):
        async with httpx.AsyncClient() as client:
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            if psp_id:
                params["psp_id"] = psp_id
            
            response = await client.get(
                f"{PAYMENT_SERVICE_URL}/api/v1/payments/reconciliation",
                params=params,
                headers=get_trace_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            return []

async def fetch_psp_transactions(start_date: datetime, end_date: datetime, psp_id: str):
    """Fetch transactions from PSP gateway"""
    with tracer.start_as_current_span("fetch_psp_transactions"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PSP_GATEWAY_URL}/api/v1/transactions",
                params={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "psp_id": psp_id
                },
                headers=get_trace_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            return []

async def fetch_ledger_entries(start_date: datetime, end_date: datetime):
    """Fetch ledger entries for reconciliation"""
    with tracer.start_as_current_span("fetch_ledger_entries"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LEDGER_SERVICE_URL}/api/v1/entries/reconciliation",
                params={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                headers=get_trace_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            return []

@app.post("/api/v1/reconciliations", response_model=ReconciliationResult)
async def create_reconciliation(
    request: ReconciliationRequest,
    background_tasks: BackgroundTasks,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Create and start a new reconciliation process"""
    with tracer.start_as_current_span("create_reconciliation", attributes=create_span_attributes(
        reconciliation_type=request.reconciliation_type,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat()
    )):
        reconciliation_id = f"REC{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create reconciliation record
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO reconciliations 
                (reconciliation_id, start_date, end_date, reconciliation_type, psp_id, status)
                VALUES ($1, $2, $3, $4, $5, 'processing')
            """, reconciliation_id, request.start_date, request.end_date, 
                request.reconciliation_type, request.psp_id)
        
        # Start reconciliation in background
        background_tasks.add_task(
            perform_reconciliation,
            reconciliation_id,
            request.start_date,
            request.end_date,
            request.psp_id
        )
        
        return ReconciliationResult(
            reconciliation_id=reconciliation_id,
            start_date=request.start_date,
            end_date=request.end_date,
            status="processing",
            total_transactions=0,
            matched_transactions=0,
            unmatched_transactions=0,
            total_amount=Decimal("0.00"),
            discrepancy_amount=Decimal("0.00"),
            created_at=datetime.utcnow(),
            completed_at=None,
            report_url=None
        )

async def perform_reconciliation(
    reconciliation_id: str,
    start_date: datetime,
    end_date: datetime,
    psp_id: Optional[str]
):
    """Perform the actual reconciliation process"""
    with tracer.start_as_current_span("perform_reconciliation", attributes=create_span_attributes(
        reconciliation_id=reconciliation_id
    )):
        try:
            # Fetch data from all sources
            internal_txns = await fetch_internal_transactions(start_date, end_date, psp_id)
            psp_txns = await fetch_psp_transactions(start_date, end_date, psp_id or "stripe")
            ledger_entries = await fetch_ledger_entries(start_date, end_date)
            
            # Create lookup maps
            internal_map = {txn.get('payment_id'): txn for txn in internal_txns}
            psp_map = {txn.get('reference_id'): txn for txn in psp_txns}
            ledger_map = {entry.get('reference_id'): entry for entry in ledger_entries}
            
            matched = 0
            unmatched = 0
            total_amount = Decimal("0.00")
            discrepancy_amount = Decimal("0.00")
            discrepancies = []
            
            # Reconcile internal transactions with PSP
            for payment_id, internal_txn in internal_map.items():
                total_amount += Decimal(str(internal_txn.get('amount', 0)))
                psp_txn = psp_map.get(payment_id)
                
                if not psp_txn:
                    # Missing in PSP
                    unmatched += 1
                    discrepancy_amount += Decimal(str(internal_txn.get('amount', 0)))
                    discrepancies.append({
                        'transaction_id': payment_id,
                        'internal_amount': internal_txn.get('amount'),
                        'discrepancy_type': 'missing_in_psp'
                    })
                elif Decimal(str(psp_txn.get('amount', 0))) != Decimal(str(internal_txn.get('amount', 0))):
                    # Amount mismatch
                    unmatched += 1
                    discrepancy_amount += abs(
                        Decimal(str(psp_txn.get('amount', 0))) - 
                        Decimal(str(internal_txn.get('amount', 0)))
                    )
                    discrepancies.append({
                        'transaction_id': payment_id,
                        'internal_amount': internal_txn.get('amount'),
                        'psp_amount': psp_txn.get('amount'),
                        'discrepancy_type': 'amount_mismatch'
                    })
                elif internal_txn.get('status') != psp_txn.get('status'):
                    # Status mismatch
                    unmatched += 1
                    discrepancies.append({
                        'transaction_id': payment_id,
                        'internal_amount': internal_txn.get('amount'),
                        'psp_amount': psp_txn.get('amount'),
                        'discrepancy_type': 'status_mismatch'
                    })
                else:
                    matched += 1
            
            # Check for PSP transactions missing in internal
            for reference_id, psp_txn in psp_map.items():
                if reference_id not in internal_map:
                    unmatched += 1
                    discrepancy_amount += Decimal(str(psp_txn.get('amount', 0)))
                    discrepancies.append({
                        'transaction_id': reference_id,
                        'psp_reference': psp_txn.get('transaction_id'),
                        'psp_amount': psp_txn.get('amount'),
                        'discrepancy_type': 'missing_internal'
                    })
            
            # Save discrepancies and update reconciliation
            async with db_pool.acquire() as conn:
                # Save discrepancies
                for disc in discrepancies:
                    discrepancy_id = f"DISC{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                    await conn.execute("""
                        INSERT INTO discrepancies 
                        (discrepancy_id, reconciliation_id, transaction_id, psp_reference, 
                         internal_amount, psp_amount, discrepancy_type, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, 'unresolved')
                    """, discrepancy_id, reconciliation_id, disc['transaction_id'],
                        disc.get('psp_reference'), 
                        Decimal(str(disc.get('internal_amount', 0))),
                        Decimal(str(disc.get('psp_amount', 0))) if disc.get('psp_amount') else None,
                        disc['discrepancy_type'])
                
                # Update reconciliation status
                await conn.execute("""
                    UPDATE reconciliations 
                    SET status = 'completed',
                        total_transactions = $1,
                        matched_transactions = $2,
                        unmatched_transactions = $3,
                        total_amount = $4,
                        discrepancy_amount = $5,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE reconciliation_id = $6
                """, len(internal_map) + len([t for t in psp_map if t not in internal_map]),
                    matched, unmatched, total_amount, discrepancy_amount, reconciliation_id)
            
            print(f"✅ Reconciliation {reconciliation_id} completed: {matched} matched, {unmatched} unmatched")
            
        except Exception as e:
            print(f"❌ Reconciliation {reconciliation_id} failed: {str(e)}")
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE reconciliations SET status = 'failed' WHERE reconciliation_id = $1",
                    reconciliation_id
                )

@app.get("/api/v1/reconciliations/{reconciliation_id}", response_model=ReconciliationResult)
async def get_reconciliation(
    reconciliation_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get reconciliation details"""
    with tracer.start_as_current_span("get_reconciliation", attributes=create_span_attributes(
        reconciliation_id=reconciliation_id
    )):
        async with db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM reconciliations WHERE reconciliation_id = $1",
                reconciliation_id
            )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reconciliation not found"
            )
        
        return ReconciliationResult(
            reconciliation_id=result['reconciliation_id'],
            start_date=result['start_date'],
            end_date=result['end_date'],
            status=result['status'],
            total_transactions=result['total_transactions'],
            matched_transactions=result['matched_transactions'],
            unmatched_transactions=result['unmatched_transactions'],
            total_amount=result['total_amount'],
            discrepancy_amount=result['discrepancy_amount'],
            created_at=result['created_at'],
            completed_at=result['completed_at'],
            report_url=result['report_url']
        )

@app.get("/api/v1/reconciliations/{reconciliation_id}/discrepancies", response_model=List[DiscrepancyRecord])
async def get_discrepancies(
    reconciliation_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get all discrepancies for a reconciliation"""
    with tracer.start_as_current_span("get_discrepancies", attributes=create_span_attributes(
        reconciliation_id=reconciliation_id
    )):
        async with db.acquire() as conn:
            results = await conn.fetch(
                "SELECT * FROM discrepancies WHERE reconciliation_id = $1 ORDER BY created_at DESC",
                reconciliation_id
            )
        
        return [
            DiscrepancyRecord(
                discrepancy_id=row['discrepancy_id'],
                reconciliation_id=row['reconciliation_id'],
                transaction_id=row['transaction_id'],
                psp_reference=row['psp_reference'],
                internal_amount=row['internal_amount'],
                psp_amount=row['psp_amount'],
                discrepancy_type=row['discrepancy_type'],
                status=row['status'],
                created_at=row['created_at'],
                resolved_at=row['resolved_at'],
                resolution_notes=row['resolution_notes']
            )
            for row in results
        ]

@app.post("/api/v1/discrepancies/{discrepancy_id}/resolve")
async def resolve_discrepancy(
    discrepancy_id: str,
    resolution_notes: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Mark a discrepancy as resolved"""
    with tracer.start_as_current_span("resolve_discrepancy", attributes=create_span_attributes(
        discrepancy_id=discrepancy_id
    )):
        async with db.acquire() as conn:
            result = await conn.execute("""
                UPDATE discrepancies 
                SET status = 'resolved',
                    resolved_at = CURRENT_TIMESTAMP,
                    resolution_notes = $1
                WHERE discrepancy_id = $2 AND status = 'unresolved'
            """, resolution_notes, discrepancy_id)
            
            if result == "UPDATE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Discrepancy not found or already resolved"
                )
        
        return {"status": "resolved", "discrepancy_id": discrepancy_id}

@app.post("/api/v1/settlements/create-batch", response_model=SettlementBatch)
async def create_settlement_batch(
    psp_id: str,
    settlement_date: datetime,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a settlement batch for a PSP"""
    with tracer.start_as_current_span("create_settlement_batch", attributes=create_span_attributes(
        psp_id=psp_id,
        settlement_date=settlement_date.isoformat()
    )):
        batch_id = f"BATCH{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Fetch eligible transactions
        start_date = settlement_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        transactions = await fetch_internal_transactions(start_date, end_date, psp_id)
        eligible_txns = [t for t in transactions if t.get('status') == 'completed']
        
        total_amount = sum(Decimal(str(t.get('amount', 0))) for t in eligible_txns)
        transaction_ids = [t.get('payment_id') for t in eligible_txns]
        
        # Create batch record
        async with db.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO settlement_batches 
                (batch_id, psp_id, settlement_date, total_amount, transaction_count, transaction_ids, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
                RETURNING *
            """, batch_id, psp_id, settlement_date, total_amount, len(eligible_txns), transaction_ids)
        
        return SettlementBatch(
            batch_id=result['batch_id'],
            psp_id=result['psp_id'],
            settlement_date=result['settlement_date'],
            total_amount=result['total_amount'],
            transaction_count=result['transaction_count'],
            status=result['status'],
            created_at=result['created_at'],
            processed_at=result['processed_at']
        )

@app.post("/api/v1/settlements/{batch_id}/process")
async def process_settlement_batch(
    batch_id: str,
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Process a settlement batch"""
    with tracer.start_as_current_span("process_settlement_batch", attributes=create_span_attributes(
        batch_id=batch_id
    )):
        async with db.acquire() as conn:
            # Get batch details
            batch = await conn.fetchrow(
                "SELECT * FROM settlement_batches WHERE batch_id = $1",
                batch_id
            )
            
            if not batch:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Settlement batch not found"
                )
            
            if batch['status'] != 'pending':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Batch is not pending. Current status: {batch['status']}"
                )
            
            # Process settlement with PSP
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{PSP_GATEWAY_URL}/api/v1/settlements",
                    json={
                        "batch_id": batch_id,
                        "psp_id": batch['psp_id'],
                        "amount": str(batch['total_amount']),
                        "transaction_count": batch['transaction_count'],
                        "transaction_ids": batch['transaction_ids']
                    },
                    headers=get_trace_headers()
                )
                
                if response.status_code == 200:
                    # Update batch status
                    await conn.execute("""
                        UPDATE settlement_batches 
                        SET status = 'processed',
                            processed_at = CURRENT_TIMESTAMP
                        WHERE batch_id = $1
                    """, batch_id)
                    
                    return {
                        "batch_id": batch_id,
                        "status": "processed",
                        "processed_at": datetime.utcnow().isoformat()
                    }
                else:
                    await conn.execute(
                        "UPDATE settlement_batches SET status = 'failed' WHERE batch_id = $1",
                        batch_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Settlement processing failed"
                    )

@app.get("/api/v1/reconciliations/stats/summary")
async def get_reconciliation_stats(
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get reconciliation statistics"""
    with tracer.start_as_current_span("get_reconciliation_stats"):
        async with db.acquire() as conn:
            # Overall stats
            overall = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_reconciliations,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
                    SUM(matched_transactions) as total_matched,
                    SUM(unmatched_transactions) as total_unmatched,
                    SUM(total_amount) as total_amount,
                    SUM(discrepancy_amount) as total_discrepancy
                FROM reconciliations
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
            """)
            
            # Discrepancy stats
            discrepancies = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_discrepancies,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                    COUNT(CASE WHEN status = 'unresolved' THEN 1 END) as unresolved,
                    COUNT(CASE WHEN discrepancy_type = 'missing_in_psp' THEN 1 END) as missing_psp,
                    COUNT(CASE WHEN discrepancy_type = 'missing_internal' THEN 1 END) as missing_internal,
                    COUNT(CASE WHEN discrepancy_type = 'amount_mismatch' THEN 1 END) as amount_mismatch,
                    COUNT(CASE WHEN discrepancy_type = 'status_mismatch' THEN 1 END) as status_mismatch
                FROM discrepancies
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
            """)
            
            # Settlement stats
            settlements = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_batches,
                    COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    SUM(total_amount) as total_settled,
                    SUM(transaction_count) as total_transactions
                FROM settlement_batches
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
            """)
        
        return {
            "reconciliations": {
                "total": overall['total_reconciliations'],
                "completed": overall['completed'],
                "failed": overall['failed'],
                "processing": overall['processing'],
                "matched_transactions": overall['total_matched'] or 0,
                "unmatched_transactions": overall['total_unmatched'] or 0
            },
            "amounts": {
                "total_processed": str(overall['total_amount'] or 0),
                "total_discrepancy": str(overall['total_discrepancy'] or 0)
            },
            "discrepancies": {
                "total": discrepancies['total_discrepancies'],
                "resolved": discrepancies['resolved'],
                "unresolved": discrepancies['unresolved'],
                "by_type": {
                    "missing_in_psp": discrepancies['missing_psp'],
                    "missing_internal": discrepancies['missing_internal'],
                    "amount_mismatch": discrepancies['amount_mismatch'],
                    "status_mismatch": discrepancies['status_mismatch']
                }
            },
            "settlements": {
                "total_batches": settlements['total_batches'],
                "processed": settlements['processed'],
                "pending": settlements['pending'],
                "total_settled": str(settlements['total_settled'] or 0),
                "total_transactions": settlements['total_transactions'] or 0
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8741)