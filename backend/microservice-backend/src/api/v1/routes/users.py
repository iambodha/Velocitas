from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....database.connection import get_db
from ....database.models.user import User
from ....schemas.user import UserResponse, UserUpdate, UserWithConnections
from ...deps import get_current_active_user, rate_limit_dependency
from ....core.cache import cached

router = APIRouter()

@router.get("/me", response_model=UserWithConnections)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with connections"""
    # Refresh user data to include connections
    db.refresh(current_user)
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Update current user profile"""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.delete("/me")
async def delete_my_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Delete current user account"""
    db.delete(current_user)
    db.commit()
    
    return {"message": "Account deleted successfully"}

@router.get("/me/stats")
@cached(ttl=300)  # Cache for 5 minutes
async def get_my_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user statistics"""
    from ....database.models.email import Email
    from ....database.models.connection import Connection
    
    # Count connections
    connections_count = db.query(Connection).filter(
        Connection.user_id == current_user.id,
        Connection.is_active == True
    ).count()
    
    # Count emails across all connections
    total_emails = db.query(Email).join(Connection).filter(
        Connection.user_id == current_user.id
    ).count()
    
    # Count unread emails
    unread_emails = db.query(Email).join(Connection).filter(
        Connection.user_id == current_user.id,
        Email.is_read == False,
        Email.is_deleted == False
    ).count()
    
    return {
        "connections_count": connections_count,
        "total_emails": total_emails,
        "unread_emails": unread_emails,
        "read_emails": total_emails - unread_emails
    }