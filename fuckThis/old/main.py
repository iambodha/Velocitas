from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
import os
import json
import secrets
from typing import Optional
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging

# Import your existing services
from services import SecureGmailClient

app = FastAPI(title="Velocitas API", version="1.0.0")

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'openid', 'email', 'profile']
CLIENT_SECRETS_FILE = os.getenv('GMAIL_CLIENT_SECRET_PATH', 'client_secrets.json')
REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://127.0.0.1:5000/callback')

# In-memory session store (use Redis/database in production)
auth_sessions = {}

security = HTTPBearer()

class GoogleOAuthHandler:
    def __init__(self):
        self.client_secrets_file = CLIENT_SECRETS_FILE
        
    def create_auth_url(self, state: str) -> str:
        """Create Google OAuth authorization URL"""
        try:
            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'
            )
            
            return auth_url
        except Exception as e:
            logger.error(f"Error creating auth URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to create auth URL")
    
    def exchange_code_for_tokens(self, code: str, state: str) -> dict:
        """Exchange authorization code for tokens"""
        try:
            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
                state=state
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user info
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'credentials_json': credentials.to_json()
            }
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

oauth_handler = GoogleOAuthHandler()

@app.get("/")
async def root():
    return {"message": "Velocitas API - Gmail OAuth Integration"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/auth/login")
async def login():
    """Initiate Google OAuth login"""
    state = secrets.token_urlsafe(32)
    auth_sessions[state] = {"status": "pending"}
    
    auth_url = oauth_handler.create_auth_url(state)
    return {"auth_url": auth_url, "state": state}

@app.get("/auth/callback")
async def auth_callback(code: str, state: str):
    """Handle OAuth callback"""
    if state not in auth_sessions:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    try:
        token_data = oauth_handler.exchange_code_for_tokens(code, state)
        
        # Store user session
        session_token = secrets.token_urlsafe(32)
        auth_sessions[session_token] = {
            "user_email": token_data["email"],
            "user_name": token_data["name"],
            "credentials": token_data["credentials_json"],
            "status": "authenticated"
        }
        
        # Clean up state session
        del auth_sessions[state]
        
        return {
            "message": "Authentication successful",
            "session_token": session_token,
            "user": {
                "email": token_data["email"],
                "name": token_data["name"],
                "picture": token_data["picture"]
            }
        }
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

def get_current_user(token: str = Depends(security)):
    """Get current authenticated user"""
    session_token = token.credentials
    
    if session_token not in auth_sessions:
        raise HTTPException(status_code=401, detail="Invalid session token")
    
    session = auth_sessions[session_token]
    if session.get("status") != "authenticated":
        raise HTTPException(status_code=401, detail="Session not authenticated")
    
    return session

@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "email": current_user["user_email"],
        "name": current_user["user_name"]
    }

@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout current user"""
    # Find and remove session
    for token, session in list(auth_sessions.items()):
        if session.get("user_email") == current_user["user_email"]:
            del auth_sessions[token]
            break
    
    return {"message": "Logged out successfully"}

@app.get("/gmail/messages")
async def get_gmail_messages(
    max_results: int = 10,
    query: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get Gmail messages for authenticated user"""
    try:
        # Create credentials from stored JSON
        creds_data = json.loads(current_user["credentials"])
        credentials = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # Use your existing SecureGmailClient with the credentials
        client = SecureGmailClient(user_id=current_user["user_email"])
        # Override the authentication to use existing credentials
        client.service = build('gmail', 'v1', credentials=credentials)
        
        message_ids = client.list_messages_securely(
            max_results=min(max_results, 50),
            query=query
        )
        
        return {
            "message_ids": message_ids,
            "count": len(message_ids)
        }
    except Exception as e:
        logger.error(f"Error fetching Gmail messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch Gmail messages")

@app.get("/gmail/messages/{message_id}")
async def get_gmail_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific Gmail message"""
    try:
        # Create credentials from stored JSON
        creds_data = json.loads(current_user["credentials"])
        credentials = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # Use your existing SecureGmailClient
        client = SecureGmailClient(user_id=current_user["user_email"])
        # Override the authentication to use existing credentials
        from googleapiclient.discovery import build
        client.service = build('gmail', 'v1', credentials=credentials)
        
        email_data = client.get_email_securely(
            message_id,
            required_fields=['id', 'subject', 'from', 'date', 'snippet']
        )
        
        if not email_data:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return email_data
    except Exception as e:
        logger.error(f"Error fetching Gmail message: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch Gmail message")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)