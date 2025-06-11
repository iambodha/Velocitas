# File: /gmail-api-microservices/gmail-api-microservices/services/auth-service/src/app.py
#Tested

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import json
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
import requests
import logging
from .database.db import get_db, SessionLocal
from .models.user import User
from .utils.jwt_utils import create_session_token, verify_session_token
from .handlers.auth import SecureCredentialManager
from pathlib import Path
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# IMPORTANT: Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI(
    title="Auth Service",
    description="Authentication service for Gmail API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Configuration
CLIENT_SECRET_PATH = os.getenv('GOOGLE_CLIENT_SECRET_PATH', '../client_secret.json')
# Change this to use the gateway URL since that's where the callback route is
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8080/callback')  # Keep as 8080 for gateway
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', 
    'https://www.googleapis.com/auth/userinfo.email', 
    'openid'
]

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
CLIENT_SECRETS_FILE = os.getenv('GOOGLE_CLIENT_SECRETS_FILE', str(PROJECT_ROOT / 'client_secret.json'))

# Initialize credential manager
credential_manager = SecureCredentialManager()

# Fallback in-memory storage for pending auth
pending_auth = {}

def get_flow():
    """Create OAuth flow"""
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

# Dependency to get database session
def get_database_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth"}

@app.get("/auth")
async def auth():
    """Get authorization URL for new user"""
    session_id = str(uuid.uuid4())
    flow = get_flow()
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=session_id
    )
    
    # Store pending auth session
    pending_auth[state] = session_id
    
    return {
        "authorization_url": authorization_url,
        "session_id": session_id
    }
@app.get("/callback")
async def callback(code: str, state: str = None, db: Session = Depends(get_database_session)):
    """Handle OAuth callback and store credentials"""
    try:
        # Validate state parameter if needed
        if state and state in pending_auth:
            session_id = pending_auth.pop(state)
            logger.info(f"Processing callback for session {session_id}")
        
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Set the state if provided
        if state:
            flow.state = state
        
        # Exchange authorization code for credentials
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Log credential details for debugging
        logger.info(f"Received credentials - has_refresh_token: {bool(credentials.refresh_token)}")
        logger.info(f"Token expires at: {credentials.expiry}")
        
        # Validate that we have all required credential components
        if not credentials.refresh_token:
            logger.error("No refresh token received - user may need to re-authorize with consent")
            raise HTTPException(
                status_code=400, 
                detail="Authorization incomplete. Please ensure you grant full permissions and try again."
            )
        
        # Get user info from Google
        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'},
            timeout=10
        )
        
        if userinfo_response.status_code != 200:
            logger.error(f"Failed to get user info: {userinfo_response.status_code}")
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
        user_info = userinfo_response.json()
        email = user_info.get("email")
        name = user_info.get("name", "")
        
        if not email:
            logger.error("No email in user info response")
            raise HTTPException(status_code=400, detail="Failed to get user email")
        
        # Check if user exists, create if not
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=name, is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {email}")
        else:
            # Update user info and ensure active
            user.name = name
            user.is_active = True
            db.commit()
            logger.info(f"Updated existing user: {email}")
        
        # Store credentials with validation
        try:
            credential_manager.store_credentials(str(user.id), credentials)
            logger.info(f"Stored credentials for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            raise HTTPException(status_code=500, detail="Failed to store credentials")
        
        # Verify credentials were stored properly
        stored_creds = credential_manager.load_credentials(str(user.id))
        if not stored_creds:
            logger.error(f"Could not load stored credentials for user {user.id}")
            raise HTTPException(status_code=500, detail="Failed to verify stored credentials")
        
        if not stored_creds.refresh_token:
            logger.error(f"Stored credentials missing refresh token for user {user.id}")
            raise HTTPException(status_code=500, detail="Stored credentials incomplete")
        
        # Generate session token
        session_token = create_session_token(str(user.id))
        
        logger.info(f"Successfully authenticated user {email} with refresh token")
        
        return {
            "message": "Authentication successful",
            "user_id": str(user.id),
            "email": email,
            "name": name,
            "session_token": session_token,
            "has_refresh_token": bool(stored_creds.refresh_token)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Callback error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@app.get("/status")
async def status(x_user_id: str = Header(None), db: Session = Depends(get_database_session)):
    """Check authentication status for current user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        creds = credential_manager.load_credentials(x_user_id)
        user = db.query(User).filter(User.id == x_user_id).first()
        
        if creds and creds.valid and user:
            return {
                "authenticated": True, 
                "message": "Ready to access Gmail", 
                "user_id": x_user_id,
                "email": user.email,
                "name": user.name
            }
        else:
            return {
                "authenticated": False, 
                "message": "Not authenticated", 
                "user_id": x_user_id
            }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/logout")
async def logout(x_user_id: str = Header(None)):
    """Logout current user and clear credentials"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        credential_manager.deactivate_user(x_user_id)
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/credentials")
async def get_credentials(x_user_id: str = Header(None)):
    """Get user credentials for other services"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        creds = credential_manager.load_credentials(x_user_id)
        
        if not creds or not creds.valid:
            raise HTTPException(status_code=401, detail="Invalid or expired credentials")
        
        return {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
    except Exception as e:
        logger.error(f"Credentials error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/verify")
async def verify_token(request: Request, db: Session = Depends(get_database_session)):
    """Verify token and return user info"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = auth_header.split("Bearer ")[1]
    
    try:
        # First try to verify as JWT token
        user_id = verify_session_token(token)
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.is_active:  # Add active check
                return {
                    "authenticated": True,
                    "user_id": user.id,
                    "email": user.email,
                    "name": user.name
                }
        
        # If JWT verification fails, try Google OAuth token verification
        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10  # Add timeout
        )
        
        if userinfo_response.status_code == 200:
            user_info = userinfo_response.json()
            email = user_info.get("email")
            
            if email:
                user = db.query(User).filter(User.email == email, User.is_active == True).first()
                if user:
                    return {
                        "authenticated": True,
                        "user_id": user.id,
                        "email": user.email,
                        "name": user.name
                    }
        
        raise HTTPException(status_code=401, detail="Invalid token")
        
    except requests.RequestException as e:
        logger.error(f"Google API request failed: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")
@app.get("/authorize")
async def authorize():
    """Redirect user to Google authorization page"""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Add offline access to get refresh token
        authorization_url, state = flow.authorization_url(
            access_type='offline',  # This is crucial for getting refresh token
            prompt='consent',       # Force consent screen to ensure refresh token
            include_granted_scopes='true'
        )
        
        logger.info(f"Generated authorization URL: {authorization_url}")
        return {"authorization_url": authorization_url, "state": state}
    except Exception as e:
        logger.error(f"Error generating authorization URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

@app.post("/reauth")
async def force_reauth(x_user_id: str = Header(...), db: Session = Depends(get_database_session)):
    """Force re-authentication for a user (clears stored credentials)"""
    try:
        user = db.query(User).filter(User.id == x_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Clear stored credentials
        user.encrypted_credentials = None
        db.commit()
        
        logger.info(f"Cleared credentials for user {x_user_id} - re-authentication required")
        
        return {
            "message": "Credentials cleared. Please re-authenticate.",
            "requires_auth": True,
            "auth_url": "/authorize"
        }
        
    except Exception as e:
        logger.error(f"Error clearing credentials for user {x_user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear credentials")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Fixed: Use port 8001