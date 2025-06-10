from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import jwt
from jwt import PyJWTError

from ..database.models.user import User
from ..core.security import create_access_token, verify_password, get_password_hash
from ..core.config import settings
from ..core.session import SessionManager
from ..core.redis import redis_client

class AuthService:
    
    @staticmethod
    def register_user(
        db: Session,
        email: str,
        name: Optional[str] = None,
        provider: str = "email",
        provider_id: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> User:
        """Register a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("User already exists")
        
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            provider=provider,
            provider_id=provider_id,
            avatar_url=avatar_url,
            is_active=True,
            is_verified=provider != "email"  # OAuth users are auto-verified
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: Optional[str] = None) -> Optional[User]:
        """Authenticate user by email and password"""
        user = db.query(User).filter(User.email == email).first()
        
        if not user or not user.is_active:
            return None
        
        # For OAuth users, password is not required
        if user.provider != "email":
            return user
        
        # For email users, verify password (you'd need to add password field to User model)
        # if password and verify_password(password, user.password_hash):
        #     return user
        
        return user  # Simplified for now
    
    @staticmethod
    def create_user_session(user_id: str, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create user session and return tokens"""
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, 
            expires_delta=access_token_expires
        )
        
        # Create session
        session_data = {
            "login_time": datetime.utcnow().isoformat(),
            "user_agent": additional_data.get("user_agent") if additional_data else None,
            "ip_address": additional_data.get("ip_address") if additional_data else None
        }
        
        session_id = SessionManager.create_session(user_id, session_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "session_id": session_id
        }
    
    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """Verify JWT token and return user ID"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            return user_id
        except PyJWTError:
            return None
    
    @staticmethod
    def logout_user(session_id: str) -> bool:
        """Logout user by deleting session"""
        return SessionManager.delete_session(session_id)
    
    @staticmethod
    def get_user_sessions(user_id: str) -> list:
        """Get all active sessions for user"""
        pattern = f"session:*"
        session_keys = redis_client.get_keys_by_pattern(pattern)
        
        user_sessions = []
        for key in session_keys:
            session_data = redis_client.get(key)
            if session_data and session_data.get("user_id") == user_id:
                session_id = key.replace("session:", "")
                user_sessions.append({
                    "session_id": session_id,
                    "created_at": session_data.get("data", {}).get("login_time"),
                    "user_agent": session_data.get("data", {}).get("user_agent"),
                    "ip_address": session_data.get("data", {}).get("ip_address")
                })
        
        return user_sessions
    
    @staticmethod
    def revoke_all_sessions(user_id: str) -> int:
        """Revoke all sessions for user"""
        sessions = AuthService.get_user_sessions(user_id)
        count = 0
        
        for session in sessions:
            if SessionManager.delete_session(session["session_id"]):
                count += 1
        
        return count