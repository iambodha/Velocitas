from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from shared.database import get_db  # FastAPI dependency version
from shared.models.schemas import User
from ..handlers.gmail_api import GmailAPIHandler
from ..models.email import EmailService
import logging
import httpx

logger = logging.getLogger(__name__)

async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)  # Use FastAPI dependency
) -> User:
    """Get current user from authorization header"""
    try:
        # Extract user ID from authorization header
        # This is a simplified version - implement proper JWT/token validation
        user_id = authorization.replace("Bearer ", "")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=401, detail="Invalid authorization")

async def get_gmail_handler(
    user_id: str
) -> GmailAPIHandler:
    """Get initialized Gmail handler for user"""
    try:
        # Get credentials from auth service
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                f"http://localhost:5000/credentials",  # AUTH_SERVICE_URL
                headers={"X-User-ID": user_id}
            )
            
            if auth_response.status_code != 200:
                raise Exception("Could not get credentials")
            
            credentials_data = auth_response.json()
        
        # Initialize Gmail handler
        handler = GmailAPIHandler()
        credentials = handler.create_credentials_from_dict(credentials_data)
        handler.initialize_service(credentials)
        
        return handler
    except Exception as e:
        logger.error(f"Error initializing Gmail handler: {e}")
        raise

async def get_email_service(db: Session = Depends(get_db)) -> EmailService:
    """Get email service instance"""
    return EmailService(db)

def decrypt_credentials(encrypted_data: str) -> dict:
    """Decrypt user credentials - implement proper encryption/decryption"""
    # Placeholder implementation
    import json
    return json.loads(encrypted_data)