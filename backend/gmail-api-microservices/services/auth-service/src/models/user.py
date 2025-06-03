from sqlalchemy import Column, String, Text, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """User model with secure credential storage"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    
    # Encrypted credential storage
    encrypted_credentials = Column(Text, nullable=True)
    credentials_updated_at = Column(DateTime, nullable=True)
    
    # User metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Add indexes for performance
    __table_args__ = (
        Index('idx_user_google_id', 'google_user_id'),
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
    )