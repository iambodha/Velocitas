from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, Union
from datetime import datetime

class UserSignUp(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserSignIn(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    email_confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"
    user: UserResponse

class GoogleAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordUpdateRequest(BaseModel):
    password: str
    access_token: str

class GmailCredentials(BaseModel):
    access_token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list

class SignupResponse(BaseModel):
    """Response for signup that might require email confirmation"""
    message: Optional[str] = None
    email_confirmation_required: Optional[bool] = False
    user_id: Optional[str] = None
    email: Optional[str] = None
    # Include auth response fields for immediate login
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = "bearer"
    user: Optional[UserResponse] = None