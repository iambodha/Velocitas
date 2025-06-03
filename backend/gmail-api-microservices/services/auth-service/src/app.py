# File: /gmail-api-microservices/gmail-api-microservices/services/auth-service/src/app.py
#Tested

from fastapi import FastAPI, Request, HTTPException, Header
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
from .database.db import get_db
from .models.user import User
from .utils.jwt_utils import create_session_token, verify_session_token
from .handlers.auth import SecureCredentialManager
from pathlib import Path

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
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8080/callback')
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
async def callback(request: Request):
    """Handle OAuth callback"""
    flow = get_flow()
    
    try:
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        
        # Extract state (session_id) from the callback
        state = request.query_params.get('state')
        session_id = pending_auth.get(state)
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Invalid or expired auth session")
        
        # Get user info from Google
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        google_user_id = user_info['id']
        user_email = user_info.get('email', 'unknown')
        user_name = user_info.get('name', '')
        
        # Check if user exists (returning user)
        existing_user = credential_manager.get_user_by_google_id(google_user_id)
        is_new_user = existing_user is None
        
        # Save user and credentials to database
        user_id = credential_manager.save_user_and_credentials(
            google_user_id, user_email, user_name, credentials
        )
        
        # Create session token
        session_token = create_session_token(user_id)
        
        # Clean up pending auth
        pending_auth.pop(state, None)
        
        # Notify other services about user login
        if is_new_user:
            # Register with email sync service or other services
            pass
        
        # Return HTML page that communicates with parent window
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Success</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%);
                    color: #e0e0e0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    text-align: center;
                }}
                .success-message {{
                    background: rgba(39, 174, 96, 0.2);
                    border: 1px solid rgba(39, 174, 96, 0.3);
                    color: #2ecc71;
                    padding: 24px;
                    border-radius: 8px;
                    max-width: 400px;
                }}
            </style>
        </head>
        <body>
            <div class="success-message">
                <h2>✅ Authentication Successful!</h2>
                <p>You can now close this window.</p>
                <p>Email: {user_email}</p>
            </div>
            <script>
                // Send authentication data to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GMAIL_AUTH_SUCCESS',
                        token: '{session_token}',
                        user_email: '{user_email}',
                        user_id: '{user_id}'
                    }}, '*');
                    
                    // Close this window after a short delay
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                }}
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_response)
        
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed</title>
        </head>
        <body>
            <div class="error-message">
                <h2>❌ Authentication Failed</h2>
                <p>{str(e)}</p>
                <p>Please close this window and try again.</p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=error_html)

@app.get("/status")
async def status(x_user_id: str = Header(None)):
    """Check authentication status for current user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    creds = credential_manager.load_credentials(x_user_id)
    
    with get_db() as db:
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

@app.post("/logout")
async def logout(x_user_id: str = Header(None)):
    """Logout current user and clear credentials"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    credential_manager.deactivate_user(x_user_id)
    return {"success": True, "message": "Logged out successfully"}

@app.get("/credentials")
async def get_credentials(x_user_id: str = Header(None)):
    """Get user credentials for other services"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)