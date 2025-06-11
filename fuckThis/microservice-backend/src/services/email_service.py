from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import uuid
from datetime import datetime

from ..database.models.email import Email, EmailThread, EmailAction, SyncStatus
from ..database.models.connection import Connection
from ..database.models.attachment import Attachment
from ..core.cache import EmailCache
from ..core.redis import redis_client

class EmailService:
    
    @staticmethod
    def get_user_emails(
        db: Session,
        user_id: str,
        connection_id: Optional[str] = None,
        filters: Dict[str, Any] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Get user emails with filtering and pagination"""
        
        filters = filters or {}
        
        # Build base query
        query = db.query(Email).join(Connection).filter(
            Connection.user_id == user_id,
            Email.is_deleted == False
        )
        
        # Apply filters
        if connection_id:
            query = query.filter(Email.connection_id == connection_id)
        
        if filters.get("is_read") is not None:
            query = query.filter(Email.is_read == filters["is_read"])
        
        if filters.get("is_starred") is not None:
            query = query.filter(Email.is_starred == filters["is_starred"])
        
        if filters.get("is_important") is not None:
            query = query.filter(Email.is_important == filters["is_important"])
        
        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            search_filter = or_(
                Email.subject.ilike(search_term),
                Email.body_text.ilike(search_term),
                Email.from_email.ilike(search_term),
                Email.from_name.ilike(search_term)
            )
            query = query.filter(search_filter)
        
        if filters.get("date_from"):
            query = query.filter(Email.date_sent >= filters["date_from"])
        
        if filters.get("date_to"):
            query = query.filter(Email.date_sent <= filters["date_to"])
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        emails = query.order_by(desc(Email.date_sent)).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        return {
            "emails": emails,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": total > page * per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    
    @staticmethod
    def get_email_by_id(db: Session, email_id: str, user_id: str) -> Optional[Email]:
        """Get email by ID for user"""
        return db.query(Email).join(Connection).filter(
            Email.id == email_id,
            Connection.user_id == user_id
        ).first()
    
    @staticmethod
    def mark_email_as_read(db: Session, email_id: str, user_id: str) -> bool:
        """Mark email as read"""
        email = EmailService.get_email_by_id(db, email_id, user_id)
        if not email:
            return False
        
        if not email.is_read:
            email.is_read = True
            
            # Log action
            EmailService.log_email_action(db, email_id, user_id, "read")
            
            db.commit()
            
            # Invalidate cache
            EmailCache.invalidate_user_emails(user_id)
        
        return True
    
    @staticmethod
    def update_email_status(
        db: Session, 
        email_id: str, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[Email]:
        """Update email status fields"""
        email = EmailService.get_email_by_id(db, email_id, user_id)
        if not email:
            return None
        
        # Track what changed for logging
        actions = []
        
        for field, value in updates.items():
            if hasattr(email, field):
                old_value = getattr(email, field)
                setattr(email, field, value)
                
                # Log specific actions
                if field == "is_read" and value != old_value:
                    actions.append("read" if value else "unread")
                elif field == "is_starred" and value != old_value:
                    actions.append("star" if value else "unstar")
                elif field == "is_archived" and value != old_value:
                    actions.append("archive" if value else "unarchive")
                elif field == "is_deleted" and value != old_value:
                    actions.append("delete" if value else "restore")
        
        db.commit()
        db.refresh(email)
        
        # Log actions
        for action in actions:
            EmailService.log_email_action(db, email_id, user_id, action)
        
        # Invalidate cache
        EmailCache.invalidate_user_emails(user_id)
        
        return email
    
    @staticmethod
    def bulk_update_emails(
        db: Session,
        email_ids: List[str],
        user_id: str,
        updates: Dict[str, Any]
    ) -> int:
        """Bulk update multiple emails"""
        emails = db.query(Email).join(Connection).filter(
            Email.id.in_(email_ids),
            Connection.user_id == user_id
        ).all()
        
        updated_count = 0
        for email in emails:
            for field, value in updates.items():
                if hasattr(email, field):
                    setattr(email, field, value)
            updated_count += 1
        
        db.commit()
        
        # Invalidate cache
        EmailCache.invalidate_user_emails(user_id)
        
        return updated_count
    
    @staticmethod
    def get_email_thread(db: Session, thread_id: str, user_id: str) -> Dict[str, Any]:
        """Get email thread with all messages"""
        thread = db.query(EmailThread).join(Connection).filter(
            EmailThread.id == thread_id,
            Connection.user_id == user_id
        ).first()
        
        if not thread:
            return None
        
        emails = db.query(Email).filter(
            Email.thread_id == thread_id,
            Email.is_deleted == False
        ).order_by(Email.date_sent).all()
        
        return {
            "thread": thread,
            "emails": emails,
            "message_count": len(emails)
        }
    
    @staticmethod
    def search_emails(
        db: Session,
        user_id: str,
        query: str,
        filters: Dict[str, Any] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Full-text search emails"""
        
        # Use the existing get_user_emails with search filter
        search_filters = filters or {}
        search_filters["search"] = query
        
        return EmailService.get_user_emails(
            db, user_id, None, search_filters, page, per_page
        )
    
    @staticmethod
    def log_email_action(
        db: Session,
        email_id: str,
        user_id: str,
        action: str,
        metadata: Dict[str, Any] = None
    ):
        """Log email action"""
        email_action = EmailAction(
            id=str(uuid.uuid4()),
            email_id=email_id,
            user_id=user_id,
            action=action,
            metadata=metadata or {}
        )
        
        db.add(email_action)
        db.commit()
    
    @staticmethod
    def get_email_stats(db: Session, user_id: str) -> Dict[str, int]:
        """Get email statistics for user"""
        
        # Check cache first
        cache_key = f"email_stats:{user_id}"
        cached_stats = redis_client.get(cache_key)
        if cached_stats:
            return cached_stats
        
        base_query = db.query(Email).join(Connection).filter(
            Connection.user_id == user_id,
            Email.is_deleted == False
        )
        
        stats = {
            "total_emails": base_query.count(),
            "unread_emails": base_query.filter(Email.is_read == False).count(),
            "starred_emails": base_query.filter(Email.is_starred == True).count(),
            "important_emails": base_query.filter(Email.is_important == True).count(),
            "archived_emails": base_query.filter(Email.is_archived == True).count(),
            "draft_emails": base_query.filter(Email.is_draft == True).count(),
            "sent_emails": base_query.filter(Email.is_sent == True).count(),
            "spam_emails": base_query.filter(Email.is_spam == True).count()
        }
        
        stats["read_emails"] = stats["total_emails"] - stats["unread_emails"]
        
        # Cache for 5 minutes
        redis_client.set(cache_key, stats, 300)
        
        return stats
    
    @staticmethod
    def get_email_attachments(db: Session, email_id: str, user_id: str) -> List[Attachment]:
        """Get attachments for an email"""
        email = EmailService.get_email_by_id(db, email_id, user_id)
        if not email:
            return []
        
        return db.query(Attachment).filter(Attachment.email_id == email_id).all()
    
    @staticmethod
    def create_or_update_email(
        db: Session,
        connection_id: str,
        email_data: Dict[str, Any]
    ) -> Email:
        """Create or update email from external source"""
        
        # Check if email already exists
        existing_email = db.query(Email).filter(
            Email.connection_id == connection_id,
            Email.message_id == email_data["message_id"]
        ).first()
        
        if existing_email:
            # Update existing email
            for field, value in email_data.items():
                if hasattr(existing_email, field):
                    setattr(existing_email, field, value)
            
            db.commit()
            db.refresh(existing_email)
            return existing_email
        
        # Create new email
        email = Email(
            id=str(uuid.uuid4()),
            connection_id=connection_id,
            **email_data
        )
        
        db.add(email)
        db.commit()
        db.refresh(email)
        
        return email