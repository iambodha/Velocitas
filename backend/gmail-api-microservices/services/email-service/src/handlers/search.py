# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/handlers/search.py

from typing import List
from ..database.db import get_db
from ..models.email import Email

class EmailSearchManager:
    """Manage email search functionality"""
    
    def search_emails(self, user_id: str, query: str, limit: int = 20) -> List[Email]:
        """Search emails by subject or sender"""
        with get_db() as db:
            return db.query(Email).filter(
                Email.user_id == user_id,
                (Email.subject.ilike(f'%{query}%') | 
                 Email.sender.ilike(f'%{query}%'))
            ).order_by(
                Email.date_sent.desc().nullslast()
            ).limit(limit).all()