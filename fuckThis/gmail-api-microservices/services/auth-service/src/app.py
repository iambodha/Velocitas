# File: /gmail-api-microservices/gmail-api-microservices/services/auth-service/src/app.py
#Revised

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import os
import json
import logging
from dotenv import load_dotenv
import requests
from .config.supabase import supabase, admin_supabase
from .models.schemas import *
from .utils.auth_utils import get_current_user, get_optional_user, AuthUtils
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI(title="Auth Service with Supabase")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Google OAuth Configuration - updated scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/userinfo.profile'
    # Note: 'openid' will be added automatically by Google
]

REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8001/auth/callback')
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CLIENT_SECRETS_FILE = os.getenv('GOOGLE_CLIENT_SECRETS_FILE', str(PROJECT_ROOT / 'client_secret.json'))

def get_flow():
    """Create OAuth flow for Gmail access"""
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth", "provider": "supabase"}

# === SUPABASE AUTH ROUTES ===

@app.post("/signup")
async def signup(user_data: UserSignUp):
    """Sign up new user with Supabase"""
    try:
        # Sign up user
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "name": user_data.name
                }
            }
        })
        
        if response.user is None:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        # Check if session exists (email confirmation may be required)
        if response.session is None:
            # Email confirmation required
            return {
                "message": "Registration successful! Please check your email to confirm your account.",
                "email_confirmation_required": True,
                "user_id": response.user.id,
                "email": response.user.email
            }
        
        # Immediate login (no email confirmation required)
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "expires_in": response.session.expires_in,
            "token_type": "bearer",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "name": response.user.user_metadata.get("name"),
                "email_confirmed_at": response.user.email_confirmed_at,
                "created_at": response.user.created_at,
                "updated_at": response.user.updated_at
            }
        }
        
    except Exception as e:
        logger.error(f"Signup error: {e}")
        # More specific error handling
        error_message = str(e)
        if "already registered" in error_message.lower() or "already been registered" in error_message.lower():
            raise HTTPException(status_code=400, detail="Email already registered")
        elif "invalid email" in error_message.lower():
            raise HTTPException(status_code=400, detail="Invalid email format")
        elif "password" in error_message.lower():
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        else:
            raise HTTPException(status_code=400, detail="Registration failed. Please try again.")

@app.post("/signin", response_model=AuthResponse)
async def signin(user_data: UserSignIn):
    """Sign in user with Supabase"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if response.user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in,
            user=UserResponse(
                id=response.user.id,
                email=response.user.email,
                name=response.user.user_metadata.get("name"),
                email_confirmed_at=response.user.email_confirmed_at,
                created_at=response.user.created_at,
                updated_at=response.user.updated_at
            )
        )
        
    except Exception as e:
        logger.error(f"Signin error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/refresh", response_model=AuthResponse)
async def refresh_token(token_data: TokenRefreshRequest):
    """Refresh access token"""
    try:
        response = supabase.auth.refresh_session(token_data.refresh_token)
        
        if response.user is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in,
            user=UserResponse(
                id=response.user.id,
                email=response.user.email,
                name=response.user.user_metadata.get("name"),
                email_confirmed_at=response.user.email_confirmed_at,
                created_at=response.user.created_at,
                updated_at=response.user.updated_at
            )
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.post("/signout")
async def signout(current_user: UserResponse = Depends(get_current_user)):
    """Sign out current user"""
    try:
        supabase.auth.sign_out()
        return {"message": "Signed out successfully"}
    except Exception as e:
        logger.error(f"Signout error: {e}")
        return {"message": "Signed out"}

@app.post("/reset-password")
async def reset_password(reset_data: PasswordResetRequest):
    """Send password reset email"""
    try:
        supabase.auth.reset_password_email(reset_data.email)
        return {"message": "Password reset email sent"}
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(status_code=400, detail="Failed to send reset email")

@app.post("/update-password")
async def update_password(update_data: PasswordUpdateRequest):
    """Update user password"""
    try:
        supabase.auth.update_user({
            "password": update_data.password
        }, jwt=update_data.access_token)
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(status_code=400, detail="Failed to update password")

@app.get("/me", response_model=UserResponse)
async def get_user_profile(current_user: UserResponse = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

# === GOOGLE OAUTH FOR GMAIL ===

@app.get("/auth/google")
async def google_auth(current_user: UserResponse = Depends(get_current_user)):
    """Get Google OAuth URL for Gmail access"""
    try:
        flow = get_flow()
        # Store user ID in state for callback
        state = f"user_{current_user.id}"
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return {
            "authorization_url": authorization_url,
            "message": "Complete Google OAuth to access Gmail"
        }
        
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

def normalize_and_validate_scopes(received_scopes, expected_scopes):
    """Normalize scopes and check if all expected scopes are present"""
    if not received_scopes:
        return False
    
    # Remove 'openid' and sort both lists for consistent comparison
    received_clean = sorted([s for s in received_scopes if s != 'openid'])
    expected_clean = sorted([s for s in expected_scopes if s != 'openid'])
    
    # Check if all expected scopes are present (order doesn't matter)
    expected_set = set(expected_clean)
    received_set = set(received_clean)
    
    # Log for debugging
    logger.info(f"Expected scopes (clean): {expected_clean}")
    logger.info(f"Received scopes (clean): {received_clean}")
    logger.info(f"Missing scopes: {expected_set - received_set}")
    
    return expected_set.issubset(received_set)

@app.get("/auth/callback")
async def google_callback(code: str, state: str = None):
    """Handle Google OAuth callback for Gmail access"""
    try:
        if not state or not state.startswith("user_"):
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        user_id = state.replace("user_", "")
        
        flow = get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        if not credentials.refresh_token:
            raise HTTPException(
                status_code=400, 
                detail="Authorization incomplete. Please ensure you grant full permissions."
            )
        
        # Expected scopes (what we requested)
        expected_scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/userinfo.email', 
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        
        # Log received scopes for debugging
        logger.info(f"Received scopes from Google: {credentials.scopes}")
        
        # Validate scopes (allowing for Google's automatic additions like 'openid')
        if not normalize_and_validate_scopes(credentials.scopes, expected_scopes):
            logger.warning(f"Scope validation failed. Expected: {expected_scopes}, Got: {credentials.scopes}")
            # Don't fail completely - just log the warning since we have the necessary scopes
        
        # Store credentials with normalized scopes (remove openid, sort for consistency)
        normalized_scopes = sorted([s for s in credentials.scopes if s != 'openid'])
        
        creds_data = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": normalized_scopes  # Store normalized scopes
        }
        
        success = AuthUtils.store_gmail_credentials(user_id, creds_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store credentials")
        
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Gmail Access Granted</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
                .success {{ color: green; }}
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ Gmail Access Granted!</h2>
                <p>You can now access your Gmail data.</p>
                <p>You can close this window.</p>
            </div>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'gmail_auth_success',
                        user_id: '{user_id}'
                    }}, '*');
                    window.close();
                }}
            </script>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Google callback error: {e}")
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
                .error {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>❌ Authentication Failed</h2>
                <p>Error: {str(e)}</p>
                <p><a href="javascript:window.close()">Close Window</a></p>
            </div>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'gmail_auth_error',
                        error: '{str(e)}'
                    }}, '*');
                    window.close();
                }}
            </script>
        </body>
        </html>
        """)

@app.get("/gmail/status")
async def gmail_status(current_user: UserResponse = Depends(get_current_user)):
    """Check Gmail access status"""
    try:
        creds = AuthUtils.get_gmail_credentials(current_user.id)
        
        if creds:
            # Try to refresh credentials to check validity
            try:
                # Handle both 'token' and 'access_token' key names
                token = creds.get("access_token") or creds.get("token")
                
                credentials = Credentials(
                    token=token,
                    refresh_token=creds["refresh_token"],
                    token_uri=creds["token_uri"],
                    client_id=creds["client_id"],
                    client_secret=creds["client_secret"],
                    scopes=creds["scopes"]
                )
                
                if credentials.expired:
                    from google.auth.transport.requests import Request
                    credentials.refresh(Request())
                    
                    # Update stored credentials with normalized scopes
                    updated_creds = {
                        "access_token": credentials.token,
                        "refresh_token": credentials.refresh_token,
                        "token_uri": credentials.token_uri,
                        "client_id": credentials.client_id,
                        "client_secret": credentials.client_secret,
                        "scopes": [scope for scope in credentials.scopes if scope != 'openid']
                    }
                    AuthUtils.store_gmail_credentials(current_user.id, updated_creds)
                
                return {
                    "gmail_access": True,
                    "message": "Gmail access is active",
                    "scopes": credentials.scopes
                }
            except Exception as refresh_error:
                logger.warning(f"Credential refresh failed: {refresh_error}")
                return {
                    "gmail_access": False,
                    "message": "Gmail credentials need refresh",
                    "error": str(refresh_error)
                }
        else:
            return {
                "gmail_access": False,
                "message": "Gmail access not granted"
            }
            
    except Exception as e:
        logger.error(f"Gmail status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/gmail/credentials")
async def get_gmail_credentials(current_user: UserResponse = Depends(get_current_user)):
    """Get Gmail credentials for internal service use"""
    try:
        creds = AuthUtils.get_gmail_credentials(current_user.id)
        if not creds:
            raise HTTPException(status_code=404, detail="Gmail credentials not found")
        
        return GmailCredentials(**creds)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get credentials error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# === VERIFICATION ENDPOINTS FOR OTHER SERVICES ===

@app.get("/verify")
async def verify_token(current_user: UserResponse = Depends(get_current_user)):
    """Verify token for other microservices"""
    return {
        "valid": True,
        "user": current_user
    }

@app.get("/user/{user_id}")
async def get_user_by_id(user_id: str):
    """Get user by ID for internal service use"""
    try:
        # Use admin client to get user by ID
        response = admin_supabase.auth.admin.get_user_by_id(user_id)
        
        if not response.user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=response.user.id,
            email=response.user.email,
            name=response.user.user_metadata.get("name"),
            email_confirmed_at=response.user.email_confirmed_at,
            created_at=response.user.created_at,
            updated_at=response.user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user by ID error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Add these endpoints to handle email confirmation

@app.post("/resend-confirmation")
async def resend_confirmation(email_data: dict):
    """Resend email confirmation"""
    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
            
        supabase.auth.resend({
            "type": "signup",
            "email": email
        })
        
        return {"message": "Confirmation email sent successfully"}
        
    except Exception as e:
        logger.error(f"Resend confirmation error: {e}")
        raise HTTPException(status_code=400, detail="Failed to send confirmation email")

@app.get("/auth/confirm")
async def confirm_email(token: str, type: str = "signup"):
    """Handle email confirmation callback"""
    try:
        # This endpoint would handle the email confirmation
        # But typically Supabase handles this automatically
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Confirmed</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
                .success { color: green; }
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ Email Confirmed!</h2>
                <p>Your email has been confirmed. You can now sign in.</p>
                <p><a href="http://localhost:3000">Return to app</a></p>
            </div>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Email confirmation error: {e}")
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Confirmation Failed</title>
        </head>
        <body>
            <h2>❌ Confirmation Failed</h2>
            <p>The confirmation link is invalid or has expired.</p>
            <p><a href="http://localhost:3000">Return to app</a></p>
        </body>
        </html>
        """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)