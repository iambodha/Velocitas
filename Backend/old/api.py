# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from contextlib import contextmanager
import os
import jwt
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from cryptography.fernet import Fernet
import httpx
import asyncio
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URI = os.getenv("DATABASE_URI", "postgresql+psycopg2://bodha@localhost:5432/email_db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# Database setup
engine = create_engine(
    DATABASE_URI,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(
    title="Enterprise Email API",
    description="Secure email processing system with multi-tenant support",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class UserSignupRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)
    oauth_provider: str = Field(..., pattern="^(google|microsoft|apple|custom)$")
    oauth_subject: str = Field(..., min_length=1, max_length=255)
    org_domain: str = Field(..., min_length=1, max_length=255)
    org_name: Optional[str] = Field(None, max_length=255)

class UserLoginRequest(BaseModel):
    email: EmailStr
    oauth_provider: str = Field(..., pattern="^(google|microsoft|apple|custom)$")
    oauth_subject: str = Field(..., min_length=1, max_length=255)
    oauth_token: Optional[str] = None  # For token verification

class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    org_id: str
    org_name: str
    org_domain: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class OrganizationResponse(BaseModel):
    org_id: str
    name: str
    domain: str
    subscription_tier: str
    max_users: int
    created_at: datetime

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def create_access_token(data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Query user from database
    user_query = """
        SELECT u.user_id, u.email, u.display_name, u.org_id, u.is_active, 
               u.is_verified, u.created_at, u.last_login, u.oauth_provider,
               o.name as org_name, o.domain as org_domain
        FROM users u
        JOIN organizations o ON u.org_id = o.org_id
        WHERE u.user_id = %s AND u.is_active = true
    """
    
    result = db.execute(user_query, (user_id,)).fetchone()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Set session variables for RLS
    db.execute("SELECT set_config('app.current_user_id', %s, true)", (str(result.user_id),))
    db.execute("SELECT set_config('app.current_org_id', %s, true)", (str(result.org_id),))
    db.commit()
    
    return result

async def verify_oauth_token(provider: str, token: str, expected_email: str) -> bool:
    """Verify OAuth token with the provider"""
    try:
        if provider == "google":
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?access_token={token}"
                )
                if response.status_code == 200:
                    token_info = response.json()
                    return token_info.get("email") == expected_email
        
        elif provider == "microsoft":
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=headers
                )
                if response.status_code == 200:
                    user_info = response.json()
                    return user_info.get("mail", user_info.get("userPrincipalName")) == expected_email
        
        # For apple and custom providers, implement similar verification
        logger.warning(f"OAuth verification not implemented for provider: {provider}")
        return True  # Skip verification for now
        
    except Exception as e:
        logger.error(f"OAuth token verification failed: {e}")
        return False

def get_or_create_organization(db: Session, domain: str, name: Optional[str] = None) -> uuid.UUID:
    """Get existing organization or create new one"""
    # Check if organization exists
    org_query = "SELECT org_id, name FROM organizations WHERE domain = %s"
    result = db.execute(org_query, (domain,)).fetchone()
    
    if result:
        return result.org_id
    
    # Create new organization
    org_id = uuid.uuid4()
    encryption_key_id = f"kms-key-{uuid.uuid4()}"  # In production, use actual KMS
    org_name = name or f"Organization {domain}"
    
    insert_org = """
        INSERT INTO organizations (org_id, name, domain, encryption_key_id, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """
    
    try:
        db.execute(insert_org, (org_id, org_name, domain, encryption_key_id))
        db.commit()
        logger.info(f"Created new organization: {org_name} ({domain})")
        return org_id
    except IntegrityError:
        db.rollback()
        # Race condition - organization was created by another request
        result = db.execute(org_query, (domain,)).fetchone()
        if result:
            return result.org_id
        raise

# API Endpoints
@app.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(request: UserSignupRequest, db: Session = Depends(get_db)):
    """Sign up a new user and create organization if needed"""
    try:
        # Verify OAuth token if provided
        if hasattr(request, 'oauth_token') and request.oauth_token:
            is_valid = await verify_oauth_token(
                request.oauth_provider, 
                request.oauth_token, 
                request.email
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OAuth token"
                )
        
        # Get or create organization
        org_id = get_or_create_organization(db, request.org_domain, request.org_name)
        
        # Check if user already exists
        existing_user_query = """
            SELECT user_id FROM users 
            WHERE oauth_provider = %s AND oauth_subject = %s
        """
        existing = db.execute(existing_user_query, (request.oauth_provider, request.oauth_subject)).fetchone()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        
        # Check organization user limit
        user_count_query = "SELECT COUNT(*) as count FROM users WHERE org_id = %s AND is_active = true"
        user_count = db.execute(user_count_query, (org_id,)).fetchone().count
        
        max_users_query = "SELECT max_users FROM organizations WHERE org_id = %s"
        max_users = db.execute(max_users_query, (org_id,)).fetchone().max_users
        
        if user_count >= max_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization user limit reached"
            )
        
        # Create user
        user_id = uuid.uuid4()
        user_encryption_key_id = f"user-key-{uuid.uuid4()}"
        
        insert_user = """
            INSERT INTO users (
                user_id, org_id, email, oauth_provider, oauth_subject, 
                display_name, user_encryption_key_id, created_at, is_verified
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """
        
        db.execute(insert_user, (
            user_id, org_id, request.email, request.oauth_provider,
            request.oauth_subject, request.display_name, user_encryption_key_id,
            True  # Assume verified if OAuth token is valid
        ))
        db.commit()
        
        # Get created user with organization info
        user_query = """
            SELECT u.user_id, u.email, u.display_name, u.org_id, u.is_active,
                   u.is_verified, u.created_at, u.last_login,
                   o.name as org_name, o.domain as org_domain
            FROM users u
            JOIN organizations o ON u.org_id = o.org_id
            WHERE u.user_id = %s
        """
        
        user_data = db.execute(user_query, (user_id,)).fetchone()
        
        # Create access token
        token_data = {
            "user_id": str(user_data.user_id),
            "email": user_data.email,
            "org_id": str(user_data.org_id)
        }
        access_token = create_access_token(token_data)
        
        # Create response
        user_response = UserResponse(
            user_id=str(user_data.user_id),
            email=user_data.email,
            display_name=user_data.display_name,
            org_id=str(user_data.org_id),
            org_name=user_data.org_name,
            org_domain=user_data.org_domain,
            is_active=user_data.is_active,
            is_verified=user_data.is_verified,
            created_at=user_data.created_at,
            last_login=user_data.last_login
        )
        
        logger.info(f"Successfully created user: {request.email}")
        
        return TokenResponse(
            access_token=access_token,
            expires_in=JWT_EXPIRE_HOURS * 3600,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/auth/login", response_model=TokenResponse)
async def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Login existing user"""
    try:
        # Verify OAuth token if provided
        if request.oauth_token:
            is_valid = await verify_oauth_token(
                request.oauth_provider, 
                request.oauth_token, 
                request.email
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OAuth token"
                )
        
        # Find user
        user_query = """
            SELECT u.user_id, u.email, u.display_name, u.org_id, u.is_active,
                   u.is_verified, u.created_at, u.last_login,
                   o.name as org_name, o.domain as org_domain
            FROM users u
            JOIN organizations o ON u.org_id = o.org_id
            WHERE u.oauth_provider = %s AND u.oauth_subject = %s
        """
        
        user_data = db.execute(user_query, (request.oauth_provider, request.oauth_subject)).fetchone()
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Update last login
        update_login = "UPDATE users SET last_login = NOW() WHERE user_id = %s"
        db.execute(update_login, (user_data.user_id,))
        db.commit()
        
        # Create access token
        token_data = {
            "user_id": str(user_data.user_id),
            "email": user_data.email,
            "org_id": str(user_data.org_id)
        }
        access_token = create_access_token(token_data)
        
        # Create response
        user_response = UserResponse(
            user_id=str(user_data.user_id),
            email=user_data.email,
            display_name=user_data.display_name,
            org_id=str(user_data.org_id),
            org_name=user_data.org_name,
            org_domain=user_data.org_domain,
            is_active=user_data.is_active,
            is_verified=user_data.is_verified,
            created_at=user_data.created_at,
            last_login=datetime.utcnow()  # Updated login time
        )
        
        logger.info(f"Successfully logged in user: {request.email}")
        
        return TokenResponse(
            access_token=access_token,
            expires_in=JWT_EXPIRE_HOURS * 3600,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        user_id=str(current_user.user_id),
        email=current_user.email,
        display_name=current_user.display_name,
        org_id=str(current_user.org_id),
        org_name=current_user.org_name,
        org_domain=current_user.org_domain,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@app.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization_info(
    org_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get organization information (admin only)"""
    # Check if user belongs to the organization
    if str(current_user.org_id) != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    org_query = """
        SELECT org_id, name, domain, subscription_tier, max_users, created_at
        FROM organizations
        WHERE org_id = %s
    """
    
    org_data = db.execute(org_query, (uuid.UUID(org_id),)).fetchone()
    
    if not org_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return OrganizationResponse(
        org_id=str(org_data.org_id),
        name=org_data.name,
        domain=org_data.domain,
        subscription_tier=org_data.subscription_tier,
        max_users=org_data.max_users,
        created_at=org_data.created_at
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
