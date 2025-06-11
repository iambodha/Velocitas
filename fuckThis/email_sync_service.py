from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import contextmanager
import uuid
import os
import base64
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dotenv import load_dotenv
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("email-sync-service")

# Load environment variables
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://username:password@localhost:5432/gmail_api_db'
)

# Gmail API configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')

# Create FastAPI app
app = FastAPI(
    title="Email Sync Service",
    description="Background service for email synchronization tasks",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Database setup
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

class EmailSyncQueue(Base):
    """Queue for email sync tasks"""
    __tablename__ = 'email_sync_queue'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False, index=True)
    status = Column(String(50), default='pending', nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    
    # Add index for efficient queue processing
    __table_args__ = (
        Index('idx_sync_queue_status_priority', 'status', 'priority'),
    )

# Database engine and session
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
def create_tables():
    """Create database tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")

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

class SecureCredentialManager:
    """Secure credential manager with PostgreSQL storage"""
    
    def __init__(self, encryption_key: str = None):
        self.encryption_key = encryption_key or JWT_SECRET
    
    def _decrypt_credentials(self, encrypted_creds: str) -> dict:
        """Decrypt stored credentials"""
        import cryptography.fernet
        key = base64.urlsafe_b64encode(self.encryption_key.ljust(32)[:32].encode())
        f = cryptography.fernet.Fernet(key)
        return json.loads(f.decrypt(encrypted_creds.encode()).decode())
    
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
                    from google.auth.transport.requests import Request as GoogleRequest
                    creds.refresh(GoogleRequest())
                    self._update_credentials(user_id, creds)
                
                return creds
            except Exception as e:
                logger.error(f"Error loading credentials for user {user_id}: {e}")
                return None
                
    def _update_credentials(self, user_id: str, creds: Credentials):
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
                
                # Re-encrypt the updated credentials
                import cryptography.fernet
                key = base64.urlsafe_b64encode(self.encryption_key.ljust(32)[:32].encode())
                f = cryptography.fernet.Fernet(key)
                encrypted_creds = f.encrypt(json.dumps(creds_dict).encode()).decode()
                
                user.encrypted_credentials = encrypted_creds
                user.credentials_updated_at = datetime.utcnow()

# Email syncing functions
class EmailSyncService:
    def __init__(self):
        self.credential_manager = SecureCredentialManager()
        
    async def process_sync_queue(self):
        """Process pending items in the sync queue"""
        logger.info("Processing email sync queue")
        with get_db() as db:
            # Get all pending queue items ordered by priority
            queue_items = db.query(EmailSyncQueue).filter(
                EmailSyncQueue.status == 'pending'
            ).order_by(
                EmailSyncQueue.priority.desc(),
                EmailSyncQueue.created_at.asc()
            ).limit(10).all()
            
            for item in queue_items:
                # Mark as processing
                item.status = 'processing'
                item.updated_at = datetime.utcnow()
                db.commit()
                
                try:
                    # Process the sync
                    await self.sync_user_emails(str(item.user_id))
                    
                    # Mark as completed
                    item.status = 'completed'
                    item.completed_at = datetime.utcnow()
                except Exception as e:
                    # Mark as failed
                    item.status = 'failed'
                    item.error = str(e)
                    logger.error(f"Failed to process queue item {item.id}: {e}")
                
                item.updated_at = datetime.utcnow()
                db.commit()
    
    async def sync_all_active_users(self):
        """Sync emails for all active users"""
        logger.info("Starting scheduled sync for all active users")
        with get_db() as db:
            active_users = db.query(User).filter(User.is_active == True).all()
            
        sync_count = 0
        for user in active_users:
            try:
                new_emails = await self.sync_user_emails(str(user.id))
                sync_count += 1
                logger.info(f"Synced {new_emails} new emails for user {user.email}")
            except Exception as e:
                logger.error(f"Error syncing emails for user {user.id}: {e}")
        
        logger.info(f"Completed sync for {sync_count} users")
        return sync_count
    
    async def sync_user_emails(self, user_id: str, max_emails: int = 100):
        """Sync emails for a specific user"""
        creds = self.credential_manager.load_credentials(user_id)
        if not creds or not creds.valid:
            logger.warning(f"Invalid credentials for user {user_id}")
            return 0
        
        try:
            # Get existing email IDs for this user 
            with get_db() as db:
                existing_emails = db.query(Email.gmail_message_id).filter(
                    Email.user_id == user_id
                ).all()
                existing_ids = {email.gmail_message_id for email in existing_emails}
            
            # Call Gmail API
            service = build('gmail', 'v1', credentials=creds)
            
            # Track our progress
            total_saved = 0
            next_page_token = None
            found_overlap = False
            batch_size = 50  # Smaller batch size to be more efficient
            max_batches = 2  # Limit to prevent excessive API calls
            
            for batch in range(max_batches):
                # Fetch batch of messages
                results = service.users().messages().list(
                    userId='me',
                    maxResults=batch_size,
                    pageToken=next_page_token
                ).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break
                    
                next_page_token = results.get('nextPageToken')
                
                # Process each message in the batch
                email_list = []
                for message in messages:
                    msg_id = message['id']
                    
                    # If we've already seen this email, we found our overlap point
                    if msg_id in existing_ids:
                        found_overlap = True
                        continue
                    
                    # Only fetch full message data if we haven't seen it
                    msg = service.users().messages().get(
                        userId='me', 
                        id=msg_id,
                        format='full'
                    ).execute()
                    
                    # Extract data and create email dict
                    email_data = self._extract_email_data(msg)
                    email_list.append(email_data)
                    
                    # Check if we've reached our max emails limit
                    if len(email_list) >= max_emails:
                        break
                
                # Save this batch of emails to database
                if email_list:
                    saved_count = self._save_emails(user_id, email_list)
                    total_saved += saved_count
                    logger.info(f"Batch {batch+1}: Saved {saved_count} new emails for user {user_id}")
                
                # If we found overlap or reached max emails, we're done
                if found_overlap or len(email_list) >= max_emails or not next_page_token:
                    break
            
            logger.info(f"Sync completed: saved {total_saved} new emails for user {user_id}")
            return total_saved
            
        except Exception as e:
            logger.error(f"Error syncing emails for user {user_id}: {e}")
            raise
            
    def _extract_email_data(self, msg):
        """Extract email data from Gmail API message"""
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
        body_text, body_html = self._extract_body(msg['payload'])
        
        return {
            'id': msg['id'],
            'subject': subject,
            'sender': sender,
            'to': to,
            'date': date,
            'body': body_text,
            'body_html': body_html,
            'snippet': msg.get('snippet', ''),
            'is_read': is_read,
            'is_starred': is_starred,
            'category': None,
            'gmail_data': msg
        }
    
    def _extract_body(self, payload):
        """Extract body content from message payload"""
        body_text = ""
        body_html = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part['body'].get('data'):
                        data = part['body']['data']
                        body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
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
                    body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        
        return body_text, body_html
    
    def _save_emails(self, user_id: str, emails: List[dict]):
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
                            body_html=email_data.get('body_html'),
                            snippet=email_data.get('snippet'),
                            is_read=email_data.get('is_read', False),
                            is_starred=email_data.get('is_starred', False),
                            gmail_metadata=email_data.get('gmail_data')
                        )
                        db.add(email)
                        saved_count += 1
                
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error saving email {email_data.get('id')}: {e}")
                    continue
            
            return saved_count
    
    def add_to_sync_queue(self, user_id: str, priority: int = 0):
        """Add user to email sync queue"""
        with get_db() as db:
            # Check for existing pending or processing queue item
            existing = db.query(EmailSyncQueue).filter(
                EmailSyncQueue.user_id == user_id,
                EmailSyncQueue.status.in_(['pending', 'processing'])
            ).first()
            
            if not existing:
                queue_item = EmailSyncQueue(
                    user_id=user_id,
                    priority=priority,
                    status='pending'
                )
                db.add(queue_item)
                db.commit()
                return str(queue_item.id)
            else:
                # Update priority if higher
                if priority > existing.priority:
                    existing.priority = priority
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                return str(existing.id)

# Initialize service and scheduler
email_sync_service = EmailSyncService()
scheduler = AsyncIOScheduler()

# API endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    with get_db() as db:
        user_count = db.query(User).filter(User.is_active == True).count()
        email_count = db.query(Email).count()
        queue_count = db.query(EmailSyncQueue).filter(
            EmailSyncQueue.status == 'pending'
        ).count()
    
    return {
        "service": "Email Sync Service",
        "version": "1.0.0",
        "status": "running",
        "stats": {
            "active_users": user_count,
            "total_emails": email_count,
            "pending_sync_tasks": queue_count
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
            return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/sync/user/{user_id}")
async def sync_user(user_id: str, background_tasks: BackgroundTasks):
    """Manually trigger sync for a specific user"""
    # Check if user exists
    with get_db() as db:
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    # Add to sync queue with high priority
    queue_id = email_sync_service.add_to_sync_queue(user_id, priority=10)
    
    # Trigger processing in background
    background_tasks.add_task(email_sync_service.process_sync_queue)
    
    return {
        "message": "Sync scheduled",
        "queue_id": queue_id,
        "user_email": user.email,
        "status": "pending"
    }

@app.post("/sync/all")
async def sync_all_users(background_tasks: BackgroundTasks):
    """Manually trigger sync for all users"""
    background_tasks.add_task(email_sync_service.sync_all_active_users)
    return {"message": "Sync scheduled for all users"}

@app.post("/sync/process-queue")
async def process_queue(background_tasks: BackgroundTasks):
    """Manually process the sync queue"""
    background_tasks.add_task(email_sync_service.process_sync_queue)
    
    # Get queue stats
    with get_db() as db:
        pending = db.query(EmailSyncQueue).filter(
            EmailSyncQueue.status == 'pending'
        ).count()
        
        processing = db.query(EmailSyncQueue).filter(
            EmailSyncQueue.status == 'processing'
        ).count()
    
    return {
        "message": "Processing queue",
        "queue_stats": {
            "pending": pending,
            "processing": processing
        }
    }

@app.post("/register/user/{user_id}")
async def register_new_user(user_id: str, background_tasks: BackgroundTasks):
    """Handle new user registration"""
    with get_db() as db:
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    # Add to sync queue with highest priority
    queue_id = email_sync_service.add_to_sync_queue(user_id, priority=100)
    
    # Immediately process in background
    background_tasks.add_task(email_sync_service.process_sync_queue)
    
    return {
        "message": "New user registered for email sync",
        "user_email": user.email,
        "queue_id": queue_id
    }

# Setup scheduled tasks
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("🚀 Email Sync Service starting up...")
    
    # Schedule email sync every 2 hours
    scheduler.add_job(
        email_sync_service.sync_all_active_users,
        trigger=IntervalTrigger(hours=2),
        id='sync_all_users',
        name='Sync all users every 2 hours',
        replace_existing=True
    )
    
    # Schedule queue processing every 5 minutes
    scheduler.add_job(
        email_sync_service.process_sync_queue,
        trigger=IntervalTrigger(minutes=5),
        id='process_queue',
        name='Process sync queue every 5 minutes',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("✅ Scheduled tasks initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Email Sync Service shutting down...")
    scheduler.shutdown()
    logger.info("✅ Scheduler shutdown complete")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081  # Use a different port than the main application
    )

