from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
import httpx
import os
import sys
import uuid
import minio
from datetime import datetime, timedelta
import io

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import AttachmentCreate, AttachmentResponse
from shared.database import db_pool, init_database
from shared.tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

tracer = setup_tracing("attachment-service")

app = FastAPI(title="Attachment Service", version="1.0.0")
instrument_fastapi(app)

security = HTTPBearer()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioaccess")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "miniosecret")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "email-attachments")

minio_client = minio.Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

@app.on_event("startup")
async def startup_event():
    await init_database()
    
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            print(f"Created MinIO bucket: {MINIO_BUCKET}")
    except Exception as e:
        print(f"MinIO bucket setup error: {e}")
    
    print("Attachment Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    await db_pool.disconnect()

async def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/auth/validate",
            headers={"Authorization": f"Bearer {credentials.credentials}", **get_trace_headers()}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()

@app.post("/attachments/upload", response_model=AttachmentResponse)
async def upload_attachment(
    file: UploadFile = File(...),
    email_id: str = None,
    auth_data = Depends(verify_auth)
):
    with tracer.start_as_current_span("upload_attachment", attributes=create_span_attributes(
        filename=file.filename,
        content_type=file.content_type,
        size=file.size,
        user_id=auth_data['user_id']
    )):
        if file.size > 25 * 1024 * 1024:  # 25MB limit
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 25MB")
        
        allowed_types = [
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "application/pdf", "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain", "text/csv", "application/zip"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")
        
        file_id = str(uuid.uuid4())
        s3_key = f"{auth_data['user_id']}/{file_id}/{file.filename}"
        
        contents = await file.read()
        
        try:
            minio_client.put_object(
                MINIO_BUCKET,
                s3_key,
                io.BytesIO(contents),
                len(contents),
                content_type=file.content_type
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
        
        attachment = await db_pool.fetchrow(
            """
            INSERT INTO attachments (email_id, filename, content_type, size, s3_key)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            uuid.UUID(email_id) if email_id else None,
            file.filename,
            file.content_type,
            len(contents),
            s3_key
        )
        
        await db_pool.execute(
            "UPDATE users SET storage_used = storage_used + $1 WHERE id = $2",
            len(contents),
            uuid.UUID(auth_data['user_id'])
        )
        
        return AttachmentResponse(
            id=str(attachment['id']),
            filename=attachment['filename'],
            content_type=attachment['content_type'],
            size=attachment['size'],
            url=f"/attachments/{attachment['id']}/download",
            uploaded_at=attachment['uploaded_at'],
            email_id=str(attachment['email_id']) if attachment['email_id'] else None
        )

@app.get("/attachments/{attachment_id}/download")
async def download_attachment(attachment_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("download_attachment", attributes=create_span_attributes(
        attachment_id=attachment_id,
        user_id=auth_data['user_id']
    )):
        attachment = await db_pool.fetchrow(
            """
            SELECT a.*, e.user_id 
            FROM attachments a
            LEFT JOIN emails e ON a.email_id = e.id
            WHERE a.id = $1
            """,
            uuid.UUID(attachment_id)
        )
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        if attachment['user_id'] and str(attachment['user_id']) != auth_data['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        try:
            response = minio_client.get_object(MINIO_BUCKET, attachment['s3_key'])
            content = response.read()
            response.close()
            response.release_conn()
            
            return StreamingResponse(
                io.BytesIO(content),
                media_type=attachment['content_type'],
                headers={
                    "Content-Disposition": f"attachment; filename={attachment['filename']}"
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@app.delete("/attachments/{attachment_id}")
async def delete_attachment(attachment_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("delete_attachment", attributes=create_span_attributes(
        attachment_id=attachment_id,
        user_id=auth_data['user_id']
    )):
        attachment = await db_pool.fetchrow(
            """
            SELECT a.*, e.user_id 
            FROM attachments a
            LEFT JOIN emails e ON a.email_id = e.id
            WHERE a.id = $1
            """,
            uuid.UUID(attachment_id)
        )
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        if attachment['user_id'] and str(attachment['user_id']) != auth_data['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        try:
            minio_client.remove_object(MINIO_BUCKET, attachment['s3_key'])
        except Exception as e:
            print(f"Failed to delete from MinIO: {e}")
        
        await db_pool.execute(
            "DELETE FROM attachments WHERE id = $1",
            uuid.UUID(attachment_id)
        )
        
        await db_pool.execute(
            "UPDATE users SET storage_used = storage_used - $1 WHERE id = $2",
            attachment['size'],
            attachment['user_id']
        )
        
        return {"message": "Attachment deleted successfully"}

@app.get("/attachments/email/{email_id}", response_model=list[AttachmentResponse])
async def get_email_attachments(email_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("get_email_attachments", attributes=create_span_attributes(
        email_id=email_id,
        user_id=auth_data['user_id']
    )):
        attachments = await db_pool.fetch(
            """
            SELECT a.* FROM attachments a
            JOIN emails e ON a.email_id = e.id
            WHERE a.email_id = $1 AND e.user_id = $2
            """,
            uuid.UUID(email_id),
            uuid.UUID(auth_data['user_id'])
        )
        
        return [
            AttachmentResponse(
                id=str(a['id']),
                filename=a['filename'],
                content_type=a['content_type'],
                size=a['size'],
                url=f"/attachments/{a['id']}/download",
                uploaded_at=a['uploaded_at'],
                email_id=str(a['email_id'])
            )
            for a in attachments
        ]

@app.get("/attachments/presigned-url/{attachment_id}")
async def get_presigned_url(attachment_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("get_presigned_url", attributes=create_span_attributes(
        attachment_id=attachment_id,
        user_id=auth_data['user_id']
    )):
        attachment = await db_pool.fetchrow(
            """
            SELECT a.*, e.user_id 
            FROM attachments a
            LEFT JOIN emails e ON a.email_id = e.id
            WHERE a.id = $1
            """,
            uuid.UUID(attachment_id)
        )
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        if attachment['user_id'] and str(attachment['user_id']) != auth_data['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        try:
            url = minio_client.presigned_get_object(
                MINIO_BUCKET,
                attachment['s3_key'],
                expires=timedelta(hours=1)
            )
            return {"url": url, "expires_in": 3600}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate URL: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "attachment-service", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8005))
    uvicorn.run(app, host="0.0.0.0", port=port)