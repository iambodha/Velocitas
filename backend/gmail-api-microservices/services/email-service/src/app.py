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
    x_user_id: str = Header(None)
):
    """Get emails from database"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    email_list = email_manager.get_user_emails(x_user_id, limit, offset)
    
    return {
        "emails": email_list,
        "user_id": x_user_id,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
