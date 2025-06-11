# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/models/email.py
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Email(Base):
    """Email model for storing Gmail messages"""
    __tablename__ = 'emails'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    gmail_message_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, index=True)
    
    # Basic email fields
    subject = Column(String)
    sender = Column(String, index=True)
    recipient = Column(String)
    cc = Column(String)  # New field
    bcc = Column(String)  # New field
    reply_to = Column(String)  # New field
    
    # Dates and content
    date_sent = Column(DateTime)
    snippet = Column(Text)
    body_text = Column(Text)
    body_html = Column(Text)
    processed_html = Column(Text)  # New field for processed HTML
    
    # Email metadata
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    is_important = Column(Boolean, default=False)  # New field
    is_draft = Column(Boolean, default=False)  # New field
    
    # Enhanced fields from gmail-service
    category = Column(String, index=True)
    urgency = Column(Integer, default=0)  # 0-10 scale
    has_tls = Column(Boolean, default=False)  # New security field
    
    # Message headers and metadata
    message_id = Column(String)  # Message-ID header
    references = Column(Text)  # References header
    in_reply_to = Column(String)  # In-Reply-To header
    list_unsubscribe = Column(String)  # List-Unsubscribe header
    
    # Gmail-specific data
    gmail_labels = Column(JSONB)  # Store label information
    gmail_metadata = Column(JSONB)  # Store other Gmail metadata
    attachments = Column(JSONB)  # Store attachment information
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Email {self.gmail_message_id}: {self.subject}>"