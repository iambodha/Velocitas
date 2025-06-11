from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum

from .base import BaseSchema

class FileType(str, Enum):
    """File type categories"""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"

class AttachmentBase(BaseModel):
    """Base attachment schema"""
    filename: str = Field(..., max_length=500, description="Original filename")
    content_type: Optional[str] = Field(None, description="MIME content type")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v.strip():
            raise ValueError('Filename cannot be empty')
        return v.strip()

class AttachmentCreate(AttachmentBase):
    """Schema for creating an attachment"""
    email_id: str = Field(..., description="Email ID this attachment belongs to")
    file_data: Optional[bytes] = Field(None, description="File data")
    is_inline: bool = Field(False, description="Whether attachment is inline")
    content_id: Optional[str] = Field(None, description="Content ID for inline attachments")

class AttachmentUpdate(BaseModel):
    """Schema for updating an attachment"""
    filename: Optional[str] = Field(None, max_length=500, description="Filename")
    is_downloaded: Optional[bool] = Field(None, description="Whether attachment is downloaded")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    file_type: Optional[FileType] = Field(None, description="File type category")

class AttachmentResponse(BaseSchema, AttachmentBase):
    """Schema for attachment response"""
    email_id: str = Field(..., description="Email ID")
    
    # Storage information
    file_path: Optional[str] = Field(None, description="Local file path")
    cloud_url: Optional[str] = Field(None, description="Cloud storage URL")
    provider_attachment_id: Optional[str] = Field(None, description="Provider attachment ID")
    
    # Attachment metadata
    is_inline: bool = Field(False, description="Whether attachment is inline")
    is_downloaded: bool = Field(False, description="Whether attachment is downloaded")
    content_id: Optional[str] = Field(None, description="Content ID for inline attachments")
    
    # AI features
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    file_type: Optional[FileType] = Field(None, description="File type category")

class AttachmentDownloadResponse(BaseModel):
    """Schema for attachment download response"""
    filename: str = Field(..., description="Filename")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., description="File size")
    download_url: str = Field(..., description="Temporary download URL")
    expires_at: str = Field(..., description="URL expiration time")