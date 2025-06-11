from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .base import BaseSchema

class ProviderType(str, Enum):
    """Email provider types"""
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    IMAP = "imap"
    EXCHANGE = "exchange"

class ConnectionBase(BaseModel):
    """Base connection schema"""
    provider: ProviderType = Field(..., description="Email provider type")
    email: EmailStr = Field(..., description="Email address")
    name: Optional[str] = Field(None, max_length=255, description="Connection name")
    
    # IMAP/SMTP settings
    imap_host: Optional[str] = Field(None, description="IMAP server host")
    imap_port: Optional[int] = Field(None, ge=1, le=65535, description="IMAP server port")
    smtp_host: Optional[str] = Field(None, description="SMTP server host")
    smtp_port: Optional[int] = Field(None, ge=1, le=65535, description="SMTP server port")
    use_ssl: bool = Field(True, description="Use SSL connection")
    use_tls: bool = Field(True, description="Use TLS connection")
    
    # Provider specific settings
    settings: Dict[str, Any] = Field(default_factory=dict, description="Provider specific settings")
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()

class ConnectionCreate(ConnectionBase):
    """Schema for creating a connection"""
    # OAuth tokens (for Gmail, Outlook)
    access_token: Optional[str] = Field(None, description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    
    # IMAP credentials
    password: Optional[str] = Field(None, description="Email password (for IMAP)")
    
    sync_frequency: int = Field(300, ge=60, le=3600, description="Sync frequency in seconds")

class ConnectionUpdate(BaseModel):
    """Schema for updating a connection"""
    name: Optional[str] = Field(None, max_length=255, description="Connection name")
    
    # OAuth tokens
    access_token: Optional[str] = Field(None, description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    
    # IMAP/SMTP settings
    imap_host: Optional[str] = Field(None, description="IMAP server host")
    imap_port: Optional[int] = Field(None, ge=1, le=65535, description="IMAP server port")
    smtp_host: Optional[str] = Field(None, description="SMTP server host")
    smtp_port: Optional[int] = Field(None, ge=1, le=65535, description="SMTP server port")
    use_ssl: Optional[bool] = Field(None, description="Use SSL connection")
    use_tls: Optional[bool] = Field(None, description="Use TLS connection")
    
    # Connection settings
    is_active: Optional[bool] = Field(None, description="Whether connection is active")
    sync_frequency: Optional[int] = Field(None, ge=60, le=3600, description="Sync frequency in seconds")
    settings: Optional[Dict[str, Any]] = Field(None, description="Provider specific settings")

class ConnectionResponse(BaseSchema, ConnectionBase):
    """Schema for connection response"""
    user_id: str = Field(..., description="User ID")
    
    # Connection status
    is_active: bool = Field(..., description="Whether connection is active")
    is_syncing: bool = Field(..., description="Whether connection is currently syncing")
    last_sync_at: Optional[datetime] = Field(None, description="Last sync timestamp")
    sync_frequency: int = Field(..., description="Sync frequency in seconds")
    
    # Hide sensitive data
    access_token: Optional[str] = Field(None, exclude=True)
    refresh_token: Optional[str] = Field(None, exclude=True)

class ConnectionWithStats(ConnectionResponse):
    """Connection with email statistics"""
    email_count: int = Field(..., description="Total number of emails")
    unread_count: int = Field(..., description="Number of unread emails")
    last_email_at: Optional[datetime] = Field(None, description="Timestamp of last email")

class SyncStatusResponse(BaseSchema):
    """Sync status response schema"""
    connection_id: str = Field(..., description="Connection ID")
    sync_type: str = Field(..., description="Type of sync (full, incremental, real-time)")
    status: str = Field(..., description="Sync status (pending, running, completed, failed)")
    
    # Sync metrics
    total_emails: int = Field(0, description="Total emails to process")
    processed_emails: int = Field(0, description="Number of processed emails")
    new_emails: int = Field(0, description="Number of new emails")
    updated_emails: int = Field(0, description="Number of updated emails")
    failed_emails: int = Field(0, description="Number of failed emails")
    
    # Sync timing
    started_at: Optional[datetime] = Field(None, description="Sync start time")
    completed_at: Optional[datetime] = Field(None, description="Sync completion time")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")

class ConnectionStatusResponse(BaseModel):
    """Connection status with latest sync"""
    connection: ConnectionResponse = Field(..., description="Connection details")
    latest_sync: Optional[SyncStatusResponse] = Field(None, description="Latest sync status")
    is_syncing: bool = Field(..., description="Whether currently syncing")