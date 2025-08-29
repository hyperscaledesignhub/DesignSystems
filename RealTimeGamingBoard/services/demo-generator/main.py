from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import random
import json
from datetime import datetime, timedelta
import os
import sys
import logging
from typing import List
import names
import uuid
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import local tracing module
from tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

# Initialize tracing first
tracer = setup_tracing("demo-generator")

app = FastAPI(title="Demo Data Generator")

# Instrument FastAPI app for tracing
instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_GATEWAY = os.getenv("API_GATEWAY_URL", "http://api-gateway:23455")
WEBSOCKET_SERVICE = os.getenv("WEBSOCKET_URL", "http://websocket-service:23456")

class DemoGenerator:
    def __init__(self):
        self.users = []
        self.games = []
        self.tournaments = []
        self.is_running = False
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def create_demo_users(self, count: int = 50):
        logger.info(f"Creating {count} demo users...")
        for i in range(count):
            try:
                name = names.get_full_name()
                username = name.lower().replace(" ", "_") + str(random.randint(100, 999))
                
                response = await self.client.post(
                    f"{API_GATEWAY}/api/v1/users/register",
                    json={
                        "username": username,
                        "email": f"{username}@demo.com",
                        "password": "demo123"
                    }
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    self.users.append({
                        "user_id": user_data["user_id"],
                        "username": username,
                        "display_name": name,
                        "token": user_data.get("auth_token")
                    })
                    logger.info(f"Created user: {username}")
                    
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                
        return self.users
    
    async def create_demo_games(self, count: int = 10):
        logger.info(f"Creating {count} demo games...")
        game_types = [
            ("Battle Royale", "Last player standing wins"),
            ("Racing Championship", "Fastest lap times"),
            ("Puzzle Master", "Solve puzzles quickly"),
            ("Strategy Wars", "Conquer territories"),
            ("Space Shooter", "Destroy enemy ships"),
            ("Card Battle", "Collectible card game"),
            ("Sports League", "Score goals to win"),
            ("Adventure Quest", "Complete missions"),
            ("Tower Defense", "Defend your base"),
            ("Fighting Arena", "1v1 combat battles")
        ]
        
        for i in range(min(count, len(game_types))):
            try:
                game_name, description = game_types[i]
                response = await self.client.post(
                    f"{API_GATEWAY}/api/v1/games",
                    json={
                        "name": game_name,
                        "description": description,
                        "max_players": random.choice([1, 2, 4, 8, 100]),
                        "scoring_type": random.choice(["points", "time", "elimination"])
                    }
                )
                
                if response.status_code == 200:
                    game_data = response.json()
                    self.games.append(game_data)
                    logger.info(f"Created game: {game_name}")
                    
            except Exception as e:
                logger.error(f"Error creating game: {e}")
                
        return self.games
    
    async def create_demo_tournaments(self, count: int = 5):
        logger.info(f"Creating {count} demo tournaments...")
        
        if not self.games:
            await self.create_demo_games()
            
        tournament_names = [
            "Weekend Warriors Championship",
            "Elite Players League",
            "Beginner's Cup",
            "Pro Tournament Series",
            "Global Gaming Festival",
            "Summer Showdown",
            "Winter Championship",
            "Spring Tournament"
        ]
        
        for i in range(min(count, len(tournament_names))):
            try:
                game = random.choice(self.games)
                start_time = datetime.utcnow() + timedelta(minutes=random.randint(5, 30))
                
                response = await self.client.post(
                    f"{API_GATEWAY}/api/v1/tournaments",
                    json={
                        "name": tournament_names[i],
                        "game_id": game["game_id"],
                        "max_participants": random.choice([16, 32, 64, 100]),
                        "entry_fee": random.choice([0, 5, 10, 25]),
                        "prize_pool": random.choice([100, 500, 1000, 5000]),
                        "start_time": start_time.isoformat(),
                        "end_time": (start_time + timedelta(hours=2)).isoformat(),
                        "rules": {
                            "format": random.choice(["elimination", "round_robin", "swiss"]),
                            "rounds": random.randint(3, 7)
                        }
                    }
                )
                
                if response.status_code == 200:
                    tournament_data = response.json()
                    self.tournaments.append(tournament_data)
                    logger.info(f"Created tournament: {tournament_names[i]}")
                    
            except Exception as e:
                logger.error(f"Error creating tournament: {e}")
                
        return self.tournaments
    
    async def simulate_gameplay(self):
        logger.info("Starting gameplay simulation...")
        
        while self.is_running:
            try:
                if not self.users or not self.games:
                    await asyncio.sleep(5)
                    continue
                    
                num_actions = random.randint(5, 15)
                
                for _ in range(num_actions):
                    user = random.choice(self.users)
                    game = random.choice(self.games)
                    score = random.randint(10, 500) * random.randint(1, 10)
                    
                    try:
                        await self.client.post(
                            f"{API_GATEWAY}/api/v1/scores",
                            json={
                                "user_id": user["user_id"],
                                "game_id": game["game_id"],
                                "score": score
                            },
                            headers={"Authorization": f"Bearer {user.get('token', '')}"}
                        )
                        
                        await self.client.post(
                            f"{WEBSOCKET_SERVICE}/broadcast/game",
                            json={
                                "type": "score_update",
                                "user": user["display_name"],
                                "game": game["name"],
                                "score": score,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                        
                        logger.info(f"Score update: {user['display_name']} scored {score} in {game['name']}")
                        
                    except Exception as e:
                        logger.error(f"Error simulating score: {e}")
                
                await asyncio.sleep(random.uniform(2, 8))
                
            except Exception as e:
                logger.error(f"Error in gameplay simulation: {e}")
                await asyncio.sleep(5)
    
    async def simulate_tournaments(self):
        logger.info("Starting tournament simulation...")
        
        while self.is_running:
            try:
                if not self.tournaments or not self.users:
                    await asyncio.sleep(10)
                    continue
                
                for tournament in self.tournaments:
                    if random.random() < 0.3:
                        user = random.choice(self.users)
                        
                        try:
                            await self.client.post(
                                f"{API_GATEWAY}/api/v1/tournaments/register",
                                json={
                                    "tournament_id": tournament["tournament_id"],
                                    "user_id": user["user_id"]
                                }
                            )
                            logger.info(f"{user['display_name']} joined {tournament['name']}")
                            
                        except Exception as e:
                            logger.debug(f"Tournament registration failed: {e}")
                    
                    if random.random() < 0.5:
                        participating_users = random.sample(self.users, min(5, len(self.users)))
                        
                        for user in participating_users:
                            score = random.randint(100, 2000)
                            
                            try:
                                await self.client.post(
                                    f"{API_GATEWAY}/api/v1/tournaments/update-score",
                                    json={
                                        "tournament_id": tournament["tournament_id"],
                                        "user_id": user["user_id"],
                                        "score": score
                                    }
                                )
                                
                            except Exception as e:
                                logger.debug(f"Tournament score update failed: {e}")
                
                await asyncio.sleep(random.uniform(5, 15))
                
            except Exception as e:
                logger.error(f"Error in tournament simulation: {e}")
                await asyncio.sleep(10)

generator = DemoGenerator()

@app.on_event("startup")
async def startup():
    await asyncio.sleep(5)
    asyncio.create_task(initialize_demo_data())

async def initialize_demo_data():
    logger.info("Initializing demo data...")
    await generator.create_demo_users(30)
    await generator.create_demo_games(8)
    await generator.create_demo_tournaments(4)
    
    generator.is_running = True
    asyncio.create_task(generator.simulate_gameplay())
    asyncio.create_task(generator.simulate_tournaments())

@app.post("/api/v1/demo/start")
async def start_demo():
    if generator.is_running:
        return {"status": "already_running"}
    
    generator.is_running = True
    asyncio.create_task(generator.simulate_gameplay())
    asyncio.create_task(generator.simulate_tournaments())
    
    return {"status": "started"}

@app.post("/api/v1/demo/stop")
async def stop_demo():
    generator.is_running = False
    return {"status": "stopped"}

@app.post("/api/v1/demo/populate")
async def populate_data(users: int = 20, games: int = 5, tournaments: int = 3):
    results = {
        "users": await generator.create_demo_users(users),
        "games": await generator.create_demo_games(games),
        "tournaments": await generator.create_demo_tournaments(tournaments)
    }
    
    return {
        "status": "populated",
        "counts": {
            "users": len(results["users"]),
            "games": len(results["games"]),
            "tournaments": len(results["tournaments"])
        }
    }

@app.get("/api/v1/demo/status")
async def demo_status():
    return {
        "is_running": generator.is_running,
        "users_count": len(generator.users),
        "games_count": len(generator.games),
        "tournaments_count": len(generator.tournaments)
    }

@app.post("/api/v1/demo/burst")
async def burst_activity(duration_seconds: int = 30):
    async def burst_simulation():
        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        while datetime.utcnow() < end_time:
            for _ in range(random.randint(10, 30)):
                if generator.users and generator.games:
                    user = random.choice(generator.users)
                    game = random.choice(generator.games)
                    score = random.randint(100, 5000)
                    
                    try:
                        await generator.client.post(
                            f"{API_GATEWAY}/api/v1/scores",
                            json={
                                "user_id": user["user_id"],
                                "game_id": game["game_id"],
                                "score": score
                            }
                        )
                    except:
                        pass
            
            await asyncio.sleep(1)
    
    asyncio.create_task(burst_simulation())
    return {"status": "burst_started", "duration": duration_seconds}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "demo-generator",
        "simulation_active": generator.is_running
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "23458"))
    uvicorn.run(app, host="0.0.0.0", port=port)