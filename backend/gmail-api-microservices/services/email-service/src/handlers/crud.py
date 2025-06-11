# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/handlers/crud.py

from typing import List, Optional, Dict, Any
from ..database.db import get_db
from ..models.email import Email
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import json
from email.utils import parsedate_to_datetime
from datetime import datetime

class EmailManager:
    """Manage email storage in PostgreSQL with enhanced gmail-service compatibility"""
    
    def save_emails(self, user_id: str, emails: List[dict]):
        """Save emails with enhanced data from gmail-service"""
        with get_db() as db:
            saved_count = 0
            for email_data in emails:
                try:
                    # Check if email already exists
                    existing = db.query(Email).filter(
                        Email.user_id == user_id,
                        Email.gmail_message_id == email_data['id']
                    ).first()
                    
                    if existing:
                        # Update existing email with new data
                        self._update_existing_email(existing, email_data)
                        saved_count += 1
                    else:
                        # Create new email
                        email = self._create_email_from_data(user_id, email_data)
                        db.add(email)
                        saved_count += 1
                        
                    db.commit()
                    
                except IntegrityError:
                    db.rollback()
                    continue
                except Exception as e:
                    print(f"Error saving email {email_data.get('id')}: {e}")
                    db.rollback()
                    continue
            
            return saved_count
    
    def _create_email_from_data(self, user_id: str, email_data: dict) -> Email:
        """Create Email object from gmail-service data"""
        # Parse date
        date_sent = None
        if email_data.get('date'):
            try:
                date_sent = parsedate_to_datetime(email_data['date'])
            except:
                pass
        
        # Format recipients
        recipient = self._format_recipients(email_data.get('to', []))
        cc = self._format_recipients(email_data.get('cc', []))
        bcc = self._format_recipients(email_data.get('bcc', []))
        
        # Parse sender
        sender = self._format_sender(email_data.get('sender', {}))
        
        return Email(
            user_id=user_id,
            gmail_message_id=email_data['id'],
            thread_id=email_data.get('thread_id'),
            subject=email_data.get('subject', ''),
            sender=sender,
            recipient=recipient,
            cc=cc,
            bcc=bcc,
            reply_to=email_data.get('reply_to'),
            date_sent=date_sent,
            snippet=email_data.get('snippet', ''),
            body_text=email_data.get('body_text', ''),
            body_html=email_data.get('body_html', ''),
            processed_html=email_data.get('processed_html', ''),
            is_read=email_data.get('is_read', False),
            is_starred=email_data.get('is_starred', False),
            is_important=email_data.get('is_important', False),
            is_draft=email_data.get('is_draft', False),
            category=email_data.get('category'),
            urgency=email_data.get('urgency', 0),
            has_tls=email_data.get('has_tls', False),
            message_id=email_data.get('message_id'),
            references=email_data.get('references'),
            in_reply_to=email_data.get('in_reply_to'),
            list_unsubscribe=email_data.get('list_unsubscribe'),
            gmail_labels=email_data.get('labels', []),
            gmail_metadata=email_data.get('raw_message', {}),
            attachments=email_data.get('attachments', [])
        )
    
    def _update_existing_email(self, email: Email, email_data: dict):
        """Update existing email with new data"""
        email.subject = email_data.get('subject', email.subject)
        email.body_text = email_data.get('body_text', email.body_text)
        email.body_html = email_data.get('body_html', email.body_html)
        email.processed_html = email_data.get('processed_html', email.processed_html)
        email.is_read = email_data.get('is_read', email.is_read)
        email.is_starred = email_data.get('is_starred', email.is_starred)
        email.is_important = email_data.get('is_important', email.is_important)
        email.is_draft = email_data.get('is_draft', email.is_draft)
        email.category = email_data.get('category', email.category)
        email.urgency = email_data.get('urgency', email.urgency)
        email.has_tls = email_data.get('has_tls', email.has_tls)
        email.gmail_labels = email_data.get('labels', email.gmail_labels)
        email.attachments = email_data.get('attachments', email.attachments)
        email.updated_at = datetime.utcnow()
    
    def _format_recipients(self, recipients: List[Dict]) -> str:
        """Format recipients list to string"""
        if not recipients:
            return ""
        
        formatted = []
        for recipient in recipients:
            if isinstance(recipient, dict):
                name = recipient.get('name')
                email = recipient.get('email', '')
                if name:
                    formatted.append(f"{name} <{email}>")
                else:
                    formatted.append(email)
            else:
                formatted.append(str(recipient))
        
        return ", ".join(formatted)
    
    def _format_sender(self, sender: Dict) -> str:
        """Format sender object to string"""
        if isinstance(sender, dict):
            name = sender.get('name')
            email = sender.get('email', '')
            if name:
                return f"{name} <{email}>"
            return email
        return str(sender)

    def get_user_emails(self, user_id: str, limit: int = 20, offset: int = 0, category: str = None):
        """Get user emails with optional category filter"""
        with get_db() as db:
            query = db.query(Email).filter(Email.user_id == user_id)
            
            # Add category filter if provided
            if category:
                query = query.filter(Email.category == category)
            
            emails = query.order_by(
                Email.date_sent.desc().nullslast()
            ).offset(offset).limit(limit).all()
            
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
                    'stored_at': email.created_at.isoformat() if email.created_at else None
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