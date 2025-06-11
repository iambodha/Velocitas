# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/handlers/search.py

from typing import List, Optional
from ..database.db import get_db
from ..models.email import Email
from sqlalchemy import or_, and_

class EmailSearchManager:
    """Enhanced email search with new fields"""
    
    def search_emails(self, user_id: str, query: str, limit: int = 20, 
                     category: Optional[str] = None,
                     urgency_min: Optional[int] = None,
                     is_important: Optional[bool] = None) -> List[Email]:
        """Enhanced search with new filters"""
        with get_db() as db:
            search_query = db.query(Email).filter(Email.user_id == user_id)
            
            # Text search
            if query:
                search_query = search_query.filter(
                    or_(
                        Email.subject.ilike(f'%{query}%'),
                        Email.sender.ilike(f'%{query}%'),
                        Email.body_text.ilike(f'%{query}%'),
                        Email.snippet.ilike(f'%{query}%')
                    )
                )
            
            # Category filter
            if category:
                search_query = search_query.filter(Email.category == category)
            
            # Urgency filter
            if urgency_min is not None:
                search_query = search_query.filter(Email.urgency >= urgency_min)
            
            # Importance filter
            if is_important is not None:
                search_query = search_query.filter(Email.is_important == is_important)
            
            return search_query.order_by(
                Email.date_sent.desc().nullslast()
            ).limit(limit).all()
    
    def search_by_thread(self, user_id: str, thread_id: str) -> List[Email]:
        """Search emails by thread ID"""
        with get_db() as db:
            return db.query(Email).filter(
                and_(
                    Email.user_id == user_id,
                    Email.thread_id == thread_id
                )
            ).order_by(Email.date_sent.asc()).all()
    
    def get_emails_with_attachments(self, user_id: str, limit: int = 20) -> List[Email]:
        """Get emails that have attachments"""
        with get_db() as db:
            return db.query(Email).filter(
                and_(
                    Email.user_id == user_id,
                    Email.attachments.isnot(None),
                    Email.attachments != '[]'
                )
            ).order_by(Email.date_sent.desc()).limit(limit).all()