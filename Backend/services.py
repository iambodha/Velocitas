import os
import re
import json
import base64
import html
import time
import gc
import logging
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
from email.utils import parseaddr
from dotenv import load_dotenv
import keyring
from cryptography.fernet import Fernet

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Load environment variables
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class SecureGmailClient:
    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.service = None
        self.client_secret_path = os.getenv('GMAIL_CLIENT_SECRET_PATH')
        self.encryption_key = os.getenv('GMAIL_ENCRYPTION_KEY')
        self._last_api_call = 0.0  # Initialize rate limiting tracker
        
        if not self.client_secret_path or not self.encryption_key:
            logger.error("Missing required environment variables")
            raise ValueError("Missing required environment variables")
        
        logger.info("SecureGmailClient initialized")
    
    def _secure_file_permissions(self, file_path):
        """Ensure file has secure permissions (Unix systems)"""
        if os.name != 'nt':  # Not Windows
            os.chmod(file_path, 0o600)
            logger.debug(f"Secure permissions applied to file")
    
    def _encrypt_token(self, token_data):
        """Encrypt token data"""
        f = Fernet(self.encryption_key.encode())
        logger.debug("Token encryption performed")
        return f.encrypt(token_data.encode())
    
    def _decrypt_token(self, encrypted_token):
        """Decrypt token data"""
        f = Fernet(self.encryption_key.encode())
        logger.debug("Token decryption performed")
        return f.decrypt(encrypted_token).decode()
    
    def _store_token_securely(self, token_data):
        """Store token in system keyring"""
        encrypted_token = self._encrypt_token(token_data)
        keyring.set_password("secure_gmail_api", self.user_id, encrypted_token.decode())
        logger.info("Credentials stored securely in keyring")
    
    def _retrieve_token_securely(self):
        """Retrieve token from system keyring"""
        encrypted_token = keyring.get_password("secure_gmail_api", self.user_id)
        if encrypted_token:
            logger.debug("Retrieved token from keyring")
            return self._decrypt_token(encrypted_token.encode())
        logger.debug("No token found in keyring")
        return None
    
    def _validate_message_id(self, message_id):
        """Validate message ID format"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', message_id):
            logger.warning(f"Invalid message ID format detected")
            raise ValueError("Invalid message ID format")
    
    def _sanitize_email_data(self, email_data):
        """Sanitize email data to prevent XSS and other attacks"""
        sanitized = {}
        
        # Sanitize text fields
        text_fields = ['subject', 'body', 'snippet']
        for field in text_fields:
            if field in email_data:
                sanitized[field] = html.escape(str(email_data[field]))
        
        # Validate and sanitize email addresses
        email_fields = ['from', 'to']
        for field in email_fields:
            if field in email_data:
                name, addr = parseaddr(email_data[field])
                if re.match(r'^[^@]+@[^@]+\.[^@]+$', addr):
                    sanitized[field] = email_data[field]
                else:
                    sanitized[field] = '[INVALID EMAIL]'
                    logger.warning(f"Invalid email format detected in {field} field")
        
        # Safe fields (IDs and dates)
        safe_fields = ['id', 'date']
        for field in safe_fields:
            if field in email_data:
                sanitized[field] = email_data[field]
        
        logger.debug("Email data sanitized")
        return sanitized
    
    def _extract_minimal_data(self, email_data, required_fields=None):
        """Extract only required fields"""
        if required_fields is None:
            required_fields = ['id', 'subject', 'from', 'date']
        
        logger.debug(f"Extracting minimal data with fields: {required_fields}")
        return {field: email_data.get(field, '') for field in required_fields}
    
    def _apply_rate_limit(self, calls_per_minute=30):
        """Apply rate limiting to API calls"""
        elapsed = time.time() - self._last_api_call
        min_interval = 60 / calls_per_minute
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self._last_api_call = time.time()
    
    def authenticate(self):
        """Securely authenticate with Gmail API"""
        creds = None
        
        # Try to retrieve stored token
        token_data = self._retrieve_token_securely()
        if token_data:
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(token_data), SCOPES
                )
                logger.info("Successfully loaded stored credentials")
            except Exception as e:
                logger.error(f"Error loading stored credentials: {type(e).__name__}")
                creds = None
        
        # Handle authentication
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Successfully refreshed credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {type(e).__name__}")
                    creds = None
            
            if not creds:
                # Secure file permissions
                self._secure_file_permissions(self.client_secret_path)
                
                logger.info("No valid credentials found, starting OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_path, SCOPES
                )
                creds = flow.run_local_server(port=8080)
                logger.info("New credentials obtained via OAuth")
            
            # Store credentials securely
            self._store_token_securely(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API service initialized successfully")
    
    def _get_email_details_raw(self, message_id):
        """Get raw email details with rate limiting"""
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Validate message ID
        self._validate_message_id(message_id)
        
        try:
            logger.debug(f"Retrieving email details for message ID")
            msg = self.service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])

            def get_header(name):
                for h in headers:
                    if h['name'].lower() == name.lower():
                        return h['value']
                return None

            subject = get_header('Subject') or ''
            sender = get_header('From') or ''
            to = get_header('To') or ''
            date = get_header('Date') or ''

            def extract_body(payload):
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                            return part['body']['data']
                        elif 'parts' in part:
                            for subpart in part['parts']:
                                if subpart.get('mimeType') == 'text/plain' and 'data' in subpart.get('body', {}):
                                    return subpart['body']['data']
                elif 'body' in payload and 'data' in payload['body']:
                    return payload['body']['data']
                return None

            raw_body = extract_body(payload)
            body = ''
            if raw_body:
                try:
                    body = base64.urlsafe_b64decode(raw_body).decode('utf-8', errors='ignore')
                except Exception:
                    body = base64.urlsafe_b64decode(raw_body).decode('latin-1', errors='ignore')

            logger.debug("Successfully extracted email content")
            return {
                'id': message_id,
                'subject': subject,
                'from': sender,
                'to': to,
                'date': date,
                'body': body,
                'snippet': msg.get('snippet', '')
            }
            
        except Exception as e:
            logger.error(f"Error retrieving email: {type(e).__name__}")
            return None
    
    def get_email_securely(self, message_id, required_fields=None):
        """Get email with full security measures"""
        try:
            logger.info(f"Getting email securely")
            # Get raw data
            raw_data = self._get_email_details_raw(message_id)
            if not raw_data:
                logger.warning("Failed to retrieve raw email data")
                return None
            
            # Sanitize data
            sanitized_data = self._sanitize_email_data(raw_data)
            
            # Extract minimal required data
            minimal_data = self._extract_minimal_data(sanitized_data, required_fields)
            
            # Clear sensitive data from memory
            raw_data.clear()
            sanitized_data.clear()
            del raw_data, sanitized_data
            
            logger.info("Successfully retrieved and processed email securely")
            return minimal_data
            
        finally:
            # Force garbage collection
            gc.collect()
    
    def list_messages_securely(self, label_ids=['INBOX'], query=None, max_results=10):
        """List messages with security measures"""
        if max_results > 50:  # Limit to prevent abuse
            max_results = 50
            logger.warning(f"Requested max_results exceeded limit, reduced to {max_results}")
        
        # Apply rate limiting
        self._apply_rate_limit()
            
        try:
            logger.info(f"Listing messages with labels: {label_ids}, query: {query if query else 'None'}")
            response = self.service.users().messages().list(
                userId='me',
                labelIds=label_ids,
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            valid_ids = [msg['id'] for msg in messages if self._validate_message_id_safe(msg['id'])]
            logger.info(f"Found {len(valid_ids)} valid messages")
            return valid_ids
            
        except Exception as e:
            logger.error(f"Error listing messages: {type(e).__name__}")
            return []
    
    def _validate_message_id_safe(self, message_id):
        """Safely validate message ID without raising exceptions"""
        try:
            self._validate_message_id(message_id)
            return True
        except ValueError:
            logger.warning(f"Invalid message ID detected in listing")
            return False
    
    def close(self):
        """Clean up resources"""
        if self.service:
            self.service.close()
            self.service = None
            logger.info("Gmail service closed and resources cleaned up")
    
    def __enter__(self):
        """Context manager entry"""
        self.authenticate()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

def generateEncryptionKey():
    """Generate a new encryption key"""
    key = Fernet.generate_key()
    logger.info("New encryption key generated")
    return key.decode()

# Usage example
if __name__ == "__main__":
    logger.info("Starting SecureGmailClient example")
    # Use as context manager for automatic cleanup
    with SecureGmailClient() as client:
        # List messages securely
        message_ids = client.list_messages_securely(max_results=5)
        logger.info(f"Found {len(message_ids)} messages.")
        
        if message_ids:
            # Get email with only required fields
            email = client.get_email_securely(
                message_ids[0], 
                required_fields=['subject', 'from', 'date']
            )
            if email:
                logger.info("Successfully retrieved secure email data")
                for key, value in email.items():
                    # Use truncated logging for extra safety
                    if isinstance(value, str) and len(value) > 100:
                        logger.info(f"{key}: {value[:50]}...")
                    else:
                        logger.info(f"{key}: {value}")