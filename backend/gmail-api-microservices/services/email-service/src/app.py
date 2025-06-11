# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/app.py

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from .database.db import get_db
from .models.email import Email
from .handlers.crud import EmailManager
from .handlers.search import EmailSearchManager
from pydantic import BaseModel, Field
from datetime import datetime
import httpx
import os
import logging  # Add this import

# Add logger
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Email Service",
    description="Email management service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Initialize managers
email_manager = EmailManager()
search_manager = EmailSearchManager()

# Pydantic models
class CategoryUpdate(BaseModel):
    category: Optional[str] = None

class UrgencyUpdate(BaseModel):
    urgency: int = Field(ge=0, le=10, description="Urgency level from 0 to 10")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "email"}

@app.get("/emails")
async def get_emails(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    category: str = Query(None),
    x_user_id: str = Header(None)
):
    """Get emails with enhanced filtering"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    emails = email_manager.get_user_emails(x_user_id, limit, offset, category)
    
    email_list = []
    for email in emails:
        email_list.append({
            'id': email['id'],
            'thread_id': email.get('thread_id'),
            'subject': email['subject'],
            'sender': email['sender'],
            'recipient': email['recipient'],
            'date': email['date'],
            'snippet': email['snippet'],
            'is_read': email['is_read'],
            'is_starred': email['is_starred'],
            'is_important': email.get('is_important', False),
            'category': email.get('category'),
            'urgency': email.get('urgency', 0),
            'has_tls': email.get('has_tls', False),
            'stored_at': email['stored_at']
        })
    
    return {
        "emails": email_list,
        "count": len(email_list),
        "offset": offset,
        "limit": limit
    }

@app.get("/email/{email_id}")
async def get_email(email_id: str, x_user_id: str = Header(None)):
    """Get specific email content from database"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    email_dict = email_manager.get_email_by_gmail_id(x_user_id, email_id)
    
    if not email_dict:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Mark as read
    with get_db() as db:
        db_email = db.query(Email).filter(
            Email.user_id == x_user_id,
            Email.gmail_message_id == email_id
        ).first()
        if db_email:
            db_email.is_read = True
    
    return email_dict

@app.get("/emails/search")
async def search_emails(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, le=50),
    x_user_id: str = Header(None)
):
    """Search emails by subject or sender"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    emails = search_manager.search_emails(x_user_id, q, limit)
    
    email_list = []
    for email in emails:
        email_list.append({
            'id': email.gmail_message_id,
            'subject': email.subject,
            'sender': email.sender,
            'recipient': email.recipient,
            'date': email.date_sent.isoformat() if email.date_sent else None,
            'snippet': email.snippet,
            'is_read': email.is_read
        })
    
    return {
        "emails": email_list,
        "query": q,
        "count": len(email_list)
    }

@app.get("/emails/search/advanced")
async def advanced_search_emails(
    q: str = Query(None, description="Search query"),
    category: str = Query(None, description="Email category"),
    urgency_min: int = Query(None, description="Minimum urgency level (0-10)"),
    is_important: bool = Query(None, description="Filter by importance"),
    limit: int = Query(default=20, le=50),
    x_user_id: str = Header(None)
):
    """Advanced email search with filters"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    emails = search_manager.search_emails(
        x_user_id, q or "", limit, category, urgency_min, is_important
    )
    
    email_list = []
    for email in emails:
        email_list.append({
            'id': email.gmail_message_id,
            'thread_id': email.thread_id,
            'subject': email.subject,
            'sender': email.sender,
            'recipient': email.recipient,
            'date': email.date_sent.isoformat() if email.date_sent else None,
            'snippet': email.snippet,
            'is_read': email.is_read,
            'is_starred': email.is_starred,
            'is_important': email.is_important,
            'category': email.category,
            'urgency': email.urgency,
            'has_attachments': len(email.attachments or []) > 0
        })
    
    return {
        "emails": email_list,
        "filters": {
            "query": q,
            "category": category,
            "urgency_min": urgency_min,
            "is_important": is_important
        },
        "count": len(email_list)
    }

@app.get("/emails/thread/{thread_id}")
async def get_thread_emails(thread_id: str, x_user_id: str = Header(None)):
    """Get all emails in a thread"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    emails = search_manager.search_by_thread(x_user_id, thread_id)
    
    email_list = []
    for email in emails:
        email_list.append({
            'id': email.gmail_message_id,
            'subject': email.subject,
            'sender': email.sender,
            'date': email.date_sent.isoformat() if email.date_sent else None,
            'body_html': email.processed_html or email.body_html,
            'body_text': email.body_text,
            'is_read': email.is_read,
            'attachments': email.attachments or []
        })
    
    return {
        "thread_id": thread_id,
        "emails": email_list,
        "count": len(email_list)
    }

@app.get("/emails/attachments")
async def get_emails_with_attachments(
    limit: int = Query(default=20, le=50),
    x_user_id: str = Header(None)
):
    """Get emails that have attachments"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    emails = search_manager.get_emails_with_attachments(x_user_id, limit)
    
    email_list = []
    for email in emails:
        email_list.append({
            'id': email.gmail_message_id,
            'subject': email.subject,
            'sender': email.sender,
            'date': email.date_sent.isoformat() if email.date_sent else None,
            'attachments': email.attachments,
            'attachment_count': len(email.attachments or [])
        })
    
    return {
        "emails": email_list,
        "count": len(email_list)
    }

@app.get("/emails/stats")
async def get_email_stats(x_user_id: str = Header(None)):
    """Get email statistics for current user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    stats = email_manager.get_email_stats(x_user_id)
    return stats

@app.put("/email/{email_id}/read")
async def mark_email_read(
    email_id: str,
    is_read: bool = True,
    x_user_id: str = Header(None)
):
    """Mark email as read/unread"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    with get_db() as db:
        email = db.query(Email).filter(
            Email.user_id == x_user_id,
            Email.gmail_message_id == email_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email.is_read = is_read
        email.updated_at = datetime.utcnow()
    
    return {
        "success": True,
        "email_id": email_id,
        "is_read": is_read
    }

@app.put("/email/{email_id}/star")
async def mark_email_starred(
    email_id: str,
    is_starred: bool = True,
    x_user_id: str = Header(None)
):
    """Mark email as starred/unstarred"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    with get_db() as db:
        email = db.query(Email).filter(
            Email.user_id == x_user_id,
            Email.gmail_message_id == email_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email.is_starred = is_starred
        email.updated_at = datetime.utcnow()
    
    return {
        "success": True,
        "email_id": email_id,
        "is_starred": is_starred,
        "message": f"Email {'starred' if is_starred else 'unstarred'} successfully"
    }

@app.put("/email/{email_id}/category")
async def update_email_category(
    email_id: str,
    category_data: CategoryUpdate,
    x_user_id: str = Header(None)
):
    """Update email category"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    # Validate category length (max 100 chars based on database schema)
    if category_data.category and len(category_data.category) > 100:
        raise HTTPException(status_code=400, detail="Category must be 100 characters or less")
    
    with get_db() as db:
        email = db.query(Email).filter(
            Email.user_id == x_user_id,
            Email.gmail_message_id == email_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email.category = category_data.category
        email.updated_at = datetime.utcnow()
    
    return {
        "success": True,
        "email_id": email_id,
        "category": category_data.category,
        "message": "Email category updated successfully"
    }

@app.put("/email/{email_id}/urgency")
async def update_email_urgency(
    email_id: str,
    urgency_data: UrgencyUpdate,
    x_user_id: str = Header(None)
):
    """Update email urgency level (0-10 scale)"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    with get_db() as db:
        email = db.query(Email).filter(
            Email.user_id == x_user_id,
            Email.gmail_message_id == email_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email.urgency = urgency_data.urgency
        email.updated_at = datetime.utcnow()
    
    return {
        "success": True,
        "email_id": email_id,
        "urgency": urgency_data.urgency,
        "message": "Email urgency updated successfully"
    }

@app.post("/emails/bulk")
async def save_bulk_emails(
    emails_data: dict,
    x_user_id: str = Header(None)
):
    """Save bulk emails from Gmail service"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    emails = emails_data.get("emails", [])
    if not emails:
        return {"success": True, "saved_count": 0}
    
    saved_count = email_manager.save_emails(x_user_id, emails)
    
    return {
        "success": True,
        "saved_count": saved_count,
        "total_received": len(emails)
    }

@app.post("/emails/sync")
async def sync_emails(x_user_id: str = Header(...)):
    """Sync emails from Gmail via gmail-service"""
    try:
        # Forward sync request to gmail-service
        gmail_service_url = os.getenv('GMAIL_SERVICE_URL', 'http://localhost:5001')
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gmail_service_url}/sync",
                headers={"X-User-ID": x_user_id},
                timeout=60.0  # Longer timeout for sync
            )
            
            if response.status_code == 200:
                return {"status": "sync_completed", "message": "Emails synced successfully"}
            else:
                raise HTTPException(status_code=response.status_code, detail="Sync failed")
                
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gmail service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
