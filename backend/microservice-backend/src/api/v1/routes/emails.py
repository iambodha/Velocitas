from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
import uuid

from ....database.connection import get_db
from ....database.models.email import Email, EmailThread
from ....database.models.connection import Connection
from ....database.models.user import User
from ....schemas.email import EmailResponse, EmailListResponse, EmailUpdate
from ...deps import get_current_active_user, rate_limit_dependency
from ....core.cache import EmailCache, cached

router = APIRouter()

@router.get("/", response_model=EmailListResponse)
async def get_emails(
    connection_id: Optional[str] = Query(None, description="Filter by connection ID"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    is_starred: Optional[bool] = Query(None, description="Filter by starred status"),
    search: Optional[str] = Query(None, description="Search in subject and body"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user emails with filtering and pagination"""
    
    # Check cache first
    cache_key = f"{current_user.id}:{connection_id}:{is_read}:{is_starred}:{search}:{page}:{per_page}"
    cached_result = EmailCache.get_user_emails(cache_key)
    if cached_result:
        return cached_result
    
    # Build query
    query = db.query(Email).join(Connection).filter(
        Connection.user_id == current_user.id,
        Email.is_deleted == False
    )
    
    # Apply filters
    if connection_id:
        query = query.filter(Email.connection_id == connection_id)
    
    if is_read is not None:
        query = query.filter(Email.is_read == is_read)
    
    if is_starred is not None:
        query = query.filter(Email.is_starred == is_starred)
    
    if search:
        search_filter = or_(
            Email.subject.ilike(f"%{search}%"),
            Email.body_text.ilike(f"%{search}%"),
            Email.from_email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    emails = query.order_by(desc(Email.date_sent)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    result = EmailListResponse(
        emails=emails,
        total=total,
        page=page,
        per_page=per_page,
        has_next=total > page * per_page
    )
    
    # Cache result for 5 minutes
    EmailCache.cache_user_emails(cache_key, result.dict(), ttl=300)
    
    return result

@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific email"""
    email = db.query(Email).join(Connection).filter(
        Email.id == email_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    # Mark as read if not already
    if not email.is_read:
        email.is_read = True
        db.commit()
        
        # Invalidate user email cache
        EmailCache.invalidate_user_emails(current_user.id)
    
    return email

@router.put("/{email_id}", response_model=EmailResponse)
async def update_email(
    email_id: str,
    email_update: EmailUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Update email (mark as read, starred, etc.)"""
    email = db.query(Email).join(Connection).filter(
        Email.id == email_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    update_data = email_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(email, field, value)
    
    db.commit()
    db.refresh(email)
    
    # Invalidate caches
    EmailCache.invalidate_user_emails(current_user.id)
    
    return email

@router.delete("/{email_id}")
async def delete_email(
    email_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Soft delete email"""
    email = db.query(Email).join(Connection).filter(
        Email.id == email_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    email.is_deleted = True
    db.commit()
    
    # Invalidate caches
    EmailCache.invalidate_user_emails(current_user.id)
    
    return {"message": "Email deleted successfully"}

@router.get("/threads/{thread_id}")
async def get_email_thread(
    thread_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get emails in a thread"""
    # Verify thread belongs to user
    thread = db.query(EmailThread).join(Connection).filter(
        EmailThread.id == thread_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    emails = db.query(Email).filter(
        Email.thread_id == thread_id,
        Email.is_deleted == False
    ).order_by(Email.date_sent).all()
    
    return {
        "thread": thread,
        "emails": emails
    }

@router.post("/bulk-update")
async def bulk_update_emails(
    email_ids: List[str],
    update_data: EmailUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Bulk update multiple emails"""
    # Verify all emails belong to user
    emails = db.query(Email).join(Connection).filter(
        Email.id.in_(email_ids),
        Connection.user_id == current_user.id
    ).all()
    
    if len(emails) != len(email_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some emails not found or don't belong to user"
        )
    
    update_dict = update_data.dict(exclude_unset=True)
    
    for email in emails:
        for field, value in update_dict.items():
            setattr(email, field, value)
    
    db.commit()
    
    # Invalidate caches
    EmailCache.invalidate_user_emails(current_user.id)
    
    return {"message": f"Updated {len(emails)} emails"}