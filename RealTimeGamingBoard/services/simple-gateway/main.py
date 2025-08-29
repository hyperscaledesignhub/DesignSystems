from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import sys
from typing import Any, Dict
import asyncio

# Import local tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing first
tracer = setup_tracing("api-gateway")

app = FastAPI(title="Simple API Gateway")

# Instrument FastAPI app for tracing
instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
USER_SERVICE = os.getenv("USER_SERVICE_URL", "http://user-service:23451")
WEBSOCKET_SERVICE = os.getenv("WEBSOCKET_SERVICE_URL", "http://websocket-service:23456")
DEMO_SERVICE = os.getenv("DEMO_SERVICE_URL", "http://demo-generator:23458")
TOURNAMENT_SERVICE = os.getenv("TOURNAMENT_SERVICE_URL", "http://tournament-service:23457")

# In-memory storage for games and leaderboard (simplified)
games_db = {}
leaderboard_db = []
scores_db = []

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api-gateway"}

# User service proxy
@app.post("/api/v1/users/register")
async def register_user(request: Request):
    with tracer.start_as_current_span("register_user", attributes=create_span_attributes(
        operation="user_registration"
    )) as span:
        async with httpx.AsyncClient() as client:
            body = await request.json()
            span.set_attributes(create_span_attributes(
                username=body.get("username", "unknown")
            ))
            response = await client.post(f"{USER_SERVICE}/api/v1/users/register", json=body, headers=get_trace_headers())
            return response.json()

@app.post("/api/v1/users/login")
async def login_user(request: Request):
    with tracer.start_as_current_span("login_user", attributes=create_span_attributes(
        operation="user_login"
    )) as span:
        async with httpx.AsyncClient() as client:
            body = await request.json()
            span.set_attributes(create_span_attributes(
                username=body.get("username", "unknown")
            ))
            response = await client.post(f"{USER_SERVICE}/api/v1/users/login", json=body, headers=get_trace_headers())
            return response.json()

# Game management (simplified in-memory)
@app.post("/api/v1/games")
async def create_game(request: Request):
    body = await request.json()
    game_id = f"game_{len(games_db) + 1}"
    games_db[game_id] = {
        "game_id": game_id,
        "name": body.get("name", "Unknown Game"),
        "description": body.get("description", ""),
        "max_players": body.get("max_players", 100),
        "scoring_type": body.get("scoring_type", "points")
    }
    return games_db[game_id]

@app.get("/api/v1/games")
async def list_games():
    return list(games_db.values())

# Score submission (simplified)
@app.post("/api/v1/scores")
async def submit_score(request: Request):
    with tracer.start_as_current_span("submit_score", attributes=create_span_attributes(
        operation="score_submission"
    )) as span:
        body = await request.json()
        score_entry = {
            "user_id": body.get("user_id"),
            "game_id": body.get("game_id"),
            "score": body.get("score", 0),
            "timestamp": body.get("timestamp", "")
        }
        
        span.set_attributes(create_span_attributes(
            user_id=score_entry["user_id"],
            game_id=score_entry["game_id"],
            score=score_entry["score"]
        ))
        
        scores_db.append(score_entry)
        
        # Update leaderboard
        update_leaderboard()
        
        # Broadcast via websocket
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{WEBSOCKET_SERVICE}/broadcast/score", json={
                    "type": "score_update",
                    "data": score_entry
                }, headers=get_trace_headers())
        except:
            pass
        
        return {"status": "success", "score": score_entry}

# Leaderboard
@app.get("/api/v1/leaderboard/global")
async def get_global_leaderboard():
    with tracer.start_as_current_span("get_global_leaderboard", attributes=create_span_attributes(
        operation="leaderboard_fetch",
        total_scores=len(scores_db)
    )) as span:
        # Aggregate scores by user
        user_scores = {}
        for score in scores_db:
            user_id = score["user_id"]
            if user_id not in user_scores:
                user_scores[user_id] = {
                    "user_id": user_id,
                    "display_name": f"Player_{user_id[-6:]}",
                    "total_score": 0,
                    "games_played": 0
                }
            user_scores[user_id]["total_score"] += score["score"]
            user_scores[user_id]["games_played"] += 1
        
        # Sort by total score
        leaderboard = sorted(user_scores.values(), key=lambda x: x["total_score"], reverse=True)
        
        span.set_attributes(create_span_attributes(
            unique_users=len(user_scores),
            leaderboard_size=len(leaderboard[:50])
        ))
        
        return leaderboard[:50]

@app.get("/api/v1/leaderboard/game/{game_id}")
async def get_game_leaderboard(game_id: str):
    # Filter scores for specific game
    game_scores = [s for s in scores_db if s.get("game_id") == game_id]
    
    user_scores = {}
    for score in game_scores:
        user_id = score["user_id"]
        if user_id not in user_scores:
            user_scores[user_id] = {
                "user_id": user_id,
                "display_name": f"Player_{user_id[-6:]}",
                "score": 0,
                "game_name": games_db.get(game_id, {}).get("name", "Unknown")
            }
        user_scores[user_id]["score"] += score["score"]
    
    leaderboard = sorted(user_scores.values(), key=lambda x: x["score"], reverse=True)
    return leaderboard[:50]

# Tournament service proxy
@app.post("/api/v1/tournaments")
async def create_tournament(request: Request):
    with tracer.start_as_current_span("create_tournament", attributes=create_span_attributes(
        operation="tournament_creation"
    )) as span:
        async with httpx.AsyncClient() as client:
            body = await request.json()
            span.set_attributes(create_span_attributes(
                tournament_name=body.get("name", "unknown")
            ))
            response = await client.post(f"{TOURNAMENT_SERVICE}/api/v1/tournaments", json=body, headers=get_trace_headers())
            return response.json()

@app.get("/api/v1/tournaments")
async def list_tournaments():
    with tracer.start_as_current_span("list_tournaments", attributes=create_span_attributes(
        operation="tournament_list"
    )) as span:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TOURNAMENT_SERVICE}/api/v1/tournaments", headers=get_trace_headers())
            tournaments = response.json()
            span.set_attributes(create_span_attributes(
                tournament_count=len(tournaments)
            ))
            return tournaments

@app.post("/api/v1/tournaments/register")
async def register_tournament(request: Request):
    with tracer.start_as_current_span("register_tournament", attributes=create_span_attributes(
        operation="tournament_registration"
    )) as span:
        async with httpx.AsyncClient() as client:
            body = await request.json()
            span.set_attributes(create_span_attributes(
                tournament_id=body.get("tournament_id", "unknown"),
                user_id=body.get("user_id", "unknown")
            ))
            response = await client.post(f"{TOURNAMENT_SERVICE}/api/v1/tournaments/register", json=body, headers=get_trace_headers())
            return response.json()

@app.post("/api/v1/tournaments/update-score")
async def update_tournament_score(request: Request):
    with tracer.start_as_current_span("update_tournament_score", attributes=create_span_attributes(
        operation="tournament_score_update"
    )) as span:
        async with httpx.AsyncClient() as client:
            body = await request.json()
            span.set_attributes(create_span_attributes(
                tournament_id=body.get("tournament_id", "unknown"),
                user_id=body.get("user_id", "unknown"),
                score=body.get("score", 0)
            ))
            response = await client.post(f"{TOURNAMENT_SERVICE}/api/v1/tournaments/update-score", json=body, headers=get_trace_headers())
            return response.json()

# Demo controls proxy
@app.post("/api/v1/demo/start")
async def start_demo():
    with tracer.start_as_current_span("start_demo", attributes=create_span_attributes(
        operation="demo_control"
    )) as span:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{DEMO_SERVICE}/api/v1/demo/start", headers=get_trace_headers())
            return response.json()

@app.post("/api/v1/demo/stop")
async def stop_demo():
    with tracer.start_as_current_span("stop_demo", attributes=create_span_attributes(
        operation="demo_control"
    )) as span:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{DEMO_SERVICE}/api/v1/demo/stop", headers=get_trace_headers())
            return response.json()

@app.post("/api/v1/demo/populate")
async def populate_demo(request: Request):
    body = await request.json() if await request.body() else {}
    
    # Create some demo games first
    demo_games = [
        {"name": "Battle Royale", "description": "Last player standing wins", "max_players": 100},
        {"name": "Racing Championship", "description": "Fastest lap times", "max_players": 8},
        {"name": "Puzzle Master", "description": "Solve puzzles quickly", "max_players": 1},
        {"name": "Strategy Wars", "description": "Conquer territories", "max_players": 4},
        {"name": "Space Shooter", "description": "Destroy enemy ships", "max_players": 2}
    ]
    
    for game in demo_games[:body.get("games", 3)]:
        game_id = f"game_{len(games_db) + 1}"
        games_db[game_id] = {
            "game_id": game_id,
            **game
        }
    
    # Proxy to demo service for users
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{DEMO_SERVICE}/api/v1/demo/populate", json=body, headers=get_trace_headers())
            result = response.json()
        except:
            result = {"counts": {"users": 0}}
    
    # Generate some random scores
    import random
    for _ in range(50):
        scores_db.append({
            "user_id": f"user_{random.randint(1, 30)}",
            "game_id": random.choice(list(games_db.keys())) if games_db else "game_1",
            "score": random.randint(100, 10000),
            "timestamp": "2024-01-01T12:00:00Z"
        })
    
    update_leaderboard()
    
    return {
        "status": "populated",
        "counts": {
            "users": result.get("counts", {}).get("users", 0),
            "games": len(games_db),
            "tournaments": 1
        }
    }

@app.post("/api/v1/demo/burst")
async def burst_demo():
    # Simulate burst activity
    asyncio.create_task(simulate_burst())
    return {"status": "burst_started", "duration": 30}

async def simulate_burst():
    import random
    from datetime import datetime
    
    # Get current leaderboard to create competitive dynamics
    current_leaderboard = await get_global_leaderboard()
    
    for round_num in range(30):
        await asyncio.sleep(1)
        
        # Create competitive scenarios
        if round_num % 5 == 0:
            # Every 5 seconds, boost lower-ranked players to create rank changes
            await create_competitive_round(current_leaderboard)
        else:
            # Regular random activity
            await create_regular_activity()
        
        # Broadcast leaderboard update via websocket
        try:
            new_leaderboard = await get_global_leaderboard()
            async with httpx.AsyncClient() as client:
                await client.post(f"{WEBSOCKET_SERVICE}/broadcast/leaderboard", json={
                    "type": "leaderboard_update",
                    "data": new_leaderboard[:10],  # Top 10
                    "timestamp": datetime.utcnow().isoformat()
                }, headers=get_trace_headers())
        except:
            pass

async def create_competitive_round(current_leaderboard):
    import random
    from datetime import datetime
    
    # Strategy: Give high scores to lower-ranked players to shake up rankings
    if len(current_leaderboard) >= 10:
        # Boost players ranked 5-15 to challenge top 5
        boost_candidates = current_leaderboard[5:15] if len(current_leaderboard) > 15 else current_leaderboard[5:]
        
        for player in boost_candidates[:3]:  # Boost top 3 candidates
            # Give them significantly high scores
            big_score = random.randint(8000, 15000)
            scores_db.append({
                "user_id": player["user_id"],
                "game_id": random.choice(list(games_db.keys())) if games_db else "game_1",
                "score": big_score,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    # Also add some regular activity
    await create_regular_activity()

async def create_regular_activity():
    import random
    from datetime import datetime
    
    for _ in range(random.randint(3, 12)):
        scores_db.append({
            "user_id": f"user_{random.randint(1, 50)}",
            "game_id": random.choice(list(games_db.keys())) if games_db else "game_1",
            "score": random.randint(100, 3000),
            "timestamp": datetime.utcnow().isoformat()
        })

@app.get("/api/v1/demo/status")
async def demo_status():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DEMO_SERVICE}/api/v1/demo/status", headers=get_trace_headers())
            return response.json()
        except:
            return {"is_running": False, "users_count": 0, "games_count": len(games_db), "tournaments_count": 0}

def update_leaderboard():
    global leaderboard_db
    # This would normally update a proper leaderboard
    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "23455"))
    uvicorn.run(app, host="0.0.0.0", port=port)