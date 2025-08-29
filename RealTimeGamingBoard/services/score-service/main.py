import os
import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import asyncio
from datetime import datetime
import httpx
import logging

app = FastAPI(title="Score Service")

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/gaming")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LEADERBOARD_SERVICE_URL = os.getenv("LEADERBOARD_SERVICE_URL", "http://localhost:23453")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "23454"))

# Database connection
db_pool = None
redis_client = None

# Pydantic models
class UserScore(BaseModel):
    user_id: str
    current_score: int
    month: str
    total_lifetime_score: int

class ScoreHistory(BaseModel):
    month: str
    score: int

class UserScoreHistory(BaseModel):
    user_id: str
    history: list[ScoreHistory]

# Event processor
class EventProcessor:
    def __init__(self):
        self.running = False
        self.task = None

    async def start(self):
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self.process_events())

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def process_events(self):
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("match_events")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        await self.handle_match_won_event(event)
                    except Exception as e:
                        logging.error(f"Error processing event: {e}")
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe("match_events")
            await pubsub.close()

    async def handle_match_won_event(self, event):
        if event.get("event") != "match_won":
            return

        user_id = event.get("user_id")
        match_id = event.get("match_id")
        points = event.get("points", 1)
        timestamp = event.get("timestamp")
        
        if not user_id or not match_id:
            logging.error(f"Invalid event data: {event}")
            return

        month = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m')
        
        try:
            # Store score in database
            async with db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO scores (user_id, match_id, points, month)
                    VALUES ($1::uuid, $2::uuid, $3, $4)
                    ON CONFLICT (match_id) DO NOTHING
                ''', user_id, match_id, points, month)

                # Update monthly score
                await conn.execute('''
                    INSERT INTO monthly_scores (user_id, month, total_score)
                    VALUES ($1::uuid, $2, $3)
                    ON CONFLICT (user_id, month)
                    DO UPDATE SET total_score = monthly_scores.total_score + $3,
                                  updated_at = CURRENT_TIMESTAMP
                ''', user_id, month, points)

            # Update leaderboard via API
            await self.update_leaderboard(user_id, points)
            
            # Publish score updated event
            score_event = {
                "event": "score_updated",
                "user_id": user_id,
                "points_added": points,
                "month": month,
                "timestamp": timestamp
            }
            await redis_client.publish("score_events", json.dumps(score_event))
            
            logging.info(f"Processed match won for user {user_id}, points: {points}")

        except Exception as e:
            logging.error(f"Error handling match won event: {e}")

    async def update_leaderboard(self, user_id: str, points: int):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{LEADERBOARD_SERVICE_URL}/api/v1/leaderboard/score",
                    json={"user_id": user_id, "points": points}
                )
                if response.status_code != 200:
                    logging.error(f"Failed to update leaderboard: {response.status_code}")
        except Exception as e:
            logging.error(f"Error calling leaderboard service: {e}")

event_processor = EventProcessor()

# Database functions
async def init_db():
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    redis_client = redis.Redis.from_url(REDIS_URL)
    
    # Create tables
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                match_id UUID NOT NULL,
                points INT NOT NULL DEFAULT 1,
                month VARCHAR(7) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(match_id)
            );

            CREATE INDEX IF NOT EXISTS idx_user_scores ON scores(user_id, month);
            CREATE INDEX IF NOT EXISTS idx_monthly_scores ON scores(month, created_at);

            CREATE TABLE IF NOT EXISTS monthly_scores (
                user_id UUID NOT NULL,
                month VARCHAR(7) NOT NULL,
                total_score INT NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, month)
            );
        ''')

def get_current_month():
    return datetime.utcnow().strftime('%Y-%m')

# Routes
@app.get("/api/v1/scores/{user_id}", response_model=UserScore)
async def get_user_score(user_id: str):
    current_month = get_current_month()
    
    async with db_pool.acquire() as conn:
        # Get current month score
        current_score = await conn.fetchval('''
            SELECT total_score FROM monthly_scores
            WHERE user_id = $1::uuid AND month = $2
        ''', user_id, current_month)
        
        if current_score is None:
            current_score = 0

        # Get total lifetime score
        total_score = await conn.fetchval('''
            SELECT SUM(total_score) FROM monthly_scores
            WHERE user_id = $1::uuid
        ''', user_id)
        
        if total_score is None:
            total_score = 0

    return UserScore(
        user_id=user_id,
        current_score=current_score,
        month=current_month,
        total_lifetime_score=total_score
    )

@app.get("/api/v1/scores/{user_id}/history", response_model=UserScoreHistory)
async def get_score_history(user_id: str):
    async with db_pool.acquire() as conn:
        scores = await conn.fetch('''
            SELECT month, total_score
            FROM monthly_scores
            WHERE user_id = $1::uuid
            ORDER BY month DESC
            LIMIT 6
        ''', user_id)

    history = [
        ScoreHistory(month=score['month'], score=score['total_score'])
        for score in scores
    ]

    return UserScoreHistory(user_id=user_id, history=history)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "score-service"}

@app.on_event("startup")
async def startup_event():
    await init_db()
    await event_processor.start()

@app.on_event("shutdown")
async def shutdown_event():
    await event_processor.stop()
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)