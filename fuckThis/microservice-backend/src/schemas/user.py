from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import BaseSchema

class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, max_length=255, description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    provider: Optional[str] = Field("email", description="Authentication provider")
    provider_id: Optional[str] = Field(None, description="Provider user ID")

class UserCreate(UserBase):
    """Schema for creating a user"""
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()
    
    @validator('name')
    def validate_name(cls, v):
        if v:
            return v.strip()
        return v

class UserUpdate(BaseModel):
    """Schema for updating a user"""
    name: Optional[str] = Field(None, max_length=255, description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    is_active: Optional[bool] = Field(None, description="Whether user is active")
    
    @validator('name')
    def validate_name(cls, v):
        if v:
            return v.strip()
        return v

class UserResponse(BaseSchema, UserBase):
    """Schema for user response"""
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether user is verified")
    preferences: Dict[str, Any] = Field(..., description="User preferences")

class UserWithConnections(UserResponse):
    """User response with connections"""
    from .connection import ConnectionResponse
    connections: List[ConnectionResponse] = Field(default_factory=list, description="User email connections")

class UserStats(BaseModel):
    """User statistics schema"""
    connections_count: int = Field(..., description="Number of email connections")
    total_emails: int = Field(..., description="Total number of emails")
    unread_emails: int = Field(..., description="Number of unread emails")
    read_emails: int = Field(..., description="Number of read emails")
    starred_emails: int = Field(..., description="Number of starred emails")
    important_emails: int = Field(..., description="Number of important emails")
    archived_emails: int = Field(..., description="Number of archived emails")
    draft_emails: int = Field(..., description="Number of draft emails")
    sent_emails: int = Field(..., description="Number of sent emails")
    spam_emails: int = Field(..., description="Number of spam emails")

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr = Field(..., description="User email")
    password: Optional[str] = Field(None, description="User password")
    remember_me: bool = Field(False, description="Whether to remember login")

class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    session_id: str = Field(..., description="Session identifier")
    user: UserResponse = Field(..., description="User information")

class TokenRefreshResponse(BaseModel):
    """Token refresh response schema"""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")