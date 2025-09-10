import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Notification API Gateway", version="1.0.0")

# Add CORS for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NOTIFICATION_SERVER_URL = os.getenv("NOTIFICATION_SERVER_URL", "http://localhost:7842")

class NotificationRequest(BaseModel):
    user_id: int
    type: str  # email, sms, push
    subject: Optional[str] = None
    message: str
    metadata: Optional[dict] = {}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}

@app.post("/api/v1/notifications/send")
async def send_notification(request: NotificationRequest):
    if request.type not in ["email", "sms", "push"]:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    if request.type == "email" and not request.subject:
        raise HTTPException(status_code=400, detail="Subject is required for email notifications")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTIFICATION_SERVER_URL}/notifications/process",
                json=request.model_dump(),
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Notification server unavailable: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7841))
    uvicorn.run(app, host="0.0.0.0", port=port)