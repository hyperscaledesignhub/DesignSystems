from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import sys
from typing import Optional
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

tracer = setup_tracing("api-gateway")

app = FastAPI(title="Email System API Gateway", version="1.0.0")
instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

SERVICE_URLS = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001"),
    "email": os.getenv("EMAIL_SERVICE_URL", "http://email-service:8002"),
    "spam": os.getenv("SPAM_SERVICE_URL", "http://spam-service:8003"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004"),
    "attachment": os.getenv("ATTACHMENT_SERVICE_URL", "http://attachment-service:8005"),
    "search": os.getenv("SEARCH_SERVICE_URL", "http://search-service:8006"),
}

async def get_auth_header(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials:
        return {"Authorization": f"Bearer {credentials.credentials}"}
    return {}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def gateway(request: Request, path: str, auth_header = Depends(get_auth_header)):
    with tracer.start_as_current_span("api_gateway_request", attributes=create_span_attributes(
        method=request.method,
        path=path,
        client_host=request.client.host if request.client else "unknown"
    )):
        service_name, service_path = parse_path(path)
        
        if service_name not in SERVICE_URLS:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
        service_url = SERVICE_URLS[service_name]
        
        headers = dict(request.headers)
        headers.update(auth_header)
        headers.update(get_trace_headers())
        
        headers.pop("host", None)
        headers.pop("content-length", None)
        
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=request.method,
                    url=f"{service_url}/{service_path}",
                    headers=headers,
                    content=body,
                    params=dict(request.query_params)
                )
                
                return_headers = dict(response.headers)
                return_headers.pop("content-encoding", None)
                return_headers.pop("content-length", None)
                return_headers.pop("transfer-encoding", None)
                
                content = response.content
                
                try:
                    json_content = response.json()
                    return json_content
                except:
                    return content
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"Service '{service_name}' unavailable")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

def parse_path(path: str) -> tuple[str, str]:
    """Parse the path to extract service name and remaining path"""
    parts = path.split("/", 1)
    
    if not parts[0]:
        if len(parts) > 1:
            parts = parts[1].split("/", 1)
    
    if not parts or not parts[0]:
        return "auth", "health"
    
    service_name = parts[0]
    remaining_path = parts[1] if len(parts) > 1 else ""
    
    service_mapping = {
        "auth": "auth",
        "login": "auth",
        "register": "auth",
        "validate": "auth",
        "emails": "email",
        "email": "email",
        "spam": "spam",
        "notifications": "notification",
        "notification": "notification",
        "attachments": "attachment",
        "attachment": "attachment",
        "search": "search",
    }
    
    mapped_service = service_mapping.get(service_name, service_name)
    
    if service_name in ["login", "register", "validate"]:
        remaining_path = f"auth/{service_name}"
    elif service_name == "search":
        remaining_path = f"search/{remaining_path}" if remaining_path else "search"
    elif service_name == "emails":
        remaining_path = "emails"
    elif service_name == "notifications":
        remaining_path = f"notifications/{remaining_path}" if remaining_path else "notifications"
    elif mapped_service != service_name and remaining_path:
        remaining_path = f"{service_name}/{remaining_path}"
    elif mapped_service != service_name:
        remaining_path = service_name
    
    return mapped_service, remaining_path

@app.get("/health")
async def health_check():
    with tracer.start_as_current_span("health_check"):
        health_status = {"gateway": "healthy", "services": {}}
        
        for service_name, service_url in SERVICE_URLS.items():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        f"{service_url}/health",
                        headers=get_trace_headers()
                    )
                    if response.status_code == 200:
                        health_status["services"][service_name] = "healthy"
                    else:
                        health_status["services"][service_name] = "unhealthy"
            except:
                health_status["services"][service_name] = "unreachable"
        
        all_healthy = all(status == "healthy" for status in health_status["services"].values())
        
        if not all_healthy:
            health_status["gateway"] = "degraded"
        
        return health_status

@app.get("/services")
async def list_services():
    with tracer.start_as_current_span("list_services"):
        return {
            "services": [
                {
                    "name": name,
                    "url": url,
                    "endpoints": get_service_endpoints(name)
                }
                for name, url in SERVICE_URLS.items()
            ]
        }

def get_service_endpoints(service_name: str) -> list:
    """Get common endpoints for each service"""
    endpoints = {
        "auth": [
            "POST /auth/register",
            "POST /auth/login",
            "GET /auth/validate",
            "POST /auth/refresh",
            "GET /auth/users/{user_id}"
        ],
        "email": [
            "POST /emails",
            "GET /emails",
            "GET /emails/{email_id}",
            "PATCH /emails/{email_id}",
            "DELETE /emails/{email_id}"
        ],
        "spam": [
            "POST /spam/check",
            "POST /spam/report",
            "GET /spam/stats"
        ],
        "notification": [
            "POST /notifications",
            "GET /notifications/{user_id}",
            "PATCH /notifications/{notification_id}/read",
            "DELETE /notifications/{notification_id}",
            "WS /ws/{user_id}"
        ],
        "attachment": [
            "POST /attachments/upload",
            "GET /attachments/{attachment_id}/download",
            "DELETE /attachments/{attachment_id}",
            "GET /attachments/email/{email_id}"
        ],
        "search": [
            "POST /search",
            "POST /search/index/{email_id}",
            "DELETE /search/index/{email_id}",
            "POST /search/reindex"
        ]
    }
    
    return endpoints.get(service_name, [])

@app.get("/")
async def root():
    return {
        "service": "Email System API Gateway",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "services": "/services"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)