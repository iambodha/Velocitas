from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..config.supabase import supabase, admin_supabase, supabase_config
from ..models.schemas import UserResponse
import logging
from typing import Optional, Dict, Any
import json
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

class AuthUtils:
    @staticmethod
    def get_user_from_token(token: str) -> Optional[Dict[Any, Any]]:
        """Get user from Supabase JWT token"""
        try:
            # Verify and get user from token
            response = supabase.auth.get_user(token)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": response.user.user_metadata.get("name"),
                    "email_confirmed_at": response.user.email_confirmed_at,
                    "created_at": response.user.created_at,
                    "updated_at": response.user.updated_at
                }
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    @staticmethod
    def normalize_scopes(scopes: list) -> list:
        """Normalize scopes by removing openid and sorting"""
        if not scopes:
            return []
        
        # Remove 'openid' scope and sort for consistency
        normalized = [scope for scope in scopes if scope != 'openid']
        normalized.sort()
        return normalized
    
    @staticmethod
    def store_gmail_credentials(user_id: str, credentials: Dict[str, Any]) -> bool:
        """Store Gmail credentials in local PostgreSQL"""
        try:
            db = next(supabase_config.get_db_session())
            
            # Normalize scopes before storing
            if 'scopes' in credentials:
                credentials['scopes'] = AuthUtils.normalize_scopes(credentials['scopes'])
            
            # Use raw SQL to handle JSONB upsert
            query = text("""
                INSERT INTO gmail_credentials (user_id, credentials, updated_at)
                VALUES (:user_id, :credentials, NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    credentials = :credentials,
                    updated_at = NOW()
            """)
            
            db.execute(query, {
                "user_id": user_id,
                "credentials": json.dumps(credentials)
            })
            db.commit()
            
            logger.info(f"Stored Gmail credentials for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store Gmail credentials: {e}")
            if 'db' in locals():
                db.rollback()
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def get_gmail_credentials(user_id: str) -> Optional[Dict[str, Any]]:
        """Get Gmail credentials from local PostgreSQL"""
        try:
            db = next(supabase_config.get_db_session())
            
            query = text("SELECT credentials FROM gmail_credentials WHERE user_id = :user_id")
            result = db.execute(query, {"user_id": user_id}).fetchone()
            
            if result:
                creds = json.loads(result[0])
                # Ensure scopes are normalized when retrieving
                if 'scopes' in creds:
                    creds['scopes'] = AuthUtils.normalize_scopes(creds['scopes'])
                return creds
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Gmail credentials: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()

# Dependency to get current user
async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> UserResponse:
    """FastAPI dependency to get current authenticated user"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_data = AuthUtils.get_user_from_token(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return UserResponse(**user_data)

# Optional dependency (doesn't raise error if no auth)
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[UserResponse]:
    """Optional authentication - returns None if not authenticated"""
    if not credentials:
        return None
    
    user_data = AuthUtils.get_user_from_token(credentials.credentials)
    if not user_data:
        return None
    
    return UserResponse(**user_data)