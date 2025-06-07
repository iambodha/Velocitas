# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/handlers/crud.py

from typing import List, Optional, Dict
from ..database.db import get_db
from ..models.email import Email
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

class EmailManager:
    """Manage email storage in PostgreSQL"""
    
    def save_emails(self, user_id: str, emails: List[dict]):
        """Save emails to database, avoiding duplicates"""
        with get_db() as db:
            saved_count = 0
            for email_data in emails:
                try:
                    # Check if email already exists
                    existing = db.query(Email).filter(
                        Email.user_id == user_id,
                        Email.gmail_message_id == email_data['id']
                    ).first()
                    
                    if not existing:
                        # Parse date
                        date_sent = None
                        if email_data.get('date'):
                            try:
                                from email.utils import parsedate_to_datetime
                                date_sent = parsedate_to_datetime(email_data['date'])
                            except:
                                pass
                        
                        email = Email(
                            user_id=user_id,
                            gmail_message_id=email_data['id'],
                            subject=email_data.get('subject'),
                            sender=email_data.get('sender'),
                            recipient=email_data.get('to'),
                            date_sent=date_sent,
                            body_text=email_data.get('body'),
                            body_html=email_data.get('body_html'),
                            snippet=email_data.get('snippet'),
                            gmail_metadata=email_data.get('gmail_data'),
                            is_read=email_data.get('is_read', False),
                            is_starred=email_data.get('is_starred', False),
                            category=email_data.get('category')
                        )
                        db.add(email)
                        saved_count += 1
                
                except IntegrityError:
                    # Skip duplicate emails
                    db.rollback()
                    continue
                except Exception as e:
                    print(f"Error saving email {email_data.get('id')}: {e}")
                    continue
            
            return saved_count
    
    def get_user_emails(self, user_id: str, limit: int = 50, offset: int = 0) -> List[dict]:
        """Get user emails from database"""
        with get_db() as db:
            emails = db.query(Email).filter(
                Email.user_id == user_id
            ).order_by(
                Email.date_sent.desc().nullslast()
            ).offset(offset).limit(limit).all()
            
            # Convert SQLAlchemy objects to dictionaries before session closes
            email_list = []
            for email in emails:
                email_list.append({
                    'id': email.gmail_message_id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'recipient': email.recipient,
                    'date': email.date_sent.isoformat() if email.date_sent else None,
                    'snippet': email.snippet,
                    'is_read': email.is_read,
                    'is_starred': email.is_starred,
                    'category': email.category,
                    'urgency': email.urgency,
                    'stored_at': email.created_at.isoformat()
                })
            
            return email_list
    
    def get_email_by_gmail_id(self, user_id: str, gmail_message_id: str) -> Optional[dict]:
        """Get specific email by Gmail message ID"""
        with get_db() as db:
            email = db.query(Email).filter(
                Email.user_id == user_id,
                Email.gmail_message_id == gmail_message_id
            ).first()
            
            if not email:
                return None
            
            # Convert to dictionary before session closes
            return {
                "id": email.gmail_message_id,
                "subject": email.subject,
                "sender": email.sender,
                "recipient": email.recipient,
                "date": email.date_sent.isoformat() if email.date_sent else None,
                "body_text": email.body_text,
                "body_html": email.body_html,
                "snippet": email.snippet,
                "is_read": email.is_read,
                "is_starred": email.is_starred,
                "category": email.category,
                "urgency": email.urgency,
                "source": "database"
            }
    
    def get_email_stats(self, user_id: str) -> dict:
        """Get email statistics for user"""
        with get_db() as db:
            total = db.query(Email).filter(Email.user_id == user_id).count()
            unread = db.query(Email).filter(
                Email.user_id == user_id,
                Email.is_read == False
            ).count()
            
            # Top senders
            top_senders = db.execute(text("""
                SELECT sender, COUNT(*) as email_count
                FROM emails 
                WHERE user_id = :user_id AND sender IS NOT NULL
                GROUP BY sender 
                ORDER BY email_count DESC 
                LIMIT 10
            """), {"user_id": user_id}).fetchall()
            
            return {
                "total_emails": total,
                "unread_emails": unread,
                "top_senders": [{"sender": row.sender, "count": row.email_count} for row in top_senders]
            }