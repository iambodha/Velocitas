# filepath: /gmail-api-microservices/gmail-api-microservices/services/gmail-service/src/models/email.py
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class EmailCache(Base):
    """Cache for Gmail API responses"""
    __tablename__ = 'gmail_email_cache'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    gmail_message_id = Column(String(255), nullable=False, index=True)
    
    # Gmail API raw data
    raw_data = Column(JSONB, nullable=False)
    
    # Cache metadata
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_cache_user_gmail_id', 'user_id', 'gmail_message_id', unique=True),
        Index('idx_cache_expires', 'expires_at'),
    )

class SyncStatus(Base):
    """Track sync status for users"""
    __tablename__ = 'gmail_sync_status'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Sync tracking
    last_sync_at = Column(DateTime, nullable=True)
    last_message_id = Column(String(255), nullable=True)
    total_synced = Column(Integer, default=0)
    sync_in_progress = Column(Boolean, default=False)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from shared.models.schemas import Email, User
from shared.database import get_db_context  # Use context manager for manual handling
from ..handlers.gmail_api import ParsedMessage, EmailAddress, Attachment
from ..utils.email_parser import EmailParser
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Enhanced email service for sophisticated Gmail data handling"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_parsed_message(self, user_id: str, parsed_message: ParsedMessage) -> Email:
        """Save a sophisticated parsed message to database"""
        try:
            # Check if email already exists
            existing_email = self.db.query(Email).filter(
                and_(
                    Email.user_id == user_id,
                    Email.gmail_message_id == parsed_message.id
                )
            ).first()
            
            if existing_email:
                # Update existing email with new data
                return self._update_email_from_parsed(existing_email, parsed_message)
            
            # Create new email record
            email = Email(
                user_id=user_id,
                gmail_message_id=parsed_message.id,
                subject=EmailParser.clean_subject(parsed_message.subject),
                sender=str(parsed_message.sender),
                recipient=self._format_recipients(parsed_message.to),
                date_sent=self._parse_date(parsed_message.date),
                body_text=parsed_message.body_text,
                body_html=parsed_message.processed_html,  # Use processed HTML
                snippet=parsed_message.snippet,
                is_read=parsed_message.is_read,
                is_starred=parsed_message.is_starred,
                category=self._determine_category(parsed_message),
                urgency=self._calculate_urgency(parsed_message),
                gmail_metadata=self._create_metadata(parsed_message)
            )
            
            self.db.add(email)
            self.db.commit()
            self.db.refresh(email)
            
            logger.info(f"Saved new email {parsed_message.id} for user {user_id}")
            return email
            
        except Exception as e:
            logger.error(f"Error saving parsed message: {e}")
            self.db.rollback()
            raise
    
    def save_thread_messages(self, user_id: str, thread_data: Dict[str, Any]) -> List[Email]:
        """Save all messages from a thread"""
        saved_emails = []
        
        try:
            for message_data in thread_data.get('messages', []):
                # Convert dict back to ParsedMessage if needed
                if isinstance(message_data, dict):
                    parsed_message = self._dict_to_parsed_message(message_data)
                else:
                    parsed_message = message_data
                
                email = self.save_parsed_message(user_id, parsed_message)
                saved_emails.append(email)
            
            return saved_emails
            
        except Exception as e:
            logger.error(f"Error saving thread messages: {e}")
            self.db.rollback()
            raise
    
    def get_user_emails(self, user_id: str, 
                       category: Optional[str] = None,
                       is_read: Optional[bool] = None,
                       limit: int = 50,
                       offset: int = 0) -> List[Email]:
        """Get user emails with sophisticated filtering"""
        query = self.db.query(Email).filter(Email.user_id == user_id)
        
        if category:
            query = query.filter(Email.category == category)
        
        if is_read is not None:
            query = query.filter(Email.is_read == is_read)
        
        return query.order_by(desc(Email.date_sent)).offset(offset).limit(limit).all()
    
    def search_emails(self, user_id: str, search_term: str, limit: int = 50) -> List[Email]:
        """Advanced email search"""
        return self.db.query(Email).filter(
            and_(
                Email.user_id == user_id,
                or_(
                    Email.subject.ilike(f'%{search_term}%'),
                    Email.sender.ilike(f'%{search_term}%'),
                    Email.body_text.ilike(f'%{search_term}%'),
                    Email.snippet.ilike(f'%{search_term}%')
                )
            )
        ).order_by(desc(Email.date_sent)).limit(limit).all()
    
    def get_email_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get sophisticated email analytics"""
        total_emails = self.db.query(Email).filter(Email.user_id == user_id).count()
        unread_emails = self.db.query(Email).filter(
            and_(Email.user_id == user_id, Email.is_read == False)
        ).count()
        starred_emails = self.db.query(Email).filter(
            and_(Email.user_id == user_id, Email.is_starred == True)
        ).count()
        
        # Category breakdown
        category_stats = self.db.query(
            Email.category, 
            self.db.func.count(Email.id)
        ).filter(Email.user_id == user_id).group_by(Email.category).all()
        
        return {
            'total_emails': total_emails,
            'unread_emails': unread_emails,
            'starred_emails': starred_emails,
            'read_percentage': (total_emails - unread_emails) / total_emails * 100 if total_emails > 0 else 0,
            'categories': dict(category_stats)
        }
    
    def _update_email_from_parsed(self, email: Email, parsed_message: ParsedMessage) -> Email:
        """Update existing email with new parsed data"""
        email.subject = EmailParser.clean_subject(parsed_message.subject)
        email.body_text = parsed_message.body_text
        email.body_html = parsed_message.processed_html
        email.is_read = parsed_message.is_read
        email.is_starred = parsed_message.is_starred
        email.category = self._determine_category(parsed_message)
        email.urgency = self._calculate_urgency(parsed_message)
        email.gmail_metadata = self._create_metadata(parsed_message)
        email.updated_at = datetime.utcnow()
        
        self.db.commit()
        return email
    
    def _format_recipients(self, recipients: List[EmailAddress]) -> str:
        """Format recipients for storage"""
        if not recipients:
            return ""
        return ", ".join([str(addr) for addr in recipients])
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse email date string to datetime"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_string)
        except Exception:
            logger.warning(f"Could not parse date: {date_string}")
            return None
    
    def _determine_category(self, parsed_message: ParsedMessage) -> str:
        """Determine email category based on sophisticated analysis"""
        # Check for promotional indicators
        if any(keyword in parsed_message.subject.lower() for keyword in 
               ['sale', 'offer', 'discount', 'deal', 'promotion']):
            return 'promotional'
        
        # Check for automated/system emails
        if any(keyword in parsed_message.sender.email.lower() for keyword in 
               ['noreply', 'no-reply', 'donotreply', 'automated', 'system']):
            return 'automated'
        
        # Check for newsletters
        if parsed_message.list_unsubscribe:
            return 'newsletter'
        
        # Check for important indicators
        if parsed_message.is_important or 'urgent' in parsed_message.subject.lower():
            return 'important'
        
        return 'primary'
    
    def _calculate_urgency(self, parsed_message: ParsedMessage) -> int:
        """Calculate urgency score (0-10)"""
        urgency = 0
        
        # Base urgency
        if parsed_message.is_important:
            urgency += 3
        
        # Subject indicators
        urgent_keywords = ['urgent', 'asap', 'immediate', 'emergency', 'critical']
        if any(keyword in parsed_message.subject.lower() for keyword in urgent_keywords):
            urgency += 4
        
        # Sender domain analysis
        sender_domain = parsed_message.sender.email.split('@')[-1].lower()
        if sender_domain in ['gmail.com', 'company.com']:  # Add your important domains
            urgency += 1
        
        # Security indicators
        if parsed_message.has_tls:
            urgency += 1
        
        return min(urgency, 10)  # Cap at 10
    
    def _create_metadata(self, parsed_message: ParsedMessage) -> Dict[str, Any]:
        """Create comprehensive metadata from parsed message"""
        return {
            'thread_id': parsed_message.thread_id,
            'message_id': parsed_message.message_id,
            'labels': [label['id'] for label in parsed_message.labels],
            'attachments': [
                {
                    'filename': att.filename,
                    'mime_type': att.mime_type,
                    'size': att.size,
                    'attachment_id': att.attachment_id
                }
                for att in parsed_message.attachments
            ],
            'security': {
                'has_tls': parsed_message.has_tls,
            },
            'recipients': {
                'to': [{'email': addr.email, 'name': addr.name} for addr in parsed_message.to],
                'cc': [{'email': addr.email, 'name': addr.name} for addr in (parsed_message.cc or [])],
            },
            'headers': {
                'reply_to': parsed_message.reply_to,
                'references': parsed_message.references,
                'in_reply_to': parsed_message.in_reply_to,
                'list_unsubscribe': parsed_message.list_unsubscribe,
            }
        }
    
    def _dict_to_parsed_message(self, data: Dict[str, Any]) -> ParsedMessage:
        """Convert dictionary back to ParsedMessage object"""
        # This is a simplified conversion - you might need to implement full conversion
        # depending on your needs
        return ParsedMessage(
            id=data['id'],
            thread_id=data['thread_id'],
            subject=data['subject'],
            sender=EmailAddress(email=data['sender']['email'], name=data['sender'].get('name')),
            to=[EmailAddress(email=addr['email'], name=addr.get('name')) for addr in data['to']],
            cc=None,  # Implement if needed
            bcc=None,
            date=data['date'],
            snippet=data['snippet'],
            body_text=data['body_text'],
            body_html=data['body_html'],
            processed_html=data['processed_html'],
            is_read=data['is_read'],
            is_starred=data['is_starred'],
            is_important=data['is_important'],
            is_draft=data['is_draft'],
            labels=data['labels'],
            attachments=[],  # Implement if needed
            message_id=data.get('message_id'),
            reply_to=data.get('reply_to'),
            references=data.get('references'),
            in_reply_to=data.get('in_reply_to'),
            list_unsubscribe=data.get('list_unsubscribe'),
            has_tls=data.get('has_tls', False),
            raw_message=data.get('raw_message', {})
        )
    
    # For methods that need manual session handling, use get_db_context:
    def bulk_save_operation(self, user_id: str, data: List[Dict]):
        """Example of using context manager for bulk operations"""
        with get_db_context() as db:
            # Bulk operations here
            pass