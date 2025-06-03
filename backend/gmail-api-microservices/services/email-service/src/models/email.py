# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/models/email.py
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Email(Base):
    """Email model for storing Gmail messages"""
    __tablename__ = 'emails'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    gmail_message_id = Column(String(255), nullable=False, index=True)
    
    # Email content
    subject = Column(Text, nullable=True)
    sender = Column(String(500), nullable=True)
    recipient = Column(String(500), nullable=True)
    date_sent = Column(DateTime, nullable=True)
    
    # Email body (can be large)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    
    # Gmail metadata stored as JSON
    gmail_metadata = Column(JSONB, nullable=True)
    
    # Processing metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    # New fields
    is_starred = Column(Boolean, default=False)
    category = Column(String(100), nullable=True, index=True)
    urgency = Column(Integer, default=0, nullable=True)
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_email_user_gmail_id', 'user_id', 'gmail_message_id', unique=True),
        Index('idx_email_user_date', 'user_id', 'date_sent'),
        Index('idx_email_user_read', 'user_id', 'is_read'),
        Index('idx_email_sender', 'sender'),
        Index('idx_email_starred', 'user_id', 'is_starred'),
        Index('idx_email_category', 'user_id', 'category'),
        Index('idx_email_urgency', 'user_id', 'urgency'),
    )