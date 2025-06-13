from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import datetime

# Database configuration
DATABASE_URL = "postgresql://download_user:test123@localhost:5432/gmail_db"

# Setup database models
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # For password-based auth
    google_user_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Email verification status
    
    # Relationships
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

class Email(Base):
    __tablename__ = 'emails'
    
    id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    thread_id = Column(String, index=True)
    subject = Column(Text)
    sender = Column(String)
    recipients = Column(Text)
    snippet = Column(Text)
    html_body = Column(Text)
    plain_body = Column(Text)
    category = Column(String)
    label_ids = Column(Text)
    internal_date = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="emails")
    attachments = relationship("Attachment", back_populates="email", cascade="all, delete-orphan")

class Attachment(Base):
    __tablename__ = 'attachments'
    
    id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    email_id = Column(String, ForeignKey('emails.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String)
    mime_type = Column(String)
    data = Column(Text)  # Base64 encoded
    
    # Relationships
    user = relationship("User", back_populates="attachments")
    email = relationship("Email", back_populates="attachments")

class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    refresh_token = Column(String(500), nullable=False, unique=True)
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

# Create DB engine
engine = create_engine(DATABASE_URL)

# Only create tables that don't exist, don't recreate existing ones
Base.metadata.create_all(engine, checkfirst=True)
DatabaseSession = sessionmaker(bind=engine)  # Renamed from Session to DatabaseSession