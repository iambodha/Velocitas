from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid

from ....database.connection import get_db
from ....database.models.connection import Connection
from ....database.models.user import User
from ....schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate
from ...deps import get_current_active_user, rate_limit_dependency
from ....services.gmail_service import GmailService
from ....core.cache import EmailCache

router = APIRouter()

@router.get("/", response_model=List[ConnectionResponse])
async def get_my_connections(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all user connections"""
    connections = db.query(Connection).filter(
        Connection.user_id == current_user.id
    ).all()
    
    return connections

@router.post("/", response_model=ConnectionResponse)
async def create_connection(
    connection_data: ConnectionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Create a new email connection"""
    # Check if connection already exists
    existing = db.query(Connection).filter(
        Connection.user_id == current_user.id,
        Connection.email == connection_data.email,
        Connection.provider == connection_data.provider
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection already exists"
        )
    
    # Create new connection
    connection = Connection(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        provider=connection_data.provider,
        email=connection_data.email,
        name=connection_data.name,
        access_token=connection_data.access_token,
        refresh_token=connection_data.refresh_token,
        token_expires_at=connection_data.token_expires_at,
        settings=connection_data.settings
    )
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    # Start initial sync in background
    if connection_data.provider == "gmail":
        background_tasks.add_task(GmailService.initial_sync, connection.id)
    
    return connection

@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific connection"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    return connection

@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: str,
    connection_update: ConnectionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Update connection"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    update_data = connection_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connection, field, value)
    
    db.commit()
    db.refresh(connection)
    
    # Invalidate related caches
    EmailCache.invalidate_user_emails(current_user.id)
    
    return connection

@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Delete connection"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    db.delete(connection)
    db.commit()
    
    # Invalidate related caches
    EmailCache.invalidate_user_emails(current_user.id)
    
    return {"message": "Connection deleted successfully"}

@router.post("/{connection_id}/sync")
async def sync_connection(
    connection_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Manually trigger connection sync"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    if connection.is_syncing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection is already syncing"
        )
    
    # Start sync in background
    if connection.provider == "gmail":
        background_tasks.add_task(GmailService.sync_emails, connection_id)
    
    return {"message": "Sync started"}

@router.get("/{connection_id}/status")
async def get_connection_status(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get connection sync status"""
    from ....database.models.email import SyncStatus
    
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.user_id == current_user.id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Get latest sync status
    latest_sync = db.query(SyncStatus).filter(
        SyncStatus.connection_id == connection_id
    ).order_by(SyncStatus.started_at.desc()).first()
    
    return {
        "connection": connection,
        "latest_sync": latest_sync,
        "is_syncing": connection.is_syncing
    }