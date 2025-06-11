from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from shared.database import get_db  # FastAPI dependency version
from shared.models.schemas import User
from ..handlers.gmail_api import GmailAPIHandler
from ..models.email import EmailService
import logging
import httpx
import os
from google.auth.transport.requests import Request as GoogleRequest

logger = logging.getLogger(__name__)

async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from authorization header"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        
        # Call auth service to verify token
        auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{auth_service_url}/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                user = db.query(User).filter(User.id == user_data["user_id"]).first()
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                return user
            else:
                raise HTTPException(status_code=401, detail="Token verification failed")
                
    except httpx.RequestError as e:
        logger.error(f"Auth service connection error: {e}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=401, detail="Invalid authorization")

def validate_credentials(creds_data: dict) -> dict:
    """Validate and return credentials with better error handling"""
    required_fields = ['token', 'token_uri', 'client_id', 'client_secret', 'scopes']
    missing_fields = [field for field in required_fields if not creds_data.get(field)]
    
    if missing_fields:
        raise ValueError(f"Missing required credential fields: {missing_fields}")
    
    # Check for refresh token - warn but don't fail immediately
    if not creds_data.get('refresh_token'):
        logger.warning("No refresh token available - user may need to re-authenticate when token expires")
    
    return creds_data

async def get_gmail_handler(
    authorization: str = Header(...)
) -> GmailAPIHandler:
    """Get Gmail handler with proper credential validation"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        
        # Get credentials from auth service
        auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{auth_service_url}/credentials",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Could not get credentials")
            
            creds_data = response.json()
            logger.info(f"Received credentials keys: {list(creds_data.keys())}")
            
            try:
                validated_creds = validate_credentials(creds_data)
                
                # Create credentials object
                from ..handlers.gmail_api import GmailAPIHandler
                handler = GmailAPIHandler()
                
                credentials = handler.create_credentials_from_dict(validated_creds)
                
                # Check if token is expired
                if credentials.expired:
                    if credentials.refresh_token:
                        try:
                            credentials.refresh(GoogleRequest())
                            logger.info("Successfully refreshed expired credentials")
                        except Exception as e:
                            logger.error(f"Failed to refresh credentials: {e}")
                            raise HTTPException(
                                status_code=401, 
                                detail="Credentials expired and could not be refreshed. Please re-authenticate."
                            )
                    else:
                        raise HTTPException(
                            status_code=401, 
                            detail="Credentials expired and no refresh token available. Please re-authenticate."
                        )
                
                return handler
            
            except ValueError as e:
                logger.error(f"Invalid credentials structure: {e}")
                raise HTTPException(status_code=401, detail=f"Invalid credentials: {e}")
            
    except httpx.RequestError as e:
        logger.error(f"Auth service connection error: {e}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing Gmail handler: {e}")
        raise HTTPException(status_code=500, detail="Could not initialize Gmail handler")

async def get_email_service(db: Session = Depends(get_db)) -> EmailService:
    """Get email service instance"""
    return EmailService(db)

def decrypt_credentials(encrypted_data: str) -> dict:
    """Decrypt user credentials - implement proper encryption/decryption"""
    # Placeholder implementation
    import json
    return json.loads(encrypted_data)