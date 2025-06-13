import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import User, Session

# Security configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing configuration
BCRYPT_ROUNDS = 12

# Security schemes
security = HTTPBearer()

class AuthService:
    """Authentication service handling JWT tokens, password hashing, and user management"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def generate_tokens(user_id: str) -> Dict[str, str]:
        """Generate access and refresh tokens for a user"""
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        }
        
        access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer'
        }
    
    @staticmethod
    def verify_token(token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Check token type
            if payload.get('type') != token_type:
                return None
                
            # Check expiration
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                return None
                
            return payload
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
        """Generate new access token from refresh token"""
        payload = AuthService.verify_token(refresh_token, 'refresh')
        if not payload:
            return None
            
        user_id = payload['user_id']
        return AuthService.generate_tokens(user_id)

class UserService:
    """User management service"""
    
    @staticmethod
    async def create_user(email: str, password: str, name: str = None) -> User:
        """Create a new user account"""
        from models import DatabaseSession
        
        session = DatabaseSession()
        try:
            # Check if user already exists
            existing_user = session.query(User).filter(User.email == email).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Create new user
            hashed_password = AuthService.hash_password(password)
            user = User(
                email=email,
                name=name or email.split('@')[0],
                hashed_password=hashed_password,
                is_active=True,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Access all needed attributes while session is active to avoid DetachedInstanceError
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'hashed_password': user.hashed_password
            }
            
            # Create a new User object with the data (detached from session)
            detached_user = User()
            for key, value in user_data.items():
                setattr(detached_user, key, value)
            
            return detached_user
            
        finally:
            session.close()
    
    @staticmethod
    async def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        from models import DatabaseSession
        
        session = DatabaseSession()
        try:
            user = session.query(User).filter(User.email == email).first()
            
            if not user:
                return None
                
            if not user.is_active:
                return None
                
            if not AuthService.verify_password(password, user.hashed_password):
                return None
            
            # Update last login
            user.last_login = datetime.utcnow()
            session.commit()
            
            # Access all needed attributes while session is active to avoid DetachedInstanceError
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'hashed_password': user.hashed_password
            }
            
            # Create a new User object with the data (detached from session)
            detached_user = User()
            for key, value in user_data.items():
                setattr(detached_user, key, value)
            
            return detached_user
            
        finally:
            session.close()
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user by ID"""
        from models import DatabaseSession
        
        session = DatabaseSession()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Access all needed attributes while session is active to avoid DetachedInstanceError
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'hashed_password': user.hashed_password
            }
            
            # Create a new User object with the data (detached from session)
            detached_user = User()
            for key, value in user_data.items():
                setattr(detached_user, key, value)
            
            return detached_user
            
        finally:
            session.close()
    
    @staticmethod
    async def update_user_last_login(user_id: str):
        """Update user's last login timestamp"""
        from models import DatabaseSession
        
        session = DatabaseSession()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                session.commit()
        finally:
            session.close()

class SessionService:
    """Session management service"""
    
    @staticmethod
    async def create_session(user_id: str, refresh_token: str, ip_address: str = None, user_agent: str = None) -> Session:
        """Create a new user session"""
        from models import DatabaseSession
        
        db_session = DatabaseSession()
        try:
            # Invalidate old sessions (optional - keep only latest N sessions)
            old_sessions = db_session.query(Session).filter(
                Session.user_id == user_id
            ).order_by(Session.created_at.desc()).offset(5).all()  # Keep only 5 most recent sessions
            
            for old_session in old_sessions:
                db_session.delete(old_session)
            
            # Create new session
            session = Session(
                user_id=user_id,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                is_active=True
            )
            
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)
            
            return session
            
        finally:
            db_session.close()
    
    @staticmethod
    async def invalidate_session(refresh_token: str):
        """Invalidate a session by refresh token"""
        from models import DatabaseSession
        
        db_session = DatabaseSession()
        try:
            session = db_session.query(Session).filter(
                Session.refresh_token == refresh_token
            ).first()
            
            if session:
                session.is_active = False
                db_session.commit()
        finally:
            db_session.close()
    
    @staticmethod
    async def cleanup_expired_sessions():
        """Clean up expired sessions"""
        from models import DatabaseSession
        
        db_session = DatabaseSession()
        try:
            expired_sessions = db_session.query(Session).filter(
                Session.expires_at < datetime.utcnow()
            ).all()
            
            for session in expired_sessions:
                db_session.delete(session)
            
            db_session.commit()
        finally:
            db_session.close()

# Dependency for getting current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dependency to get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token
        payload = AuthService.verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        user_id = payload.get('user_id')
        if user_id is None:
            raise credentials_exception
        
        # Get user from database
        user = await UserService.get_user_by_id(user_id)
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Update last login
        await UserService.update_user_last_login(user_id)
        
        return user
        
    except Exception as e:
        raise credentials_exception

# Optional dependency for getting current user (allows None)
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[User]:
    """Optional dependency to get current authenticated user"""
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

# Dependency for getting user ID from token
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency to get current user ID"""
    user = await get_current_user(credentials)
    return str(user.id)

# Rate limiting helper (basic implementation)
class RateLimiter:
    def __init__(self):
        self.attempts = {}
    
    def is_rate_limited(self, identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """Check if identifier is rate limited"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Clean old attempts
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier] 
            if attempt > window_start
        ]
        
        return len(self.attempts[identifier]) >= max_attempts
    
    def record_attempt(self, identifier: str):
        """Record an attempt"""
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        self.attempts[identifier].append(datetime.utcnow())

# Global rate limiter instance
rate_limiter = RateLimiter()