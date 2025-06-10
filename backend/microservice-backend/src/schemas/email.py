from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .base import BaseSchema, PaginationSchema

class EmailPriority(int, Enum):
    """Email priority levels"""
    LOWEST = 1
    LOW = 2
    NORMAL = 3
    HIGH = 4
    HIGHEST = 5

class EmailBase(BaseModel):
    """Base email schema"""
    subject: Optional[str] = Field(None, description="Email subject")
    from_email: Optional[str] = Field(None, description="Sender email address")
    from_name: Optional[str] = Field(None, description="Sender name")
    reply_to: Optional[str] = Field(None, description="Reply-to email address")
    
    to_emails: List[str] = Field(default_factory=list, description="Recipient email addresses")
    cc_emails: List[str] = Field(default_factory=list, description="CC email addresses")
    bcc_emails: List[str] = Field(default_factory=list, description="BCC email addresses")
    
    body_text: Optional[str] = Field(None, description="Plain text email body")
    body_html: Optional[str] = Field(None, description="HTML email body")
    snippet: Optional[str] = Field(None, description="Email snippet/preview")

class EmailCreate(EmailBase):
    """Schema for creating/sending an email"""
    connection_id: str = Field(..., description="Connection ID to send from")
    
    @validator('to_emails')
    def validate_to_emails(cls, v):
        if not v:
            raise ValueError('At least one recipient is required')
        return v

class EmailUpdate(BaseModel):
    """Schema for updating an email"""
    is_read: Optional[bool] = Field(None, description="Whether email is read")
    is_starred: Optional[bool] = Field(None, description="Whether email is starred")
    is_important: Optional[bool] = Field(None, description="Whether email is important")
    is_archived: Optional[bool] = Field(None, description="Whether email is archived")
    is_deleted: Optional[bool] = Field(None, description="Whether email is deleted")
    priority: Optional[EmailPriority] = Field(None, description="Email priority")
    category: Optional[str] = Field(None, description="Email category")

class EmailResponse(BaseSchema, EmailBase):
    """Schema for email response"""
    connection_id: str = Field(..., description="Connection ID")
    thread_id: Optional[str] = Field(None, description="Thread ID")
    message_id: str = Field(..., description="Provider message ID")
    provider_message_id: Optional[str] = Field(None, description="Original provider message ID")
    
    # Email metadata
    date_sent: Optional[datetime] = Field(None, description="When email was sent")
    date_received: Optional[datetime] = Field(None, description="When email was received")
    
    # Email status
    is_read: bool = Field(False, description="Whether email is read")
    is_starred: bool = Field(False, description="Whether email is starred")
    is_important: bool = Field(False, description="Whether email is important")
    is_draft: bool = Field(False, description="Whether email is a draft")
    is_sent: bool = Field(False, description="Whether email is sent")
    is_deleted: bool = Field(False, description="Whether email is deleted")
    is_archived: bool = Field(False, description="Whether email is archived")
    is_spam: bool = Field(False, description="Whether email is spam")
    
    # Provider specific
    provider_labels: List[str] = Field(default_factory=list, description="Provider labels")
    provider_flags: Dict[str, Any] = Field(default_factory=dict, description="Provider flags")
    provider_folder: Optional[str] = Field(None, description="Provider folder")
    
    # Email properties
    size_bytes: Optional[int] = Field(None, description="Email size in bytes")
    has_attachments: bool = Field(False, description="Whether email has attachments")
    attachment_count: int = Field(0, description="Number of attachments")
    
    # AI/ML features
    summary: Optional[str] = Field(None, description="AI-generated summary")
    sentiment: Optional[Dict[str, Any]] = Field(None, description="Sentiment analysis")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    category: Optional[str] = Field(None, description="Auto-categorization")
    priority: EmailPriority = Field(EmailPriority.NORMAL, description="Email priority")

class EmailWithAttachments(EmailResponse):
    """Email response with attachments"""
    from .attachment import AttachmentResponse
    attachments: List[AttachmentResponse] = Field(default_factory=list, description="Email attachments")

class EmailListResponse(BaseModel):
    """Schema for paginated email list response"""
    emails: List[EmailResponse] = Field(..., description="List of emails")
    pagination: PaginationSchema = Field(..., description="Pagination information")

class EmailThreadResponse(BaseSchema):
    """Email thread response schema"""
    connection_id: str = Field(..., description="Connection ID")
    thread_id: str = Field(..., description="Provider thread ID")
    subject: Optional[str] = Field(None, description="Thread subject")
    participants: List[str] = Field(default_factory=list, description="Thread participants")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")
    message_count: int = Field(0, description="Number of messages in thread")
    is_archived: bool = Field(False, description="Whether thread is archived")

class EmailThreadWithMessages(EmailThreadResponse):
    """Email thread with messages"""
    emails: List[EmailResponse] = Field(default_factory=list, description="Thread messages")

class EmailSearchRequest(BaseModel):
    """Email search request schema"""
    query: str = Field(..., min_length=1, description="Search query")
    connection_id: Optional[str] = Field(None, description="Filter by connection")
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    is_starred: Optional[bool] = Field(None, description="Filter by starred status")
    is_important: Optional[bool] = Field(None, description="Filter by important status")
    date_from: Optional[datetime] = Field(None, description="Filter emails from this date")
    date_to: Optional[datetime] = Field(None, description="Filter emails until this date")
    has_attachments: Optional[bool] = Field(None, description="Filter by attachment presence")
    
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(50, ge=1, le=100, description="Items per page")

class EmailBulkUpdateRequest(BaseModel):
    """Bulk email update request schema"""
    email_ids: List[str] = Field(..., min_items=1, description="List of email IDs to update")
    updates: EmailUpdate = Field(..., description="Updates to apply")
    
    @validator('email_ids')
    def validate_email_ids(cls, v):
        if len(v) > 100:
            raise ValueError('Cannot update more than 100 emails at once')
        return v

class EmailStatsResponse(BaseModel):
    """Email statistics response"""
    total_emails: int = Field(..., description="Total number of emails")
    unread_emails: int = Field(..., description="Number of unread emails")
    read_emails: int = Field(..., description="Number of read emails")
    starred_emails: int = Field(..., description="Number of starred emails")
    important_emails: int = Field(..., description="Number of important emails")
    archived_emails: int = Field(..., description="Number of archived emails")
    draft_emails: int = Field(..., description="Number of draft emails")
    sent_emails: int = Field(..., description="Number of sent emails")
    spam_emails: int = Field(..., description="Number of spam emails")
    
    # Time-based stats
    today_emails: int = Field(..., description="Emails received today")
    week_emails: int = Field(..., description="Emails received this week")
    month_emails: int = Field(..., description="Emails received this month")

class EmailActionResponse(BaseSchema):
    """Email action response schema"""
    email_id: str = Field(..., description="Email ID")
    user_id: str = Field(..., description="User ID")
    action: str = Field(..., description="Action performed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Action metadata")