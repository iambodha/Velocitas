from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid

from ....database.connection import get_db
from ....database.models.user import User
from ....core.config import settings
from ....core.security import create_access_token, verify_password, get_password_hash
from ....schemas.user import UserCreate, UserResponse
from ....core.session import SessionManager
from ...deps import get_current_user, rate_limit_dependency

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        name=user_data.name,
        avatar_url=user_data.avatar_url,
        provider=user_data.provider,
        provider_id=user_data.provider_id,
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Login and get access token"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    # Create session
    session_id = SessionManager.create_session(user.id, {"login_time": "now"})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "session_id": session_id,
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Logout user"""
    SessionManager.delete_session(session_id)
    return {"message": "Successfully logged out"}

@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.id}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }