# File: /gmail-api-microservices/gmail-api-microservices/services/gmail-service/src/app.py

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import logging
from shared.database_init import initialize_database, check_database_health
from .handlers.gmail_api import GmailAPIHandler
from .models.email import EmailService
from .utils.dependencies import get_gmail_handler
import os
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gmail API Microservice",
    description="Sophisticated Gmail API service with advanced parsing",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Gmail API Microservice starting up...")
    
    # Initialize database
    initialize_database()
    
    # Check database health
    if not check_database_health():
        logger.error("Database health check failed!")
        raise Exception("Database connection failed")
    
    logger.info("Database connection established")

# Direct service endpoints (called by gateway)
@app.get("/health")
async def health_check():
    db_healthy = check_database_health()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "service": "gmail-api",
        "database": "connected" if db_healthy else "disconnected"
    }

@app.get("/profile")
async def get_user_profile(x_user_id: str = Header(...)):
    """Get user profile information - called by gateway"""
    try:
        handler = await get_gmail_handler(x_user_id)
        return handler.get_user_profile()
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/threads/list")
async def list_threads(
    request: dict,
    x_user_id: str = Header(...)
):
    """List email threads - called by gateway"""
    try:
        handler = await get_gmail_handler(x_user_id)
        result = handler.list_threads(
            folder=request.get('folder', 'inbox'),
            query=request.get('query'),
            max_results=request.get('max_results', 100),
            page_token=request.get('page_token'),
            label_ids=request.get('label_ids')
        )
        return result
    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    x_user_id: str = Header(...)
):
    """Get complete thread - called by gateway"""
    try:
        handler = await get_gmail_handler(x_user_id)
        return handler.get_thread(thread_id)
    except Exception as e:
        logger.error(f"Error getting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/messages/{message_id}/attachments/{attachment_id}")
async def get_attachment(
    message_id: str,
    attachment_id: str,
    x_user_id: str = Header(...)
):
    """Get attachment data - called by gateway"""
    try:
        handler = await get_gmail_handler(x_user_id)
        data = handler.get_attachment(message_id, attachment_id)
        return {
            "data": data,
            "message_id": message_id,
            "attachment_id": attachment_id
        }
    except Exception as e:
        logger.error(f"Error getting attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync")
async def sync_emails(x_user_id: str = Header(...)):
    """Sync emails from Gmail"""
    try:
        # Get Gmail handler using existing dependency
        handler = await get_gmail_handler(x_user_id)
        
        # Use the correct method names from GmailAPIHandler
        emails = []
        
        # Get messages from inbox (check what methods are available)
        try:
            # Try different method names that might exist
            if hasattr(handler, 'get_messages'):
                messages = handler.get_messages(folder='INBOX', max_results=50)
            elif hasattr(handler, 'fetch_messages'):
                messages = handler.fetch_messages(max_results=50)
            elif hasattr(handler, 'list_inbox'):
                messages = handler.list_inbox(max_results=50)
            else:
                # Use the Gmail API directly through the service
                results = handler.service.users().messages().list(
                    userId='me',
                    labelIds=['INBOX'],
                    maxResults=50
                ).execute()
                messages = results.get('messages', [])
        except Exception as e:
            logger.error(f"Error getting messages list: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")
        
        # Get message IDs
        if isinstance(messages, dict) and 'messages' in messages:
            message_ids = [msg['id'] for msg in messages['messages']]
        elif isinstance(messages, list):
            message_ids = [msg['id'] if isinstance(msg, dict) else msg for msg in messages[:50]]
        else:
            message_ids = []
        
        # Fetch detailed email data
        for msg_id in message_ids:
            try:
                # Try different method names for getting message details
                if hasattr(handler, 'get_message'):
                    email_data = handler.get_message(msg_id)
                elif hasattr(handler, 'fetch_message'):
                    email_data = handler.fetch_message(msg_id)
                else:
                    # Use Gmail API directly
                    message = handler.service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full'
                    ).execute()
                    
                    # Parse the message manually
                    email_data = {
                        'id': message['id'],
                        'subject': '',
                        'from': '',
                        'to': '',
                        'date': '',
                        'snippet': message.get('snippet', ''),
                        'body_text': '',
                        'body_html': '',
                        'labelIds': message.get('labelIds', [])
                    }
                    
                    # Parse headers
                    headers = message.get('payload', {}).get('headers', [])
                    for header in headers:
                        name = header.get('name', '').lower()
                        value = header.get('value', '')
                        if name == 'subject':
                            email_data['subject'] = value
                        elif name == 'from':
                            email_data['from'] = value
                        elif name == 'to':
                            email_data['to'] = value
                        elif name == 'date':
                            email_data['date'] = value
                
                # Convert to the format expected by email-service
                emails.append({
                    'id': email_data.get('id'),
                    'subject': email_data.get('subject', ''),
                    'sender': email_data.get('from', ''),
                    'recipient': email_data.get('to', ''),
                    'date': email_data.get('date'),
                    'snippet': email_data.get('snippet', ''),
                    'body_text': email_data.get('body_text', ''),
                    'body_html': email_data.get('body_html', ''),
                    'is_read': not ('UNREAD' in email_data.get('labelIds', [])),
                    'is_starred': 'STARRED' in email_data.get('labelIds', [])
                })
            except Exception as e:
                logger.warning(f"Failed to fetch message {msg_id}: {e}")
                continue
        
        # Send emails to email-service for storage
        email_service_url = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:5002')
        
        async with httpx.AsyncClient() as client:
            save_response = await client.post(
                f"{email_service_url}/emails/bulk",
                headers={"X-User-ID": x_user_id},
                json={"emails": emails},
                timeout=60.0
            )
            
            if save_response.status_code != 200:
                logger.error(f"Failed to save emails: {save_response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to save emails")
            
            save_data = save_response.json()
            
            return {
                "status": "sync_completed", 
                "user_id": x_user_id,
                "emails_fetched": len(emails),
                "emails_saved": save_data.get("saved_count", 0),
                "message": "Emails synced successfully"
            }
            
    except Exception as e:
        logger.error(f"Error syncing emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))