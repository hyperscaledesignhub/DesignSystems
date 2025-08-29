from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from elasticsearch import AsyncElasticsearch
from datetime import datetime
import httpx
import os
import sys
import uuid
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import SearchRequest, SearchResponse, EmailResponse
from shared.database import db_pool, init_database
from shared.tracing import setup_tracing, instrument_fastapi, create_span_attributes, get_trace_headers

tracer = setup_tracing("search-service")

app = FastAPI(title="Search Service", version="1.0.0")
instrument_fastapi(app)

security = HTTPBearer()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")

es_client = AsyncElasticsearch([ELASTICSEARCH_URL])

@app.on_event("startup")
async def startup_event():
    await init_database()
    
    try:
        if not await es_client.indices.exists(index="emails"):
            await es_client.indices.create(
                index="emails",
                body={
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "user_id": {"type": "keyword"},
                            "from_email": {"type": "keyword"},
                            "to_recipients": {"type": "keyword"},
                            "subject": {"type": "text", "analyzer": "standard"},
                            "body": {"type": "text", "analyzer": "standard"},
                            "labels": {"type": "keyword"},
                            "folder": {"type": "keyword"},
                            "status": {"type": "keyword"},
                            "priority": {"type": "keyword"},
                            "is_read": {"type": "boolean"},
                            "is_starred": {"type": "boolean"},
                            "spam_score": {"type": "float"},
                            "created_at": {"type": "date"},
                            "sent_at": {"type": "date"}
                        }
                    }
                }
            )
            print("Created Elasticsearch index: emails")
    except Exception as e:
        print(f"Elasticsearch setup error: {e}")
    
    print("Search Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    await es_client.close()
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

async def index_email(email_data: dict):
    """Index an email in Elasticsearch"""
    with tracer.start_as_current_span("index_email", attributes=create_span_attributes(
        email_id=email_data['id']
    )):
        try:
            await es_client.index(
                index="emails",
                id=email_data['id'],
                body=email_data
            )
        except Exception as e:
            print(f"Failed to index email: {e}")

@app.post("/search", response_model=SearchResponse)
async def search_emails(request: SearchRequest, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("search_emails", attributes=create_span_attributes(
        query=request.query,
        user_id=auth_data['user_id'],
        limit=request.limit
    )):
        start_time = datetime.utcnow()
        
        query_body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id": auth_data['user_id']}}
                    ],
                    "should": [],
                    "filter": []
                }
            },
            "size": request.limit,
            "from": request.offset,
            "sort": [{"created_at": {"order": "desc"}}],
            "aggs": {
                "folders": {
                    "terms": {"field": "folder"}
                },
                "labels": {
                    "terms": {"field": "labels"}
                },
                "senders": {
                    "terms": {"field": "from_email", "size": 10}
                }
            }
        }
        
        if request.query:
            query_body["query"]["bool"]["should"] = [
                {"match": {"subject": {"query": request.query, "boost": 2}}},
                {"match": {"body": request.query}},
                {"match": {"from_email": request.query}}
            ]
            query_body["query"]["bool"]["minimum_should_match"] = 1
        
        if request.filters:
            for key, value in request.filters.items():
                if key == "folder":
                    query_body["query"]["bool"]["filter"].append({"term": {"folder": value}})
                elif key == "label":
                    query_body["query"]["bool"]["filter"].append({"term": {"labels": value}})
                elif key == "is_read":
                    query_body["query"]["bool"]["filter"].append({"term": {"is_read": value}})
                elif key == "is_starred":
                    query_body["query"]["bool"]["filter"].append({"term": {"is_starred": value}})
                elif key == "from_email":
                    query_body["query"]["bool"]["filter"].append({"term": {"from_email": value}})
        
        if request.from_date:
            query_body["query"]["bool"]["filter"].append({
                "range": {"created_at": {"gte": request.from_date.isoformat()}}
            })
        
        if request.to_date:
            query_body["query"]["bool"]["filter"].append({
                "range": {"created_at": {"lte": request.to_date.isoformat()}}
            })
        
        try:
            result = await es_client.search(index="emails", body=query_body)
            
            emails = []
            for hit in result['hits']['hits']:
                source = hit['_source']
                emails.append(EmailResponse(
                    id=source['id'],
                    from_email=source['from_email'],
                    to_recipients=source.get('to_recipients', []),
                    cc_recipients=source.get('cc_recipients', []),
                    bcc_recipients=source.get('bcc_recipients', []),
                    subject=source['subject'],
                    body=source['body'],
                    html_body=source.get('html_body'),
                    status=source['status'],
                    priority=source['priority'],
                    is_read=source['is_read'],
                    is_starred=source['is_starred'],
                    spam_score=source.get('spam_score', 0.0),
                    labels=source.get('labels', []),
                    attachments=[],
                    created_at=datetime.fromisoformat(source['created_at']),
                    sent_at=datetime.fromisoformat(source['sent_at']) if source.get('sent_at') else None,
                    thread_id=source.get('thread_id'),
                    folder=source['folder']
                ))
            
            facets = {
                "folders": {},
                "labels": {},
                "senders": {}
            }
            
            if 'aggregations' in result:
                if 'folders' in result['aggregations']:
                    facets['folders'] = {
                        bucket['key']: bucket['doc_count']
                        for bucket in result['aggregations']['folders']['buckets']
                    }
                if 'labels' in result['aggregations']:
                    facets['labels'] = {
                        bucket['key']: bucket['doc_count']
                        for bucket in result['aggregations']['labels']['buckets']
                    }
                if 'senders' in result['aggregations']:
                    facets['senders'] = {
                        bucket['key']: bucket['doc_count']
                        for bucket in result['aggregations']['senders']['buckets']
                    }
            
            took_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return SearchResponse(
                total=result['hits']['total']['value'],
                results=emails,
                facets=facets,
                took_ms=took_ms
            )
        except Exception as e:
            print(f"Search error: {e}")
            
            emails = await db_pool.fetch(
                """
                SELECT * FROM emails 
                WHERE user_id = $1 
                AND (subject ILIKE $2 OR body ILIKE $2)
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """,
                uuid.UUID(auth_data['user_id']),
                f"%{request.query}%" if request.query else "%",
                request.limit,
                request.offset
            )
            
            results = []
            for email in emails:
                results.append(EmailResponse(
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
                    attachments=[],
                    created_at=email['created_at'],
                    sent_at=email['sent_at'],
                    thread_id=str(email['thread_id']) if email['thread_id'] else None,
                    folder=email['folder']
                ))
            
            took_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return SearchResponse(
                total=len(results),
                results=results,
                facets={},
                took_ms=took_ms
            )

@app.post("/search/index/{email_id}")
async def index_email_endpoint(email_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("index_email_endpoint", attributes=create_span_attributes(
        email_id=email_id,
        user_id=auth_data['user_id']
    )):
        email = await db_pool.fetchrow(
            "SELECT * FROM emails WHERE id = $1 AND user_id = $2",
            uuid.UUID(email_id),
            uuid.UUID(auth_data['user_id'])
        )
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email_data = {
            "id": str(email['id']),
            "user_id": str(email['user_id']),
            "from_email": email['from_email'],
            "to_recipients": email['to_recipients'],
            "subject": email['subject'],
            "body": email['body'],
            "labels": email['labels'],
            "folder": email['folder'],
            "status": email['status'],
            "priority": email['priority'],
            "is_read": email['is_read'],
            "is_starred": email['is_starred'],
            "spam_score": email['spam_score'],
            "created_at": email['created_at'].isoformat(),
            "sent_at": email['sent_at'].isoformat() if email['sent_at'] else None
        }
        
        await index_email(email_data)
        
        return {"message": "Email indexed successfully"}

@app.delete("/search/index/{email_id}")
async def delete_from_index(email_id: str, auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("delete_from_index", attributes=create_span_attributes(
        email_id=email_id,
        user_id=auth_data['user_id']
    )):
        try:
            await es_client.delete(index="emails", id=email_id)
            return {"message": "Email removed from search index"}
        except Exception as e:
            return {"message": f"Failed to remove from index: {str(e)}"}

@app.post("/search/reindex")
async def reindex_all(auth_data = Depends(verify_auth)):
    with tracer.start_as_current_span("reindex_all", attributes=create_span_attributes(
        user_id=auth_data['user_id']
    )):
        emails = await db_pool.fetch(
            "SELECT * FROM emails WHERE user_id = $1",
            uuid.UUID(auth_data['user_id'])
        )
        
        indexed = 0
        for email in emails:
            email_data = {
                "id": str(email['id']),
                "user_id": str(email['user_id']),
                "from_email": email['from_email'],
                "to_recipients": email['to_recipients'],
                "subject": email['subject'],
                "body": email['body'],
                "labels": email['labels'],
                "folder": email['folder'],
                "status": email['status'],
                "priority": email['priority'],
                "is_read": email['is_read'],
                "is_starred": email['is_starred'],
                "spam_score": email['spam_score'],
                "created_at": email['created_at'].isoformat(),
                "sent_at": email['sent_at'].isoformat() if email['sent_at'] else None
            }
            
            await index_email(email_data)
            indexed += 1
        
        return {"message": f"Reindexed {indexed} emails"}

@app.get("/health")
async def health_check():
    es_health = "unknown"
    try:
        health = await es_client.cluster.health()
        es_health = health['status']
    except:
        pass
    
    return {
        "status": "healthy",
        "service": "search-service",
        "timestamp": datetime.utcnow(),
        "elasticsearch": es_health
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8006))
    uvicorn.run(app, host="0.0.0.0", port=port)