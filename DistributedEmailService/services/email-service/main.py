from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
import httpx
import os
import sys
import uuid
from typing import List, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import EmailCreate, EmailUpdate, EmailResponse, EmailStatus
from shared.database import db_pool, init_database
from shared.tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

tracer = setup_tracing("email-service")

app = FastAPI(title="Email Service", version="1.0.0")
instrument_fastapi(app)

security = HTTPBearer()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
SPAM_SERVICE_URL = os.getenv("SPAM_SERVICE_URL", "http://spam-service:8003")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")
SEARCH_SERVICE_URL = os.getenv("SEARCH_SERVICE_URL", "http://search-service:8006")

@app.on_event("startup")
async def startup_event():
    await init_database()
    print("Email Service started successfully")

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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return response.json()

async def check_spam(email_data: dict) -> float:
    with tracer.start_as_current_span("check_spam"):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SPAM_SERVICE_URL}/spam/check",
                    json={
                        "subject": email_data["subject"],
                        "body": email_data["body"],
                        "from_email": email_data["from_email"],
                        "to_emails": email_data["to_recipients"]
                    },
                    headers=get_trace_headers()
                )
                if response.status_code == 200:
                    result = response.json()
                    return result["spam_score"]
        except Exception as e:
            print(f"Spam check failed: {e}")
        return 0.0

async def send_notification(user_id: str, notification_type: str, title: str, message: str, email_id: str):
    with tracer.start_as_current_span("send_notification"):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{NOTIFICATION_SERVICE_URL}/notifications",
                    json={
                        "user_id": user_id,
                        "type": notification_type,
                        "title": title,
                        "message": message,
                        "data": {"email_id": email_id}
                    },
                    headers=get_trace_headers()
                )
        except Exception as e:
            print(f"Notification failed: {e}")

async def index_email_to_search(email_id: str, token: str):
    """Index email to search service for searchability"""
    with tracer.start_as_current_span("index_email_to_search"):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SEARCH_SERVICE_URL}/search/index/{email_id}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        **get_trace_headers()
                    }
                )
                if response.status_code == 200:
                    print(f"Email {email_id} indexed to search successfully")
                else:
                    print(f"Failed to index email {email_id}: {response.status_code}")
        except Exception as e:
            print(f"Failed to index email to search: {e}")

@app.post("/emails", response_model=EmailResponse)
async def create_email(
    email: EmailCreate,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_data = Depends(verify_auth)
):
    with tracer.start_as_current_span("create_email", attributes=create_span_attributes(
        user_id=auth_data['user_id'],
        subject=email.subject,
        recipients_count=len(email.to_recipients)
    )):
        spam_score = await check_spam({
            "subject": email.subject,
            "body": email.body,
            "from_email": auth_data['email'],
            "to_recipients": email.to_recipients
        })
        
        status = EmailStatus.DRAFT if email.is_draft else EmailStatus.SENT
        if spam_score > 0.7:
            status = EmailStatus.SPAM
        
        result = await db_pool.fetchrow(
            """
            INSERT INTO emails (
                user_id, from_email, to_recipients, cc_recipients, bcc_recipients,
                subject, body, html_body, status, priority, spam_score, labels,
                sent_at, scheduled_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING *
            """,
            uuid.UUID(auth_data['user_id']),
            auth_data['email'],
            email.to_recipients,
            email.cc_recipients or [],
            email.bcc_recipients or [],
            email.subject,
            email.body,
            email.html_body,
            status,
            email.priority,
            spam_score,
            email.labels or [],
            datetime.utcnow() if not email.is_draft else None,
            email.scheduled_at
        )
        
        if not email.is_draft:
            background_tasks.add_task(
                send_notification,
                auth_data['user_id'],
                "email_sent",
                "Email Sent",
                f"Your email '{email.subject}' has been sent successfully",
                str(result['id'])
            )
            
            # Index email in search service
            background_tasks.add_task(
                index_email_to_search,
                str(result['id']),
                credentials.credentials
            )
        
        return EmailResponse(
            id=str(result['id']),
            from_email=result['from_email'],
            to_recipients=result['to_recipients'],
            cc_recipients=result['cc_recipients'],
            bcc_recipients=result['bcc_recipients'],
            subject=result['subject'],
            body=result['body'],
            html_body=result['html_body'],
            status=result['status'],
            priority=result['priority'],
            is_read=result['is_read'],
            is_starred=result['is_starred'],
            spam_score=result['spam_score'],
            labels=result['labels'],
            attachments=[],
            created_at=result['created_at'],
            sent_at=result['sent_at'],
            thread_id=str(result['thread_id']) if result['thread_id'] else None,
            folder=result['folder']
        )

@app.get("/emails", response_model=List[EmailResponse])
async def list_emails(
    folder: str = "inbox",
    limit: int = 50,
    offset: int = 0,
    auth_data = Depends(verify_auth)
):
    with tracer.start_as_current_span("list_emails", attributes=create_span_attributes(
        user_id=auth_data['user_id'],
        folder=folder,
        limit=limit
    )):
        emails = await db_pool.fetch(
            """
            SELECT e.*, 
                   COALESCE(array_agg(
                       json_build_object(
                           'id', a.id,
                           'filename', a.filename,
                           'size', a.size,
                           'content_type', a.content_type
                       ) 
                   ) FILTER (WHERE a.id IS NOT NULL), '{}') as attachments
            FROM emails e
            LEFT JOIN attachments a ON e.id = a.email_id
            WHERE e.user_id = $1 AND e.folder = $2 AND e.status != 'deleted'
            GROUP BY e.id
            ORDER BY e.created_at DESC
            LIMIT $3 OFFSET $4
            """,
            uuid.UUID(auth_data['user_id']),
            folder,
            limit,
            offset
        )
        
        return [
            EmailResponse(
                id=str(email['id']),
                from_email=email['from_email'],
                to_recipients=email['to_recipients'],
                cc_recipients=email['cc_recipients'],
                bcc_recipients=email['bcc_recipients'],
                subject=email['subject'],
                body=email['body'],
                html_body=email['html_body'],
                status=email['status'],
                priority=email['priority'],
                is_read=email['is_read'],
                is_starred=email['is_starred'],
                spam_score=email['spam_score'],
                labels=email['labels'],
                attachments=email['attachments'],
                created_at=email['created_at'],
                sent_at=email['sent_at'],
                thread_id=str(email['thread_id']) if email['thread_id'] else None,
                folder=email['folder']
            )
            for email in emails
        ]

@app.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(email_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("get_email", attributes=create_span_attributes(
        email_id=email_id,
        user_id=auth_data['user_id']
    )):
        email = await db_pool.fetchrow(
            """
            SELECT e.*, 
                   COALESCE(array_agg(
                       json_build_object(
                           'id', a.id,
                           'filename', a.filename,
                           'size', a.size,
                           'content_type', a.content_type
                       ) 
                   ) FILTER (WHERE a.id IS NOT NULL), '{}') as attachments
            FROM emails e
            LEFT JOIN attachments a ON e.id = a.email_id
            WHERE e.id = $1 AND e.user_id = $2
            GROUP BY e.id
            """,
            uuid.UUID(email_id),
            uuid.UUID(auth_data['user_id'])
        )
        
        if not email:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        
        await db_pool.execute(
            "UPDATE emails SET is_read = true WHERE id = $1",
            uuid.UUID(email_id)
        )
        
        return EmailResponse(
            id=str(email['id']),
            from_email=email['from_email'],
            to_recipients=email['to_recipients'],
            cc_recipients=email['cc_recipients'],
            bcc_recipients=email['bcc_recipients'],
            subject=email['subject'],
            body=email['body'],
            html_body=email['html_body'],
            status=email['status'],
            priority=email['priority'],
            is_read=True,
            is_starred=email['is_starred'],
            spam_score=email['spam_score'],
            labels=email['labels'],
            attachments=email['attachments'],
            created_at=email['created_at'],
            sent_at=email['sent_at'],
            thread_id=str(email['thread_id']) if email['thread_id'] else None,
            folder=email['folder']
        )

@app.patch("/emails/{email_id}", response_model=EmailResponse)
async def update_email(
    email_id: str,
    update: EmailUpdate,
    auth_data = Depends(verify_auth)
):
    with tracer.start_as_current_span("update_email", attributes=create_span_attributes(
        email_id=email_id,
        user_id=auth_data['user_id']
    )):
        updates = []
        values = [uuid.UUID(email_id), uuid.UUID(auth_data['user_id'])]
        
        if update.is_starred is not None:
            updates.append(f"is_starred = ${len(values) + 1}")
            values.append(update.is_starred)
        
        if update.labels is not None:
            updates.append(f"labels = ${len(values) + 1}")
            values.append(update.labels)
        
        if update.status is not None:
            updates.append(f"status = ${len(values) + 1}")
            values.append(update.status)
            updates.append(f"folder = ${len(values) + 1}")
            folder = "trash" if update.status == EmailStatus.DELETED else "inbox"
            values.append(folder)
        
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updates provided")
        
        query = f"""
            UPDATE emails 
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND user_id = $2
            RETURNING *
        """
        
        result = await db_pool.fetchrow(query, *values)
        
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        
        attachments = await db_pool.fetch(
            "SELECT id, filename, size, content_type FROM attachments WHERE email_id = $1",
            uuid.UUID(email_id)
        )
        
        return EmailResponse(
            id=str(result['id']),
            from_email=result['from_email'],
            to_recipients=result['to_recipients'],
            cc_recipients=result['cc_recipients'],
            bcc_recipients=result['bcc_recipients'],
            subject=result['subject'],
            body=result['body'],
            html_body=result['html_body'],
            status=result['status'],
            priority=result['priority'],
            is_read=result['is_read'],
            is_starred=result['is_starred'],
            spam_score=result['spam_score'],
            labels=result['labels'],
            attachments=[{
                "id": str(a['id']),
                "filename": a['filename'],
                "size": a['size'],
                "content_type": a['content_type']
            } for a in attachments],
            created_at=result['created_at'],
            sent_at=result['sent_at'],
            thread_id=str(result['thread_id']) if result['thread_id'] else None,
            folder=result['folder']
        )

@app.delete("/emails/{email_id}")
async def delete_email(email_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("delete_email", attributes=create_span_attributes(
        email_id=email_id,
        user_id=auth_data['user_id']
    )):
        result = await db_pool.execute(
            "UPDATE emails SET status = 'deleted', folder = 'trash' WHERE id = $1 AND user_id = $2",
            uuid.UUID(email_id),
            uuid.UUID(auth_data['user_id'])
        )
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        
        return {"message": "Email moved to trash"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "email-service", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)