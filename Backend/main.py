from fastapi import FastAPI, Request, HTTPException, Depends, Query
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

# Database imports
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Boolean, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.exc import IntegrityError
import bcrypt
from contextlib import contextmanager

# Load environment variables
load_dotenv()

# IMPORTANT: Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI(
    title="Multi-User Gmail API with PostgreSQL",
    description="Gmail API with PostgreSQL storage, user management, and email persistence",
    version="2.0.0"
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

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://username:password@localhost:5432/gmail_api_db'
)

# Redis configuration (keeping for session management)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Thread pool for handling Gmail API calls
executor = ThreadPoolExecutor(max_workers=10)

# Database Setup
Base = declarative_base()

class User(Base):
    """User model with secure credential storage"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    
    # Encrypted credential storage
    encrypted_credentials = Column(Text, nullable=True)
    credentials_updated_at = Column(DateTime, nullable=True)
    
    # User metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Add indexes for performance
    __table_args__ = (
        Index('idx_user_google_id', 'google_user_id'),
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
    )

class Email(Base):
    """Email model for storing Gmail messages"""
    __tablename__ = 'emails'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    gmail_message_id = Column(String(255), nullable=False, index=True)
    
    # Email content
    subject = Column(Text, nullable=True)
    sender = Column(String(500), nullable=True)
    recipient = Column(String(500), nullable=True)
    date_sent = Column(DateTime, nullable=True)
    
    # Email body (can be large)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    
    # Gmail metadata stored as JSON
    gmail_metadata = Column(JSONB, nullable=True)
    
    # Processing metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    # New fields
    is_starred = Column(Boolean, default=False)
    category = Column(String(100), nullable=True, index=True)
    urgency = Column(Integer, default=0, nullable=True)
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_email_user_gmail_id', 'user_id', 'gmail_message_id', unique=True),
        Index('idx_email_user_date', 'user_id', 'date_sent'),
        Index('idx_email_user_read', 'user_id', 'is_read'),
        Index('idx_email_sender', 'sender'),
        Index('idx_email_starred', 'user_id', 'is_starred'),
        Index('idx_email_category', 'user_id', 'category'),
        Index('idx_email_urgency', 'user_id', 'urgency'),
    )

# Database engine and session
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
def create_tables():
    """Create database tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

# Initialize database
create_tables()

# Database dependency
@contextmanager
def get_db():
    """Database session context manager"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_db_session():
    """FastAPI dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize Redis client (keeping for caching)
def create_redis_client():
    """Create Redis client with error handling"""
    try:
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
        client.ping()
        print("✅ Redis connection successful")
        return client
    except redis.ConnectionError:
        print("❌ Redis connection failed - caching disabled")
        return None

redis_client = create_redis_client()

class SecureCredentialManager:
    """Secure credential manager with PostgreSQL storage"""
    
    def __init__(self, encryption_key: str = None):
        self.encryption_key = encryption_key or JWT_SECRET
    
    def _encrypt_credentials(self, creds_dict: dict) -> str:
        """Encrypt credentials before storage"""
        import cryptography.fernet
        key = base64.urlsafe_b64encode(self.encryption_key.ljust(32)[:32].encode())
        f = cryptography.fernet.Fernet(key)
        return f.encrypt(json.dumps(creds_dict).encode()).decode()
    
    def _decrypt_credentials(self, encrypted_creds: str) -> dict:
        """Decrypt stored credentials"""
        import cryptography.fernet
        key = base64.urlsafe_b64encode(self.encryption_key.ljust(32)[:32].encode())
        f = cryptography.fernet.Fernet(key)
        return json.loads(f.decrypt(encrypted_creds.encode()).decode())
    
    def save_user_and_credentials(self, google_user_id: str, email: str, name: str, creds: Credentials):
        """Save or update user and their credentials securely"""
        with get_db() as db:
            # Check if user exists
            user = db.query(User).filter(User.google_user_id == google_user_id).first()
            
            # Prepare credentials dict
            creds_dict = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            encrypted_creds = self._encrypt_credentials(creds_dict)
            
            if user:
                # Update existing user
                user.email = email
                user.name = name
                user.encrypted_credentials = encrypted_creds
                user.credentials_updated_at = datetime.utcnow()
                user.last_login = datetime.utcnow()
                user.is_active = True
            else:
                # Create new user
                user = User(
                    google_user_id=google_user_id,
                    email=email,
                    name=name,
                    encrypted_credentials=encrypted_creds,
                    credentials_updated_at=datetime.utcnow(),
                    last_login=datetime.utcnow()
                )
                db.add(user)
                # Process new user registration
                process_new_user_registration(email, name, google_user_id)
            
            db.flush()
            return str(user.id)
    
    def load_credentials(self, user_id: str) -> Optional[Credentials]:
        """Load and decrypt user credentials"""
        with get_db() as db:
            user = db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user or not user.encrypted_credentials:
                return None
            
            try:
                creds_data = self._decrypt_credentials(user.encrypted_credentials)
                
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
                    self.update_credentials(user_id, creds)
                
                return creds
            except Exception as e:
                print(f"Error loading credentials for user {user_id}: {e}")
                return None
    
    def update_credentials(self, user_id: str, creds: Credentials):
        """Update existing user credentials"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                creds_dict = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes,
                    'updated_at': datetime.utcnow().isoformat()
                }
                user.encrypted_credentials = self._encrypt_credentials(creds_dict)
                user.credentials_updated_at = datetime.utcnow()
    
    def get_user_by_google_id(self, google_user_id: str) -> Optional[User]:
        """Get user by Google ID"""
        with get_db() as db:
            return db.query(User).filter(
                User.google_user_id == google_user_id,
                User.is_active == True
            ).first()
    
    def deactivate_user(self, user_id: str):
        """Deactivate user instead of deleting"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                user.encrypted_credentials = None

class EmailManager:
    """Manage email storage in PostgreSQL"""
    
    def save_emails(self, user_id: str, emails: List[dict]):
        """Save emails to database, avoiding duplicates"""
        with get_db() as db:
            saved_count = 0
            for email_data in emails:
                try:
                    # Check if email already exists
                    existing = db.query(Email).filter(
                        Email.user_id == user_id,
                        Email.gmail_message_id == email_data['id']
                    ).first()
                    
                    if not existing:
                        # Parse date
                        date_sent = None
                        if email_data.get('date'):
                            try:
                                from email.utils import parsedate_to_datetime
                                date_sent = parsedate_to_datetime(email_data['date'])
                            except:
                                pass
                        
                        email = Email(
                            user_id=user_id,
                            gmail_message_id=email_data['id'],
                            subject=email_data.get('subject'),
                            sender=email_data.get('sender'),
                            recipient=email_data.get('to'),
                            date_sent=date_sent,
                            body_text=email_data.get('body'),
                            snippet=email_data.get('snippet'),
                            gmail_metadata=email_data
                        )
                        db.add(email)
                        saved_count += 1
                
                except IntegrityError:
                    # Skip duplicate emails
                    db.rollback()
                    continue
                except Exception as e:
                    print(f"Error saving email {email_data.get('id')}: {e}")
                    continue
            
            return saved_count
    
    def get_user_emails(self, user_id: str, limit: int = 50, offset: int = 0) -> List[dict]:
        """Get user emails from database"""
        with get_db() as db:
            emails = db.query(Email).filter(
                Email.user_id == user_id
            ).order_by(
                Email.date_sent.desc().nullslast()
            ).offset(offset).limit(limit).all()
            
            # Convert SQLAlchemy objects to dictionaries before session closes
            email_list = []
            for email in emails:
                email_list.append({
                    'id': email.gmail_message_id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'recipient': email.recipient,
                    'date': email.date_sent.isoformat() if email.date_sent else None,
                    'snippet': email.snippet,
                    'is_read': email.is_read,
                    'stored_at': email.created_at.isoformat()
                })
            
            return email_list
    
    def get_email_by_gmail_id(self, user_id: str, gmail_message_id: str) -> Optional[dict]:
        """Get specific email by Gmail message ID"""
        with get_db() as db:
            email = db.query(Email).filter(
                Email.user_id == user_id,
                Email.gmail_message_id == gmail_message_id
            ).first()
            
            if not email:
                return None
            
            # Convert to dictionary before session closes
            return {
                "id": email.gmail_message_id,
                "subject": email.subject,
                "sender": email.sender,
                "recipient": email.recipient,
                "date": email.date_sent.isoformat() if email.date_sent else None,
                "body_text": email.body_text,
                "body_html": email.body_html,
                "snippet": email.snippet,
                "is_read": email.is_read,
                "source": "database"
            }
    
    def search_emails(self, user_id: str, query: str, limit: int = 20) -> List[Email]:
        """Search emails by subject or sender"""
        with get_db() as db:
            return db.query(Email).filter(
                Email.user_id == user_id,
                (Email.subject.ilike(f'%{query}%') | 
                 Email.sender.ilike(f'%{query}%'))
            ).order_by(
                Email.date_sent.desc().nullslast()
            ).limit(limit).all()
    
    def get_email_stats(self, user_id: str) -> dict:
        """Get email statistics for user"""
        with get_db() as db:
            total = db.query(Email).filter(Email.user_id == user_id).count()
            unread = db.query(Email).filter(
                Email.user_id == user_id,
                Email.is_read == False
            ).count()
            
            # Top senders
            top_senders = db.execute(text("""
                SELECT sender, COUNT(*) as email_count
                FROM emails 
                WHERE user_id = :user_id AND sender IS NOT NULL
                GROUP BY sender 
                ORDER BY email_count DESC 
                LIMIT 10
            """), {"user_id": user_id}).fetchall()
            
            return {
                "total_emails": total,
                "unread_emails": unread,
                "top_senders": [{"sender": row.sender, "count": row.email_count} for row in top_senders]
            }

# Initialize managers
credential_manager = SecureCredentialManager()
email_manager = EmailManager()

# Authentication functions
def create_session_token(user_id: str) -> str:
    """Create JWT session token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# New function to handle user registration
def process_new_user_registration(email: str, name: str, google_user_id: str):
    """
    Process a new user registration.
    This function is called only when a new user signs up and is added to the database.
    
    Args:
        email: User's email address
        name: User's name
        google_user_id: Google's unique user identifier
    """
    print(f"🎉 New user registered: {name} ({email})")
    
    try:
        # Get the user's ID from database
        with get_db() as db:
            user = db.query(User).filter(User.google_user_id == google_user_id).first()
            if not user:
                print(f"⚠️ Could not find newly registered user: {email}")
                return
            
            user_id = str(user.id)
        
        # Load credentials for the new user
        creds = credential_manager.load_credentials(user_id)
        if not creds or not creds.valid:
            print(f"⚠️ Could not load valid credentials for new user: {email}")
            return
            
        # Fetch emails from Gmail API (synchronously)
        service = build('gmail', 'v1', credentials=creds)
        
        # Get list of messages (most recent 50)
        results = service.users().messages().list(
            userId='me',
            maxResults=50
        ).execute()
        
        messages = results.get('messages', [])
        print(f"📥 Fetching {len(messages)} initial emails for new user: {email}")
        
        email_list = []
        for message in messages:
            try:
                # Get message details
                msg = service.users().messages().get(
                    userId='me', 
                    id=message['id'],
                    format='full'  # Get full message details
                ).execute()
                
                # Extract headers
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
                
                # Extract message metadata
                is_read = 'UNREAD' not in msg.get('labelIds', [])
                is_starred = 'STARRED' in msg.get('labelIds', [])
                
                # Extract body
                def extract_body(payload):
                    body = ""
                    body_html = ""
                    if 'parts' in payload:
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/plain':
                                if part['body'].get('data'):
                                    data = part['body']['data']
                                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                            elif part['mimeType'] == 'text/html':
                                if part['body'].get('data'):
                                    data = part['body']['data']
                                    body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    else:
                        if payload['body'].get('data'):
                            data = payload['body']['data']
                            if 'mimeType' in payload and payload['mimeType'] == 'text/html':
                                body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                            else:
                                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    return body, body_html
                
                body_text, body_html = extract_body(msg['payload'])
                
                # Set category to None for all emails
                category = None
                
                email_list.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'to': to,
                    'date': date,
                    'body': body_text,
                    'body_html': body_html,
                    'snippet': msg.get('snippet', ''),
                    'is_read': is_read,
                    'is_starred': is_starred,
                    'category': category,  # Always None
                    'gmail_data': msg
                })
            except Exception as e:
                print(f"Error processing message {message['id']}: {e}")
                continue
        
        # Save emails to database
        if email_list:
            saved_count = email_manager.save_emails(user_id, email_list)
            print(f"✅ Successfully saved {saved_count} initial emails for new user: {email}")
        
    except Exception as e:
        print(f"❌ Error importing initial emails for {email}: {str(e)}")

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

# Fallback in-memory storage for pending auth
pending_auth: Dict[str, str] = {}

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    with get_db() as db:
        user_count = db.query(User).filter(User.is_active == True).count()
        email_count = db.query(Email).count()
    
    return {
        "message": "Multi-User Gmail API with PostgreSQL", 
        "version": "2.0.0",
        "database": "PostgreSQL",
        "redis_connected": redis_client is not None,
        "stats": {
            "active_users": user_count,
            "total_emails": email_count
        }
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
    
    # Test database connection
    db_status = "connected"
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    with get_db() as db:
        active_users = db.query(User).filter(User.is_active == True).count()
    
    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status,
        "active_users": active_users
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
        
        # For returning users, sync latest emails as a background task
        if not is_new_user:
            asyncio.create_task(sync_latest_emails_until_overlap(user_id))
            print(f"🔄 Background sync started for returning user: {user_email}")
        
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
    
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
    
    if creds and creds.valid and user:
        return {
            "authenticated": True, 
            "message": "Ready to access Gmail", 
            "user_id": user_id,
            "email": user.email,
            "name": user.name
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
    credential_manager.deactivate_user(user_id)
    return {"success": True, "message": "Logged out successfully"}

@app.get("/emails")
async def get_emails(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    sync_new: bool = Query(default=False),
    user_id: str = Depends(get_current_user)
):
    """Get emails from database with option to sync new emails from Gmail"""
    
    if sync_new:
        # Sync new emails from Gmail API
        await sync_emails_from_gmail(user_id, limit)
    
    # Get emails from database (now returns dictionaries, not SQLAlchemy objects)
    email_list = email_manager.get_user_emails(user_id, limit, offset)
    
    return {
        "emails": email_list,
        "user_id": user_id,
        "count": len(email_list),
        "offset": offset,
        "limit": limit
    }

async def sync_emails_from_gmail(user_id: str, limit: int = 20):
    """Sync emails from Gmail API to database"""
    creds = credential_manager.load_credentials(user_id)
    if not creds or not creds.valid:
        return
    
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
                    
                    body = extract_body(msg['payload'])
                    
                    email_list.append({
                        'id': message['id'],
                        'subject': subject,
                        'sender': sender,
                        'to': to,
                        'date': date,
                        'body': body,
                        'snippet': msg.get('snippet', ''),
                        'gmail_data': msg
                    })
                except Exception as e:
                    print(f"Error processing message {message['id']}: {e}")
                    continue
            
            return email_list
        
        email_list = await gmail_api_call(fetch_emails)
        
        # Save emails to database
        if email_list:
            saved_count = email_manager.save_emails(user_id, email_list)
            print(f"Saved {saved_count} new emails for user {user_id}")
        
    except Exception as e:
        print(f"Error syncing emails from Gmail: {e}")

@app.get("/email/{email_id}")
async def get_email(email_id: str, user_id: str = Depends(get_current_user)):
    """Get specific email content from database or Gmail API"""
    
    # Try to get from database first
    email_dict = email_manager.get_email_by_gmail_id(user_id, email_id)
    
    if email_dict:
        # Mark as read (in a separate session)
        with get_db() as db:
            db_email = db.query(Email).filter(
                Email.user_id == user_id,
                Email.gmail_message_id == email_id
            ).first()
            if db_email:
                db_email.is_read = True
        
        return email_dict
    
    # Fallback to Gmail API if not in database
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
                "recipient": to,
                "date": date,
                "body_text": body,
                "snippet": message.get('snippet', ''),
                "source": "gmail_api"
            }
        
        email_data = await gmail_api_call(fetch_email)
        
        # Save to database for future use
        email_manager.save_emails(user_id, [email_data])
        
        return email_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch email: {str(e)}")

@app.get("/emails/search")
async def search_emails(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, le=50),
    user_id: str = Depends(get_current_user)
):
    """Search emails by subject or sender"""
    
    emails = email_manager.search_emails(user_id, q, limit)
    
    email_list = []
    for email in emails:
        email_list.append({
            'id': email.gmail_message_id,
            'subject': email.subject,
            'sender': email.sender,
            'recipient': email.recipient,
            'date': email.date_sent.isoformat() if email.date_sent else None,
            'snippet': email.snippet,
            'is_read': email.is_read
        })
    
    return {
        "emails": email_list,
        "query": q,
        "count": len(email_list)
    }

@app.get("/emails/stats")
async def get_email_stats(user_id: str = Depends(get_current_user)):
    """Get email statistics for current user"""
    stats = email_manager.get_email_stats(user_id)
    return stats

@app.post("/emails/sync")
async def sync_emails(
    limit: int = Query(default=50, le=200),
    user_id: str = Depends(get_current_user)
):
    """Manually trigger email sync from Gmail"""
    await sync_emails_from_gmail(user_id, limit)
    
    # Get updated stats
    stats = email_manager.get_email_stats(user_id)
    
    return {
        "success": True,
        "message": f"Synced up to {limit} emails",
        "stats": stats
    }

@app.put("/email/{email_id}/read")
async def mark_email_read(
    email_id: str,
    is_read: bool = True,
    user_id: str = Depends(get_current_user)
):
    """Mark email as read/unread"""
    with get_db() as db:
        email = db.query(Email).filter(
            Email.user_id == user_id,
            Email.gmail_message_id == email_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email.is_read = is_read
        email.updated_at = datetime.utcnow()
    
    return {
        "success": True,
        "email_id": email_id,
        "is_read": is_read
    }

# User management endpoints

@app.get("/user/profile")
async def get_user_profile(user_id: str = Depends(get_current_user)):
    """Get current user profile"""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        stats = email_manager.get_email_stats(user_id)
        
        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "email_stats": stats
        }

@app.put("/user/profile")
async def update_user_profile(
    name: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Update user profile"""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if name is not None:
            user.name = name
    
    return {"success": True, "message": "Profile updated"}

# Admin endpoints

@app.get("/admin/users")
async def get_all_users():
    """Get all users (admin endpoint)"""
    with get_db() as db:
        users = db.query(User).filter(User.is_active == True).all()
        
        user_list = []
        for user in users:
            stats = email_manager.get_email_stats(str(user.id))
            user_list.append({
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "email_count": stats["total_emails"]
            })
    
    return {
        "users": user_list,
        "count": len(user_list)
    }

@app.get("/admin/stats")
async def get_admin_stats():
    """Get system-wide statistics"""
    with get_db() as db:
        total_users = db.query(User).filter(User.is_active == True).count()
        total_emails = db.query(Email).count()
        
        # Recent activity
        recent_users = db.query(User).filter(
            User.last_login >= datetime.utcnow() - timedelta(days=7),
            User.is_active == True
        ).count()
        
        # Database size info
        db_size = db.execute(text("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as size
        """)).scalar()
        
        # Email volume by day (last 7 days)
        email_volume = db.execute(text("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM emails 
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)).fetchall()
    
    return {
        "total_users": total_users,
        "total_emails": total_emails,
        "active_users_week": recent_users,
        "database_size": db_size,
        "email_volume_week": [
            {"date": row.date.isoformat(), "count": row.count} 
            for row in email_volume
        ]
    }

@app.delete("/admin/user/{user_id}")
async def delete_user_admin(user_id: str):
    """Deactivate user (admin endpoint)"""
    credential_manager.deactivate_user(user_id)
    return {"success": True, "message": f"User {user_id} deactivated"}

@app.get("/admin/database/health")
async def database_health():
    """Check database health and performance"""
    with get_db() as db:
        try:
            # Connection test
            db.execute(text("SELECT 1"))
            
            # Table sizes
            table_sizes = db.execute(text("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)).fetchall()
            
            # Index usage
            index_usage = db.execute(text("""
                SELECT 
                    schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
                FROM pg_stat_user_indexes 
                ORDER BY idx_tup_read DESC 
                LIMIT 10
            """)).fetchall()
            
            return {
                "status": "healthy",
                "table_sizes": [
                    {"table": row.tablename, "size": row.size} 
                    for row in table_sizes
                ],
                "top_indexes": [
                    {
                        "table": row.tablename,
                        "index": row.indexname,
                        "reads": row.idx_tup_read,
                        "fetches": row.idx_tup_fetch
                    }
                    for row in index_usage
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

# Cache management endpoints

@app.delete("/cache/clear")
async def clear_cache(user_id: str = Depends(get_current_user)):
    """Clear Redis cache for current user"""
    if redis_client:
        try:
            # Clear user-specific cache keys
            keys = redis_client.keys(f"*:{user_id}")
            if keys:
                redis_client.delete(*keys)
            return {"success": True, "message": f"Cleared {len(keys)} cache entries"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        return {"success": False, "message": "Redis not available"}

# Startup and shutdown events

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("🚀 Gmail API with PostgreSQL starting up...")
    
    # Test database connection
    try:
        with get_db() as db:
            db.execute(text("SELECT version()"))
        print("✅ PostgreSQL connection successful")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
    
    # Test Redis connection
    if redis_client:
        try:
            redis_client.ping()
            print("✅ Redis connection successful")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Gmail API shutting down...")
    
    # Close thread pool
    executor.shutdown(wait=True)
    
    # Close database connections
    engine.dispose()
    
    print("✅ Cleanup completed")

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

async def sync_latest_emails_until_overlap(user_id: str):
    print(f"🔄 Starting background sync for user {user_id}")
