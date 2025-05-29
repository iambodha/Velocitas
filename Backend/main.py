from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import json
import base64
import uuid
import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import redis
import jwt
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# IMPORTANT: Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI(
    title="Multi-User Gmail API",
    description="Gmail API with support for multiple users and concurrent requests",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
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
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Thread pool for handling Gmail API calls
executor = ThreadPoolExecutor(max_workers=10)

# Fallback in-memory storage
user_credentials: Dict[str, dict] = {}
pending_auth: Dict[str, str] = {}  # state -> session_id

# Initialize Redis client
def create_redis_client():
    """Create Redis client with error handling"""
    try:
        # Fixed: Removed deprecated retry_on_timeout parameter
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30
        )
        # Test connection
        client.ping()
        print("✅ Redis connection successful")
        return client
    except redis.ConnectionError:
        print("❌ Redis connection failed - using in-memory storage")
        return None

redis_client = create_redis_client()

class CredentialManager:
    """Enhanced credential manager with Redis support and fallback"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
    
    def save_credentials(self, user_id: str, creds: Credentials):
        """Save credentials with Redis persistence"""
        creds_dict = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if self.redis:
            try:
                # Store in Redis with 24-hour expiration
                self.redis.setex(
                    f"creds:{user_id}", 
                    timedelta(hours=24), 
                    json.dumps(creds_dict)
                )
            except Exception as e:
                print(f"Redis save error: {e}, falling back to memory")
                user_credentials[user_id] = creds_dict
        else:
            # Fallback to in-memory
            user_credentials[user_id] = creds_dict
    
    def load_credentials(self, user_id: str) -> Optional[Credentials]:
        """Load credentials from Redis or memory"""
        creds_data = None
        
        if self.redis:
            try:
                # Load from Redis
                data = self.redis.get(f"creds:{user_id}")
                if data:
                    creds_data = json.loads(data)
            except Exception as e:
                print(f"Redis load error: {e}, trying memory")
                creds_data = user_credentials.get(user_id)
        else:
            # Fallback to in-memory
            creds_data = user_credentials.get(user_id)
        
        if not creds_data:
            return None
        
        try:
            creds = Credentials(
                token=creds_data['token'],
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data['token_uri'],
                client_id=creds_data['client_id'],
                client_secret=creds_data['client_secret'],
                scopes=creds_data['scopes']
            )
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(GoogleRequest())
                self.save_credentials(user_id, creds)
            
            return creds
        except Exception as e:
            print(f"Error loading credentials for user {user_id}: {e}")
            return None
    
    def delete_credentials(self, user_id: str):
        """Delete credentials from Redis and memory"""
        if self.redis:
            try:
                self.redis.delete(f"creds:{user_id}")
            except Exception as e:
                print(f"Redis delete error: {e}")
        
        user_credentials.pop(user_id, None)
    
    def get_active_users(self) -> List[str]:
        """Get list of users with stored credentials"""
        active_users = set()
        
        if self.redis:
            try:
                keys = self.redis.keys("creds:*")
                redis_users = [key.replace("creds:", "") for key in keys]
                active_users.update(redis_users)
            except Exception as e:
                print(f"Redis keys error: {e}")
        
        # Also check memory
        active_users.update(user_credentials.keys())
        
        return list(active_users)
    
    def cache_emails(self, user_id: str, emails: List[dict], ttl: int = 300):
        """Cache email list for 5 minutes"""
        if self.redis:
            try:
                self.redis.setex(
                    f"emails:{user_id}", 
                    ttl, 
                    json.dumps(emails)
                )
            except Exception as e:
                print(f"Cache emails error: {e}")
    
    def get_cached_emails(self, user_id: str) -> Optional[List[dict]]:
        """Get cached emails if available"""
        if self.redis:
            try:
                data = self.redis.get(f"emails:{user_id}")
                if data:
                    return json.loads(data)
            except Exception as e:
                print(f"Get cached emails error: {e}")
        return None

# Initialize credential manager
credential_manager = CredentialManager(redis_client)

def create_session_token(user_id: str) -> str:
    """Create JWT session token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_session_token(token: str) -> Optional[str]:
    """Verify JWT session token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user(authorization: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> str:
    """Dependency to get current user from JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    user_id = verify_session_token(authorization.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_id

def get_flow():
    """Create OAuth flow"""
    return Flow.from_client_secrets_file(
        CLIENT_SECRET_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

async def gmail_api_call(func, *args, **kwargs):
    """Execute Gmail API call in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args, **kwargs)

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multi-User Gmail API", 
        "version": "1.0.0",
        "redis_connected": redis_client is not None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "connected" if redis_client else "disconnected"
    if redis_client:
        try:
            redis_client.ping()
        except:
            redis_status = "error"
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "active_users": len(credential_manager.get_active_users())
    }

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
        user_id = user_info['id']
        user_email = user_info.get('email', 'unknown')
        
        # Save credentials for this user
        credential_manager.save_credentials(user_id, credentials)
        
        # Create session token
        session_token = create_session_token(user_id)
        
        # Clean up pending auth
        pending_auth.pop(state, None)
        
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
                }} else {{
                    // Fallback: redirect to main app with token as hash
                    window.location.href = 'http://localhost:8080/frontend.html#token={session_token}&email={user_email}';
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
                .error-message {{
                    background: rgba(231, 76, 60, 0.2);
                    border: 1px solid rgba(231, 76, 60, 0.3);
                    color: #e74c3c;
                    padding: 24px;
                    border-radius: 8px;
                    max-width: 400px;
                }}
            </style>
        </head>
        <body>
            <div class="error-message">
                <h2>❌ Authentication Failed</h2>
                <p>{str(e)}</p>
                <p>Please close this window and try again.</p>
            </div>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GMAIL_AUTH_ERROR',
                        error: '{str(e)}'
                    }}, '*');
                    
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                }}
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=error_html)

@app.get("/status")
async def status(user_id: str = Depends(get_current_user)):
    """Check authentication status for current user"""
    creds = credential_manager.load_credentials(user_id)
    if creds and creds.valid:
        return {
            "authenticated": True, 
            "message": "Ready to access Gmail", 
            "user_id": user_id
        }
    else:
        return {
            "authenticated": False, 
            "message": "Not authenticated", 
            "user_id": user_id
        }

@app.post("/logout")
async def logout(user_id: str = Depends(get_current_user)):
    """Logout current user and clear credentials"""
    credential_manager.delete_credentials(user_id)
    return {"success": True, "message": "Logged out successfully"}

@app.get("/emails")
async def get_emails(
    limit: int = 10, 
    use_cache: bool = True,
    user_id: str = Depends(get_current_user)
):
    """Get list of emails for current user with caching"""
    
    # Check cache first
    if use_cache:
        cached_emails = credential_manager.get_cached_emails(user_id)
        if cached_emails:
            return {
                "emails": cached_emails, 
                "user_id": user_id, 
                "cached": True,
                "count": len(cached_emails)
            }
    
    # Load credentials
    creds = credential_manager.load_credentials(user_id)
    if not creds or not creds.valid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        def fetch_emails():
            service = build('gmail', 'v1', credentials=creds)
            
            # Get list of messages
            results = service.users().messages().list(
                userId='me', 
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            
            email_list = []
            for message in messages:
                try:
                    # Get message details
                    msg = service.users().messages().get(
                        userId='me', 
                        id=message['id']
                    ).execute()
                    
                    # Extract headers
                    headers = msg['payload'].get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                    
                    email_list.append({
                        'id': message['id'],
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'snippet': msg.get('snippet', '')
                    })
                except Exception as e:
                    print(f"Error processing message {message['id']}: {e}")
                    continue
            
            return email_list
        
        email_list = await gmail_api_call(fetch_emails)
        
        # Cache the results
        if email_list:
            credential_manager.cache_emails(user_id, email_list)
        
        return {
            "emails": email_list, 
            "user_id": user_id, 
            "cached": False,
            "count": len(email_list)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")

@app.get("/email/{email_id}")
async def get_email(email_id: str, user_id: str = Depends(get_current_user)):
    """Get specific email content for current user"""
    creds = credential_manager.load_credentials(user_id)
    if not creds or not creds.valid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        def fetch_email():
            service = build('gmail', 'v1', credentials=creds)
            
            # Get message
            message = service.users().messages().get(
                userId='me', 
                id=email_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
            
            # Extract body
            def extract_body(payload):
                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            if part['body'].get('data'):
                                data = part['body']['data']
                                body = base64.urlsafe_b64decode(data).decode('utf-8')
                                break
                        elif part['mimeType'] == 'text/html' and not body:
                            if part['body'].get('data'):
                                data = part['body']['data']
                                body = base64.urlsafe_b64decode(data).decode('utf-8')
                else:
                    if payload['body'].get('data'):
                        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                return body
            
            body = extract_body(message['payload'])
            
            return {
                "id": email_id,
                "subject": subject,
                "sender": sender,
                "to": to,
                "date": date,
                "body": body,
                "snippet": message.get('snippet', ''),
                "user_id": user_id
            }
        
        email_data = await gmail_api_call(fetch_email)
        return email_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch email: {str(e)}")

# Admin endpoints

@app.get("/admin/users")
async def get_active_users():
    """Get list of active users"""
    active_users = credential_manager.get_active_users()
    return {
        "active_users": active_users,
        "count": len(active_users)
    }

@app.get("/admin/redis/info")
async def redis_info():
    """Get Redis server information"""
    if not redis_client:
        return {"error": "Redis not available"}
    
    try:
        info = redis_client.info()
        return {
            "connected_clients": info.get('connected_clients'),
            "used_memory_human": info.get('used_memory_human'),
            "total_commands_processed": info.get('total_commands_processed'),
            "uptime_in_seconds": info.get('uptime_in_seconds'),
            "redis_version": info.get('redis_version')
        }
    except Exception as e:
        return {"error": f"Failed to get Redis info: {str(e)}"}

@app.delete("/admin/user/{user_id}")
async def delete_user(user_id: str):
    """Delete a specific user's credentials (admin endpoint)"""
    credential_manager.delete_credentials(user_id)
    return {"success": True, "message": f"User {user_id} deleted"}

# Fixed: Proper way to run with reload
def run_server():
    """Run the server with proper configuration"""
    import uvicorn
    uvicorn.run(
        "main:app",  # Use import string format
        host="0.0.0.0", 
        port=8080,
        reload=True  # Now works properly with import string
    )

if __name__ == "__main__":
    run_server()