import os
import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta
import json
import httpx

app = FastAPI(title="Game Service")
security = HTTPBearer()

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/gaming")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:23451")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "23452"))

# Database connection
db_pool = None
redis_client = None

# Pydantic models
class MatchStart(BaseModel):
    user_id: str
    game_mode: str = "standard"

class MatchEnd(BaseModel):
    match_id: str
    user_id: str
    result: str  # "win" or "lose"

class MatchResponse(BaseModel):
    match_id: str
    user_id: str
    game_mode: str
    start_time: datetime
    end_time: datetime = None
    result: str = None
    points_earned: int = 0

class MatchResult(BaseModel):
    match_result: str
    points_earned: int

# Database functions
async def init_db():
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    redis_client = redis.Redis.from_url(REDIS_URL)
    
    # Create tables
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                game_mode VARCHAR(20) DEFAULT 'standard',
                start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                result VARCHAR(10),
                points_earned INT DEFAULT 0
            );
            
            CREATE INDEX IF NOT EXISTS idx_user_matches ON matches(user_id, start_time DESC);
            CREATE INDEX IF NOT EXISTS idx_match_time ON matches(start_time);
        ''')

async def validate_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{USER_SERVICE_URL}/api/v1/users/validate",
                json={"token": token}
            )
            if response.status_code == 200:
                data = response.json()
                return data["user_id"]
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
        except Exception:
            raise HTTPException(status_code=401, detail="Could not validate token")

async def check_anti_cheat(user_id: str) -> bool:
    today = datetime.utcnow().date()
    async with db_pool.acquire() as conn:
        wins_today = await conn.fetchval('''
            SELECT COUNT(*) FROM matches
            WHERE user_id = $1::uuid AND result = 'win'
            AND DATE(start_time) = $2
        ''', user_id, today)
    
    return wins_today < 50  # Max 50 wins per day

# Routes
@app.post("/api/v1/games/match/start", response_model=MatchResponse)
async def start_match(match_data: MatchStart, user_id: str = Depends(validate_user_token)):
    if match_data.user_id != user_id:
        raise HTTPException(status_code=403, detail="User mismatch")
    
    async with db_pool.acquire() as conn:
        match = await conn.fetchrow('''
            INSERT INTO matches (user_id, game_mode)
            VALUES ($1::uuid, $2)
            RETURNING match_id::text, user_id::text, game_mode, start_time
        ''', user_id, match_data.game_mode)
    
    return MatchResponse(
        match_id=match['match_id'],
        user_id=match['user_id'],
        game_mode=match['game_mode'],
        start_time=match['start_time']
    )

@app.post("/api/v1/games/match/end", response_model=MatchResult)
async def end_match(match_data: MatchEnd, user_id: str = Depends(validate_user_token)):
    if match_data.user_id != user_id:
        raise HTTPException(status_code=403, detail="User mismatch")
    
    if match_data.result not in ["win", "lose"]:
        raise HTTPException(status_code=400, detail="Result must be 'win' or 'lose'")
    
    async with db_pool.acquire() as conn:
        # Get match and validate
        match = await conn.fetchrow('''
            SELECT match_id, user_id::text, start_time, end_time
            FROM matches
            WHERE match_id = $1::uuid AND user_id = $2::uuid
        ''', match_data.match_id, user_id)
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        if match['end_time']:
            raise HTTPException(status_code=400, detail="Match already ended")
        
        # Validate match duration (min 30 seconds)
        duration = datetime.utcnow() - match['start_time']
        if duration.total_seconds() < 30:
            raise HTTPException(status_code=400, detail="Match too short")
    
    points_earned = 0
    
    if match_data.result == "win":
        # Anti-cheat check
        if not await check_anti_cheat(user_id):
            raise HTTPException(status_code=429, detail="Too many wins today")
        
        points_earned = 1
        
        # Publish win event to Redis
        win_event = {
            "event": "match_won",
            "user_id": user_id,
            "match_id": match_data.match_id,
            "points": points_earned,
            "timestamp": datetime.utcnow().isoformat()
        }
        await redis_client.publish("match_events", json.dumps(win_event))
    
    # Update match
    async with db_pool.acquire() as conn:
        await conn.execute('''
            UPDATE matches
            SET end_time = CURRENT_TIMESTAMP, result = $1, points_earned = $2
            WHERE match_id = $3::uuid
        ''', match_data.result, points_earned, match_data.match_id)
    
    return MatchResult(match_result=match_data.result, points_earned=points_earned)

@app.get("/api/v1/games/user/{user_id}/matches")
async def get_match_history(user_id: str, current_user: str = Depends(validate_user_token)):
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check cache first
    cached_matches = await redis_client.get(f"matches:history:{user_id}")
    if cached_matches:
        return json.loads(cached_matches)
    
    async with db_pool.acquire() as conn:
        matches = await conn.fetch('''
            SELECT match_id::text, game_mode, start_time, end_time, result, points_earned
            FROM matches
            WHERE user_id = $1::uuid
            ORDER BY start_time DESC
            LIMIT 10
        ''', user_id)
    
    match_list = []
    for match in matches:
        match_list.append({
            "match_id": match['match_id'],
            "game_mode": match['game_mode'],
            "start_time": match['start_time'].isoformat() if match['start_time'] else None,
            "end_time": match['end_time'].isoformat() if match['end_time'] else None,
            "result": match['result'],
            "points_earned": match['points_earned']
        })
    
    # Cache for 1 minute
    await redis_client.setex(f"matches:history:{user_id}", 60, json.dumps(match_list))
    
    return {"matches": match_list}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "game-service"}

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)