from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import json
import base64
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import asyncio
from contextlib import asynccontextmanager
import asyncpg
from pydantic import BaseModel, EmailStr
import jwt
from passlib.context import CryptContext
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# IMPORTANT: Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bodha@localhost:5432/email_db")
CLIENT_SECRET_PATH = '../client_secret.json'
REDIRECT_URI = 'http://localhost:8080/callback'
FRONTEND_URL = 'http://localhost:3000/frontend.html'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/userinfo.email', 'openid']
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None

class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool

class EmailResponse(BaseModel):
    id: str
    subject: str
    sender: str
    date: str
    snippet: str
    thread_id: Optional[str]

class EmailDetailResponse(BaseModel):
    id: str
    subject: str
    sender: str
    to: str
    date: str
    body: str
    snippet: str
    thread_id: Optional[str]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Database connection pool
class Database:
    pool: Optional[asyncpg.Pool] = None

db = Database()

async def init_db():
    """Initialize database connection pool"""
    db.pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=20,
        command_timeout=60
    )
    logger.info("Database connection pool initialized")

async def close_db():
    """Close database connection pool"""
    if db.pool:
        await db.pool.close()
        logger.info("Database connection pool closed")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Utility functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user(user_id: str = Depends(verify_token)) -> Dict[str, Any]:
    """Get current user from database"""
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT user_id, email, display_name, created_at, last_login, is_active FROM users WHERE user_id = $1",
            uuid.UUID(user_id)
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return dict(user)

def get_flow():
    """Get Google OAuth flow"""
    return Flow.from_client_secrets_file(
        CLIENT_SECRET_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

async def save_user_credentials(user_id: str, credentials: Credentials):
    """Save user's OAuth credentials to database"""
    creds_dict = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users 
            SET oauth_credentials = $2, last_login = NOW()
            WHERE user_id = $1
            """,
            uuid.UUID(user_id), json.dumps(creds_dict)
        )

async def load_user_credentials(user_id: str) -> Optional[Credentials]:
    """Load user's OAuth credentials from database"""
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT oauth_credentials FROM users WHERE user_id = $1",
            uuid.UUID(user_id)
        )
        
        if not row or not row['oauth_credentials']:
            return None
        
        try:
            creds_data = json.loads(row['oauth_credentials'])
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
                # Save updated credentials
                await save_user_credentials(user_id, creds)
            
            return creds
        except Exception as e:
            logger.error(f"Error loading credentials for user {user_id}: {e}")
            return None

# API Endpoints

@app.get("/")
async def root():
    return {"message": "Gmail API Multi-User Backend", "status": "running"}

@app.get("/test")
async def test():
    return {"message": "Backend is working!", "status": "ok"}

@app.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    user_id = str(uuid.uuid4())
    
    async with db.pool.acquire() as conn:
        try:
            # Check if user already exists
            existing = await conn.fetchrow(
                "SELECT user_id FROM users WHERE email = $1",
                user_data.email
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Create default organization for single-user setup
            # In a real multi-tenant setup, you'd handle org assignment differently
            org_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO organizations (org_id, name, domain, encryption_key_id, settings)
                VALUES ($1, $2, $3, $4, $5)
                """,
                uuid.UUID(org_id), f"Personal - {user_data.email}", 
                user_data.email.split('@')[1], "default-key", json.dumps({})  # Convert dict to JSON string
            )
            
            # Insert new user
            await conn.execute(
                """
                INSERT INTO users (user_id, org_id, email, oauth_provider, oauth_subject, display_name, preferences)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                uuid.UUID(user_id), uuid.UUID(org_id), user_data.email, 
                'google', user_data.email, user_data.display_name, json.dumps({})  # Convert dict to JSON string
            )
            
            # Fetch created user
            user = await conn.fetchrow(
                "SELECT user_id, email, display_name, created_at, last_login, is_active FROM users WHERE user_id = $1",
                uuid.UUID(user_id)
            )
            
            return UserResponse(**dict(user), user_id=str(user['user_id']))
            
        except asyncpg.UniqueViolationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

@app.post("/login", response_model=TokenResponse)
async def login_user(email: EmailStr):
    """Login user and return JWT token"""
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT user_id, email, is_active FROM users WHERE email = $1",
            email
        )
        
        if not user or not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials or user inactive"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user['user_id'])}, expires_delta=access_token_expires
        )
        
        return TokenResponse(access_token=access_token, token_type="bearer")

@app.get("/auth")
async def auth(user_id: str = Depends(verify_token)):
    """Get authorization URL for current user"""
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=user_id  # Pass user_id in state
    )
    
    return {
        "authorization_url": authorization_url,
        "state": state
    }

@app.get("/callback")
async def callback(request: Request):
    """Handle OAuth callback and store credentials"""
    flow = get_flow()
    
    try:
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        
        # Get user_id from state parameter
        url_params = dict(request.query_params)
        user_id = url_params.get('state')
        
        if not user_id:
            return RedirectResponse(url=f"{FRONTEND_URL}?auth=error&message=Invalid state parameter")
        
        # Save credentials for the user
        await save_user_credentials(user_id, credentials)
        
        # Get user info from Google to verify
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        # Update user info in database
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users 
                SET display_name = COALESCE($2, display_name), 
                    last_login = NOW(),
                    is_verified = true
                WHERE user_id = $1
                """,
                uuid.UUID(user_id), user_info.get('name')
            )
        
        # Redirect to frontend with success parameter
        return RedirectResponse(url=f"{FRONTEND_URL}?auth=success")
    
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}?auth=error&message={str(e)}")

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(**current_user, user_id=str(current_user['user_id']))

@app.get("/status")
async def status(user_id: str = Depends(verify_token)):
    """Check authentication status for current user"""
    creds = await load_user_credentials(user_id)
    if creds and creds.valid:
        return {"authenticated": True, "message": "Ready to access Gmail"}
    else:
        return {"authenticated": False, "message": "Gmail not connected"}

@app.post("/logout")
async def logout(user_id: str = Depends(verify_token)):
    """Logout by removing stored credentials"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET oauth_credentials = NULL WHERE user_id = $1",
                uuid.UUID(user_id)
            )
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during logout: {str(e)}")

@app.get("/emails", response_model=List[EmailResponse])
async def get_emails(limit: int = 10, user_id: str = Depends(verify_token)):
    """Get list of emails for current user"""
    creds = await load_user_credentials(user_id)
    if not creds or not creds.valid:
        raise HTTPException(status_code=401, detail="Gmail not connected")
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # Get list of messages
        results = service.users().messages().list(
            userId='me', 
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        
        email_list = []
        for message in messages:
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
            
            email_data = EmailResponse(
                id=message['id'],
                subject=subject,
                sender=sender,
                date=date,
                snippet=msg.get('snippet', ''),
                thread_id=msg.get('threadId')
            )
            email_list.append(email_data)
            
            # Store email in database for future reference
            await store_email_in_db(user_id, message['id'], msg)
        
        return email_list
    
    except Exception as e:
        logger.error(f"Error fetching emails for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/email/{email_id}", response_model=EmailDetailResponse)
async def get_email(email_id: str, user_id: str = Depends(verify_token)):
    """Get specific email content"""
    creds = await load_user_credentials(user_id)
    if not creds or not creds.valid:
        raise HTTPException(status_code=401, detail="Gmail not connected")
    
    try:
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
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                    elif part['mimeType'] == 'text/html':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                if payload['body'].get('data'):
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            return body
        
        body = extract_body(message['payload'])
        
        # Store/update email in database
        await store_email_in_db(user_id, email_id, message)
        
        return EmailDetailResponse(
            id=email_id,
            subject=subject,
            sender=sender,
            to=to,
            date=date,
            body=body,
            snippet=message.get('snippet', ''),
            thread_id=message.get('threadId')
        )
    
    except Exception as e:
        logger.error(f"Error fetching email {email_id} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def store_email_in_db(user_id: str, email_id: str, message_data: Dict[str, Any]):
    """Store email data in database for caching and future processing"""
    try:
        async with db.pool.acquire() as conn:
            # Get user's org_id
            user_data = await conn.fetchrow(
                "SELECT org_id FROM users WHERE user_id = $1",
                uuid.UUID(user_id)
            )
            
            if not user_data:
                return
            
            # Extract basic info from message
            headers = message_data['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), None)
            
            # Convert date string to timestamp
            received_at = datetime.now()  # Fallback
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(date_str)
                except:
                    pass
            
            # Calculate email size (rough estimate)
            email_size = len(json.dumps(message_data).encode('utf-8'))
            
            # Check if email already exists
            existing = await conn.fetchrow(
                "SELECT email_id FROM emails WHERE external_id = $1 AND user_id = $2",
                email_id, uuid.UUID(user_id)
            )
            
            if not existing:
                # Insert new email
                await conn.execute(
                    """
                    INSERT INTO emails (
                        user_id, org_id, external_id, thread_id, 
                        raw_email_encrypted, sender_encrypted, subject_encrypted,
                        received_at, email_size_bytes, labels
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (external_id, org_id) DO NOTHING
                    """,
                    uuid.UUID(user_id), user_data['org_id'], email_id,
                    message_data.get('threadId'), 
                    json.dumps(message_data).encode('utf-8'),  # In production, encrypt this
                    sender.encode('utf-8'),  # In production, encrypt this
                    subject.encode('utf-8'),  # In production, encrypt this
                    received_at, email_size, 
                    json.dumps(message_data.get('labelIds', []))
                )
    
    except Exception as e:
        logger.error(f"Error storing email in database: {e}")
        # Don't raise exception - this is just caching

@app.get("/users", response_model=List[UserResponse])
async def list_users(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all users (admin endpoint)"""
    async with db.pool.acquire() as conn:
        users = await conn.fetch(
            "SELECT user_id, email, display_name, created_at, last_login, is_active FROM users ORDER BY created_at DESC"
        )
        return [UserResponse(**dict(user), user_id=str(user['user_id'])) for user in users]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)