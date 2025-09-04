from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from celery import Celery
import redis
import httpx
import os
import json
import uuid

app = FastAPI(title="Fanout Service", version="1.0.0")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "pyamqp://guest@localhost//")
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8373")

redis_client = redis.from_url(REDIS_URL)
celery_app = Celery("main", broker=RABBITMQ_URL, backend=REDIS_URL)

class FanoutRequest(BaseModel):
    post_id: int
    user_id: int

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int

@celery_app.task
def distribute_post_task(post_id: int, user_id: int, job_id: str):
    try:
        redis_client.hset(f"job:{job_id}", "status", "processing")
        redis_client.hset(f"job:{job_id}", "progress", "0")
        
        response = httpx.get(f"{GRAPH_SERVICE_URL}/api/v1/graph/users/{user_id}/friends")
        if response.status_code != 200:
            redis_client.hset(f"job:{job_id}", "status", "failed")
            return
        
        friend_ids = response.json()
        total_friends = len(friend_ids)
        
        if total_friends == 0:
            redis_client.hset(f"job:{job_id}", "status", "completed")
            redis_client.hset(f"job:{job_id}", "progress", "100")
            return
        
        for i, friend_id in enumerate(friend_ids):
            feed_key = f"feed:{friend_id}"
            
            redis_client.lpush(feed_key, post_id)
            redis_client.ltrim(feed_key, 0, 999)
            
            progress = int((i + 1) / total_friends * 100)
            redis_client.hset(f"job:{job_id}", "progress", str(progress))
        
        redis_client.hset(f"job:{job_id}", "status", "completed")
        redis_client.expire(f"job:{job_id}", 3600)
        
    except Exception as e:
        redis_client.hset(f"job:{job_id}", "status", "failed")
        redis_client.hset(f"job:{job_id}", "error", str(e))

@app.post("/api/v1/fanout/distribute")
async def distribute_post(request: FanoutRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    redis_client.hset(f"job:{job_id}", "status", "queued")
    redis_client.hset(f"job:{job_id}", "post_id", request.post_id)
    redis_client.hset(f"job:{job_id}", "user_id", request.user_id)
    redis_client.expire(f"job:{job_id}", 3600)
    
    distribute_post_task.delay(request.post_id, request.user_id, job_id)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/v1/fanout/status/{job_id}")
def get_job_status(job_id: str):
    job_data = redis_client.hgetall(f"job:{job_id}")
    if not job_data:
        return {"error": "Job not found"}
    
    return {
        "job_id": job_id,
        "status": job_data.get(b"status", b"unknown").decode(),
        "progress": int(job_data.get(b"progress", b"0").decode()),
        "post_id": job_data.get(b"post_id", b"").decode(),
        "user_id": job_data.get(b"user_id", b"").decode()
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8374)