from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
import httpx
import redis
import time
import logging
import os

app = FastAPI(title="API Gateway")
redis_client = redis.Redis(host='redis-master', port=6739, decode_responses=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use environment variables for service URLs
SERVICES = {
    "location": os.getenv("LOCATION_SERVICE_URL", "http://location-service:8921"),
    "business": os.getenv("BUSINESS_SERVICE_URL", "http://business-service-standalone:9823")
}

RATE_LIMIT = 1000
RATE_WINDOW = 60

async def check_rate_limit(client_ip: str) -> bool:
    key = f"rate_limit:{client_ip}"
    try:
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, RATE_WINDOW)
        return current <= RATE_LIMIT
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    
    if not await check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
    
    response = await call_next(request)
    return response

@app.get("/api/v1/search/nearby")
async def search_nearby(latitude: float, longitude: float, radius: int = 5000):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SERVICES['location']}/nearby",
                params={"latitude": latitude, "longitude": longitude, "radius": radius},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception as e:
        logger.error(f"Error in search_nearby: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/businesses/{business_id}")
async def get_business(business_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SERVICES['business']}/businesses/{business_id}",
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Business not found")
        raise HTTPException(status_code=500, detail="Internal server error")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception as e:
        logger.error(f"Error in get_business: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/businesses")
async def create_business(business: Dict[str, Any]):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SERVICES['business']}/businesses",
                json=business,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception as e:
        logger.error(f"Error in create_business: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/v1/businesses/{business_id}")
async def update_business(business_id: str, business: Dict[str, Any]):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{SERVICES['business']}/businesses/{business_id}",
                json=business,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Business not found")
        raise HTTPException(status_code=500, detail="Internal server error")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception as e:
        logger.error(f"Error in update_business: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/v1/businesses/{business_id}")
async def delete_business(business_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{SERVICES['business']}/businesses/{business_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Business not found")
        raise HTTPException(status_code=500, detail="Internal server error")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception as e:
        logger.error(f"Error in delete_business: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    health_status = {"status": "healthy", "services": {}}
    
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/health", timeout=2.0)
                health_status["services"][service_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            health_status["services"][service_name] = "unhealthy"
            health_status["status"] = "degraded"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7891)