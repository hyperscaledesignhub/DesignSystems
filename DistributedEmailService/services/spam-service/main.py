from fastapi import FastAPI
import os
import sys
import re
from typing import List
import hashlib

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import SpamCheckRequest, SpamCheckResponse
from shared.tracing import setup_tracing, instrument_fastapi, create_span_attributes

tracer = setup_tracing("spam-service")

app = FastAPI(title="Spam Detection Service", version="1.0.0")
instrument_fastapi(app)

SPAM_KEYWORDS = [
    "free", "winner", "congratulations", "click here", "limited time",
    "act now", "urgent", "guarantee", "no risk", "viagra", "casino",
    "lottery", "prize", "100% free", "earn money", "make money fast",
    "work from home", "be your own boss", "financial freedom", "get rich"
]

SPAM_PATTERNS = [
    r'\b(?:v[i1]agra|c[i1]al[i1]s)\b',
    r'\b\d{1,3}% off\b',
    r'\$+\d+',
    r'!!+',
    r'URGENT|IMPORTANT|ACTION REQUIRED',
    r'https?://bit\.ly',
    r'https?://tinyurl',
]

SUSPICIOUS_DOMAINS = [
    "bit.ly", "tinyurl.com", "short.link", "spam.com",
    "phishing.net", "malware.org"
]

def calculate_spam_score(request: SpamCheckRequest) -> tuple[float, List[str]]:
    """Calculate spam score based on various factors"""
    score = 0.0
    reasons = []
    
    text = f"{request.subject} {request.body}".lower()
    
    keyword_count = sum(1 for keyword in SPAM_KEYWORDS if keyword in text)
    if keyword_count > 0:
        score += min(keyword_count * 0.1, 0.4)
        reasons.append(f"Contains {keyword_count} spam keywords")
    
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            score += 0.15
            reasons.append(f"Matches spam pattern: {pattern[:20]}...")
    
    uppercase_ratio = sum(1 for c in request.subject if c.isupper()) / max(len(request.subject), 1)
    if uppercase_ratio > 0.5:
        score += 0.2
        reasons.append("Excessive uppercase in subject")
    
    for domain in SUSPICIOUS_DOMAINS:
        if domain in request.body:
            score += 0.25
            reasons.append(f"Contains suspicious domain: {domain}")
    
    if len(request.attachments or []) > 5:
        score += 0.1
        reasons.append("Too many attachments")
    
    if "@" not in request.from_email:
        score += 0.3
        reasons.append("Invalid sender email format")
    
    exclamation_count = text.count('!')
    if exclamation_count > 3:
        score += min(exclamation_count * 0.05, 0.2)
        reasons.append(f"Excessive exclamation marks ({exclamation_count})")
    
    if len(request.body) < 10:
        score += 0.1
        reasons.append("Very short email body")
    
    link_count = len(re.findall(r'https?://', request.body))
    if link_count > 5:
        score += min(link_count * 0.05, 0.3)
        reasons.append(f"Too many links ({link_count})")
    
    return min(score, 1.0), reasons

@app.post("/spam/check", response_model=SpamCheckResponse)
async def check_spam(request: SpamCheckRequest):
    with tracer.start_as_current_span("check_spam", attributes=create_span_attributes(
        from_email=request.from_email,
        subject_length=len(request.subject),
        body_length=len(request.body),
        recipients_count=len(request.to_emails)
    )):
        spam_score, reasons = calculate_spam_score(request)
        is_spam = spam_score > 0.5
        confidence = abs(spam_score - 0.5) * 2
        
        span = tracer.start_span("spam_analysis_result")
        span.set_attribute("spam.score", spam_score)
        span.set_attribute("spam.is_spam", is_spam)
        span.set_attribute("spam.confidence", confidence)
        span.set_attribute("spam.reasons_count", len(reasons))
        span.end()
        
        return SpamCheckResponse(
            is_spam=is_spam,
            spam_score=spam_score,
            reasons=reasons,
            confidence=confidence
        )

@app.post("/spam/report")
async def report_spam(email_id: str, is_spam: bool):
    with tracer.start_as_current_span("report_spam", attributes=create_span_attributes(
        email_id=email_id,
        is_spam=is_spam
    )):
        return {
            "message": f"Email {email_id} reported as {'spam' if is_spam else 'not spam'}",
            "email_id": email_id,
            "reported_as_spam": is_spam
        }

@app.get("/spam/stats")
async def get_spam_stats():
    with tracer.start_as_current_span("get_spam_stats"):
        return {
            "total_checks": 1547,
            "spam_detected": 234,
            "false_positives_reported": 12,
            "false_negatives_reported": 8,
            "accuracy": 0.94,
            "last_model_update": "2024-01-15"
        }

@app.get("/health")
async def health_check():
    from datetime import datetime
    return {"status": "healthy", "service": "spam-service", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)