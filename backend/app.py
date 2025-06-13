import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import io
import asyncio
from datetime import datetime

# Import our modules
from email_retrieval import (
    get_email_by_id_async, 
    get_attachment_data_async, 
    search_emails_async,
    get_user_emails_async,
    get_starred_emails_async
)
from gmailDownload import sync_emails_async
from auth import (
    AuthService, 
    UserService, 
    SessionService,
    get_current_user, 
    get_current_user_id,
    rate_limiter
)
from models import User

app = FastAPI(title="Velocitas Email API", version="1.0.0", description="Production-ready email management API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://yourdomain.com"],  # Update with your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for requests/responses
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

class EmailUpdateRequest(BaseModel):
    is_starred: Optional[bool] = None
    is_read: Optional[bool] = None
    category: Optional[str] = None
    urgency: Optional[int] = None

# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Authentication endpoints
@app.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister, request: Request):
    """Register a new user account"""
    client_ip = get_client_ip(request)
    
    # Rate limiting
    if rate_limiter.is_rate_limited(f"register_{client_ip}", max_attempts=3, window_minutes=60):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")
    
    rate_limiter.record_attempt(f"register_{client_ip}")
    
    try:
        # Create user
        user = await UserService.create_user(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name
        )
        
        # Generate tokens
        tokens = AuthService.generate_tokens(str(user.id))
        
        # Create session
        await SessionService.create_session(
            user_id=str(user.id),
            refresh_token=tokens['refresh_token'],
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent")
        )
        
        return TokenResponse(
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_type=tokens['token_type'],
            user={
                'id': str(user.id),
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
    """Login with email and password"""
    client_ip = get_client_ip(request)
    
    # Rate limiting
    if rate_limiter.is_rate_limited(f"login_{client_ip}", max_attempts=5, window_minutes=15):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    
    rate_limiter.record_attempt(f"login_{client_ip}")
    
    # Authenticate user
    user = await UserService.authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate tokens
    tokens = AuthService.generate_tokens(str(user.id))
    
    # Create session
    await SessionService.create_session(
        user_id=str(user.id),
        refresh_token=tokens['refresh_token'],
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent")
    )
    
    return TokenResponse(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        token_type=tokens['token_type'],
        user={
            'id': str(user.id),
            'email': user.email,
            'name': user.name,
            'is_active': user.is_active
        }
    )

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(token_data: RefreshTokenRequest, request: Request):
    """Refresh access token using refresh token"""
    client_ip = get_client_ip(request)
    
    # Rate limiting
    if rate_limiter.is_rate_limited(f"refresh_{client_ip}", max_attempts=10, window_minutes=5):
        raise HTTPException(status_code=429, detail="Too many refresh attempts. Please try again later.")
    
    rate_limiter.record_attempt(f"refresh_{client_ip}")
    
    # Verify and refresh token
    new_tokens = AuthService.refresh_access_token(token_data.refresh_token)
    if not new_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Get user info
    payload = AuthService.verify_token(token_data.refresh_token, 'refresh')
    user = await UserService.get_user_by_id(payload['user_id'])
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Create new session
    await SessionService.create_session(
        user_id=str(user.id),
        refresh_token=new_tokens['refresh_token'],
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent")
    )
    
    # Invalidate old session
    await SessionService.invalidate_session(token_data.refresh_token)
    
    return TokenResponse(
        access_token=new_tokens['access_token'],
        refresh_token=new_tokens['refresh_token'],
        token_type=new_tokens['token_type'],
        user={
            'id': str(user.id),
            'email': user.email,
            'name': user.name,
            'is_active': user.is_active
        }
    )

@app.post("/auth/logout")
async def logout(token_data: RefreshTokenRequest, current_user: User = Depends(get_current_user)):
    """Logout user and invalidate session"""
    await SessionService.invalidate_session(token_data.refresh_token)
    return {"message": "Successfully logged out"}

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

# Protected email endpoints
@app.get("/emails")
async def get_emails(
    q: str = Query("", description="Search query"),
    max_results: int = Query(50, description="Maximum number of emails to return"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get list of emails with optional search for the authenticated user"""
    if q:
        search_results = await search_emails_async(q, max_results, current_user_id)
        return {"emails": search_results}
    
    emails = await get_user_emails_async(current_user_id, limit=max_results)
    return {"emails": emails}

@app.get("/emails/starred")
async def get_starred_emails(
    max_results: int = Query(50, description="Maximum number of starred emails to return"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get starred emails for the authenticated user"""
    starred_emails = await get_starred_emails_async(current_user_id, limit=max_results)
    return {"emails": starred_emails}

@app.get("/email/{email_id}")
async def get_email(
    email_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get specific email with full details for the authenticated user"""
    email = await get_email_by_id_async(email_id, current_user_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return email

@app.get("/email/{email_id}/attachment/{attachment_id}")
async def download_attachment(
    email_id: str,
    attachment_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Download attachment for the authenticated user"""
    attachment = await get_attachment_data_async(attachment_id, current_user_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    return StreamingResponse(
        io.BytesIO(attachment['data']),
        media_type=attachment['mime_type'],
        headers={
            "Content-Disposition": f"attachment; filename={attachment['filename']}"
        }
    )

@app.post("/emails/sync")
async def sync_gmail_emails(
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """Trigger Gmail email synchronization for the authenticated user"""
    # Start email sync in background task
    background_tasks.add_task(sync_emails_async, current_user_id)
    
    return {
        "status": "sync_started",
        "message": "Email synchronization process has been started",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/emails/sync/status")
async def get_sync_status(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get current sync status for the authenticated user"""
    # In a real implementation, you'd check a database or cache for the status
    # For now we'll return a placeholder
    
    return {
        "status": "completed",
        "last_sync": datetime.utcnow().isoformat(),
        "emails_synced": 0
    }

# Health check endpoint (public)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Velocitas Email API is running", "version": "1.0.0"}

# Cleanup task (run periodically)
@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    # Schedule session cleanup
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    """Periodic cleanup of expired sessions"""
    while True:
        try:
            await SessionService.cleanup_expired_sessions()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            print(f"Cleanup error: {e}")
            await asyncio.sleep(3600)

@app.put("/email/{email_id}")
async def update_email(
    email_id: str,
    update_data: EmailUpdateRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update email properties (starred, read, category, urgency) for the authenticated user"""
    from models import DatabaseSession, Email
    
    session = DatabaseSession()
    try:
        # Find the email and verify it belongs to the current user
        email = session.query(Email).filter(
            Email.id == email_id,
            Email.user_id == current_user_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Update fields if provided
        if update_data.is_starred is not None:
            email.is_starred = update_data.is_starred
        if update_data.is_read is not None:
            email.is_read = update_data.is_read
        if update_data.category is not None:
            email.category = update_data.category
        if update_data.urgency is not None:
            if update_data.urgency < 1 or update_data.urgency > 100:
                raise HTTPException(status_code=400, detail="Urgency must be between 1 and 100")
            email.urgency = update_data.urgency
        
        session.commit()
        
        return {
            "message": "Email updated successfully",
            "email_id": email_id,
            "updated_fields": {
                "is_starred": email.is_starred,
                "is_read": email.is_read,
                "category": email.category,
                "urgency": email.urgency
            }
        }
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update email: {str(e)}")
    finally:
        session.close()

@app.put("/emails/bulk-update")
async def bulk_update_emails(
    email_ids: list[str],
    update_data: EmailUpdateRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Bulk update email properties for multiple emails"""
    from models import DatabaseSession, Email
    
    session = DatabaseSession()
    try:
        # Find emails that belong to the current user
        emails = session.query(Email).filter(
            Email.id.in_(email_ids),
            Email.user_id == current_user_id
        ).all()
        
        if not emails:
            raise HTTPException(status_code=404, detail="No emails found")
        
        updated_count = 0
        for email in emails:
            # Update fields if provided
            if update_data.is_starred is not None:
                email.is_starred = update_data.is_starred
            if update_data.is_read is not None:
                email.is_read = update_data.is_read
            if update_data.category is not None:
                email.category = update_data.category
            if update_data.urgency is not None:
                if update_data.urgency < 1 or update_data.urgency > 100:
                    raise HTTPException(status_code=400, detail="Urgency must be between 1 and 100")
                email.urgency = update_data.urgency
            updated_count += 1
        
        session.commit()
        
        return {
            "message": f"Successfully updated {updated_count} emails",
            "updated_count": updated_count,
            "total_requested": len(email_ids)
        }
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to bulk update emails: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8002, reload=True)