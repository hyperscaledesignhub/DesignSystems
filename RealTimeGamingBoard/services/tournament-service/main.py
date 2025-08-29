from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncpg
import redis.asyncio as redis
import json
import os
from datetime import datetime, timedelta
import logging
import random
import asyncio
import httpx
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import local tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing first
tracer = setup_tracing("tournament-service")

app = FastAPI(title="Tournament Service")

# Instrument FastAPI app for tracing
instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Tournament(BaseModel):
    name: str
    game_id: str
    max_participants: int = 100
    entry_fee: float = 0
    prize_pool: float = 0
    start_time: datetime
    end_time: datetime
    rules: Optional[Dict] = {}

class TournamentRegistration(BaseModel):
    tournament_id: str
    user_id: str

class TournamentUpdate(BaseModel):
    tournament_id: str
    user_id: str
    score: int

db_pool = None
redis_client = None

async def get_db():
    global db_pool
    if not db_pool:
        db_url = os.getenv("DATABASE_URL", "postgresql://gaming:gaming123@postgres:5432/gamingdb")
        db_pool = await asyncpg.create_pool(db_url)
    return db_pool

async def get_redis():
    global redis_client
    if not redis_client:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        redis_client = await redis.from_url(redis_url, decode_responses=True)
    return redis_client

@app.on_event("startup")
async def startup():
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tournaments (
                tournament_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) NOT NULL,
                game_id VARCHAR(100) NOT NULL,
                status VARCHAR(50) DEFAULT 'upcoming',
                max_participants INT DEFAULT 100,
                current_participants INT DEFAULT 0,
                entry_fee DECIMAL(10, 2) DEFAULT 0,
                prize_pool DECIMAL(10, 2) DEFAULT 0,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                rules JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tournament_participants (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tournament_id UUID REFERENCES tournaments(tournament_id),
                user_id UUID NOT NULL,
                score INT DEFAULT 0,
                rank INT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tournament_id, user_id)
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tournament_results (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tournament_id UUID REFERENCES tournaments(tournament_id),
                user_id UUID NOT NULL,
                final_rank INT NOT NULL,
                score INT NOT NULL,
                prize_won DECIMAL(10, 2) DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    asyncio.create_task(tournament_status_updater())

async def tournament_status_updater():
    while True:
        try:
            pool = await get_db()
            async with pool.acquire() as conn:
                now = datetime.utcnow()
                
                await conn.execute('''
                    UPDATE tournaments 
                    SET status = 'active' 
                    WHERE status = 'upcoming' AND start_time <= $1
                ''', now)
                
                ended = await conn.fetch('''
                    UPDATE tournaments 
                    SET status = 'completed' 
                    WHERE status = 'active' AND end_time <= $1
                    RETURNING tournament_id
                ''', now)
                
                for tournament in ended:
                    await finalize_tournament(str(tournament['tournament_id']))
                    
        except Exception as e:
            logger.error(f"Error updating tournament status: {e}")
        
        await asyncio.sleep(30)

async def finalize_tournament(tournament_id: str):
    pool = await get_db()
    r = await get_redis()
    
    async with pool.acquire() as conn:
        participants = await conn.fetch('''
            SELECT user_id, score 
            FROM tournament_participants 
            WHERE tournament_id = $1 
            ORDER BY score DESC
        ''', tournament_id)
        
        tournament = await conn.fetchrow('''
            SELECT prize_pool FROM tournaments WHERE tournament_id = $1
        ''', tournament_id)
        
        prize_distribution = {
            1: 0.5,
            2: 0.3,
            3: 0.2
        }
        
        for idx, participant in enumerate(participants, 1):
            prize = 0
            if idx <= 3 and tournament['prize_pool'] > 0:
                prize = float(tournament['prize_pool']) * prize_distribution.get(idx, 0)
            
            await conn.execute('''
                INSERT INTO tournament_results (tournament_id, user_id, final_rank, score, prize_won)
                VALUES ($1, $2, $3, $4, $5)
            ''', tournament_id, participant['user_id'], idx, participant['score'], prize)
        
        await r.publish("tournament:updates", json.dumps({
            "type": "tournament_ended",
            "tournament_id": tournament_id,
            "winners": [
                {"rank": idx + 1, "user_id": str(p['user_id']), "score": p['score']}
                for idx, p in enumerate(participants[:3])
            ]
        }))

@app.post("/api/v1/tournaments")
async def create_tournament(tournament: Tournament):
    with tracer.start_as_current_span("create_tournament", attributes=create_span_attributes(
        operation="tournament_creation",
        tournament_name=tournament.name,
        game_id=tournament.game_id,
        max_participants=tournament.max_participants,
        prize_pool=tournament.prize_pool
    )) as span:
        pool = await get_db()
        r = await get_redis()
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow('''
                INSERT INTO tournaments (name, game_id, max_participants, entry_fee, prize_pool, start_time, end_time, rules)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING tournament_id, status, current_participants
            ''', tournament.name, tournament.game_id, tournament.max_participants, 
            tournament.entry_fee, tournament.prize_pool, tournament.start_time, 
            tournament.end_time, json.dumps(tournament.rules))
        
        tournament_data = {
            "tournament_id": str(result['tournament_id']),
            "name": tournament.name,
            "status": result['status'],
            "participants": result['current_participants'],
            "max_participants": tournament.max_participants
        }
        
        span.set_attributes(create_span_attributes(
            tournament_id=tournament_data["tournament_id"],
            creation_success=True
        ))
        
        await r.publish("tournament:updates", json.dumps({
            "type": "tournament_created",
            "tournament": tournament_data
        }))
        
        return tournament_data

@app.post("/api/v1/tournaments/register")
async def register_for_tournament(registration: TournamentRegistration):
    pool = await get_db()
    r = await get_redis()
    
    async with pool.acquire() as conn:
        tournament = await conn.fetchrow('''
            SELECT status, current_participants, max_participants, entry_fee 
            FROM tournaments WHERE tournament_id = $1
        ''', registration.tournament_id)
        
        if not tournament:
            raise HTTPException(status_code=404, detail="Tournament not found")
        
        if tournament['status'] != 'upcoming':
            raise HTTPException(status_code=400, detail="Tournament registration closed")
        
        if tournament['current_participants'] >= tournament['max_participants']:
            raise HTTPException(status_code=400, detail="Tournament is full")
        
        try:
            await conn.execute('''
                INSERT INTO tournament_participants (tournament_id, user_id)
                VALUES ($1, $2)
            ''', registration.tournament_id, registration.user_id)
            
            await conn.execute('''
                UPDATE tournaments 
                SET current_participants = current_participants + 1 
                WHERE tournament_id = $1
            ''', registration.tournament_id)
            
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Already registered")
    
    await r.publish("tournament:updates", json.dumps({
        "type": "player_registered",
        "tournament_id": registration.tournament_id,
        "user_id": registration.user_id
    }))
    
    return {"status": "registered", "tournament_id": registration.tournament_id}

@app.post("/api/v1/tournaments/update-score")
async def update_tournament_score(update: TournamentUpdate):
    pool = await get_db()
    r = await get_redis()
    
    async with pool.acquire() as conn:
        tournament = await conn.fetchrow('''
            SELECT status FROM tournaments WHERE tournament_id = $1
        ''', update.tournament_id)
        
        if not tournament or tournament['status'] != 'active':
            raise HTTPException(status_code=400, detail="Tournament not active")
        
        await conn.execute('''
            UPDATE tournament_participants 
            SET score = score + $1 
            WHERE tournament_id = $2 AND user_id = $3
        ''', update.score, update.tournament_id, update.user_id)
        
        participants = await conn.fetch('''
            SELECT user_id, score 
            FROM tournament_participants 
            WHERE tournament_id = $1 
            ORDER BY score DESC 
            LIMIT 10
        ''', update.tournament_id)
    
    leaderboard = [
        {"rank": idx + 1, "user_id": str(p['user_id']), "score": p['score']}
        for idx, p in enumerate(participants)
    ]
    
    await r.publish("tournament:updates", json.dumps({
        "type": "leaderboard_update",
        "tournament_id": update.tournament_id,
        "leaderboard": leaderboard
    }))
    
    cache_key = f"tournament:leaderboard:{update.tournament_id}"
    await r.setex(cache_key, 30, json.dumps(leaderboard))
    
    return {"status": "updated", "new_score": update.score}

@app.get("/api/v1/tournaments")
async def get_tournaments(status: Optional[str] = None):
    with tracer.start_as_current_span("get_tournaments", attributes=create_span_attributes(
        operation="tournament_list",
        status_filter=status or "all"
    )) as span:
        pool = await get_db()
        
        async with pool.acquire() as conn:
            if status:
                tournaments = await conn.fetch('''
                    SELECT tournament_id, name, game_id, status, max_participants, 
                           current_participants, prize_pool, start_time, end_time
                    FROM tournaments 
                    WHERE status = $1
                    ORDER BY start_time DESC
                    LIMIT 20
                ''', status)
            else:
                tournaments = await conn.fetch('''
                    SELECT tournament_id, name, game_id, status, max_participants, 
                           current_participants, prize_pool, start_time, end_time
                    FROM tournaments 
                    ORDER BY start_time DESC
                    LIMIT 20
                ''')
        
        span.set_attributes(create_span_attributes(
            tournament_count=len(tournaments)
        ))
        
        return [
            {
                "tournament_id": str(t['tournament_id']),
                "name": t['name'],
                "game_id": t['game_id'],
                "status": t['status'],
                "participants": f"{t['current_participants']}/{t['max_participants']}",
                "prize_pool": float(t['prize_pool']),
            "start_time": t['start_time'].isoformat(),
            "end_time": t['end_time'].isoformat()
        }
        for t in tournaments
    ]

@app.get("/api/v1/tournaments/{tournament_id}/leaderboard")
async def get_tournament_leaderboard(tournament_id: str):
    r = await get_redis()
    
    cache_key = f"tournament:leaderboard:{tournament_id}"
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    pool = await get_db()
    async with pool.acquire() as conn:
        participants = await conn.fetch('''
            SELECT p.user_id, p.score, u.display_name
            FROM tournament_participants p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.tournament_id = $1
            ORDER BY p.score DESC
            LIMIT 50
        ''', tournament_id)
    
    leaderboard = [
        {
            "rank": idx + 1,
            "user_id": str(p['user_id']),
            "display_name": p['display_name'],
            "score": p['score']
        }
        for idx, p in enumerate(participants)
    ]
    
    await r.setex(cache_key, 30, json.dumps(leaderboard))
    return leaderboard

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "tournament-service"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "23457"))
    uvicorn.run(app, host="0.0.0.0", port=port)