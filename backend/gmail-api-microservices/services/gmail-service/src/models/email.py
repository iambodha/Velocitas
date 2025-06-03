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