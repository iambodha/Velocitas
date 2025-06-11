from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from typing import List, Dict, Any, Optional
import base64
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

class GmailService:
    """Gmail service for email operations"""
    
    def __init__(self, credentials_data: Dict[str, Any]):
        """Initialize Gmail service with credentials"""
        # Handle both 'token' and 'access_token' key names
        token = credentials_data.get("access_token") or credentials_data.get("token")
        
        if not token:
            raise ValueError("No access token found in credentials")
        
        # Normalize scopes - remove 'openid' if present
        scopes = credentials_data.get("scopes", [])
        normalized_scopes = [scope for scope in scopes if scope != 'openid']
        
        self.credentials = Credentials(
            token=token,
            refresh_token=credentials_data.get("refresh_token"),
            token_uri=credentials_data.get("token_uri"),
            client_id=credentials_data.get("client_id"),
            client_secret=credentials_data.get("client_secret"),
            scopes=normalized_scopes
        )
        
        try:
            self.service = build('gmail', 'v1', credentials=self.credentials)
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            raise ValueError(f"Failed to initialize Gmail service: {e}")
    
    async def get_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get user's emails"""
        try:
            # Get message list
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    email_data = self._parse_message(msg)
                    emails.append(email_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to get message {message['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise Exception(f"Failed to get emails: {e}")
    
    async def get_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get specific email by ID"""
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_message(msg)
            
        except HttpError as e:
            logger.error(f"Gmail API error getting message {message_id}: {e}")
            return None
    
    async def search_emails(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search emails with query"""
        try:
            # Search messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    email_data = self._parse_message(msg)
                    emails.append(email_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to get message {message['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API search error: {e}")
            raise Exception(f"Failed to search emails: {e}")
    
    async def get_labels(self) -> List[Dict[str, Any]]:
        """Get Gmail labels"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            return [
                {
                    'id': label['id'],
                    'name': label['name'],
                    'type': label.get('type', 'user'),
                    'messagesTotal': label.get('messagesTotal', 0),
                    'messagesUnread': label.get('messagesUnread', 0)
                }
                for label in labels
            ]
            
        except HttpError as e:
            logger.error(f"Gmail API error getting labels: {e}")
            raise Exception(f"Failed to get labels: {e}")
    
    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into standardized format"""
        headers = message.get('payload', {}).get('headers', [])
        
        # Extract headers
        subject = self._get_header_value(headers, 'Subject') or '(no subject)'
        sender = self._get_header_value(headers, 'From') or ''
        recipient = self._get_header_value(headers, 'To') or ''
        date = self._get_header_value(headers, 'Date') or ''
        
        # Extract body
        body_text, body_html = self._extract_body(message.get('payload', {}))
        
        return {
            'id': message['id'],
            'thread_id': message.get('threadId'),
            'subject': subject,
            'sender': sender,
            'recipient': recipient,
            'date': date,
            'snippet': message.get('snippet', ''),
            'body_text': body_text,
            'body_html': body_html,
            'label_ids': message.get('labelIds', []),
            'is_read': 'UNREAD' not in message.get('labelIds', []),
            'is_starred': 'STARRED' in message.get('labelIds', []),
            'is_important': 'IMPORTANT' in message.get('labelIds', [])
        }
    
    def _get_header_value(self, headers: List[Dict], name: str) -> Optional[str]:
        """Get header value by name"""
        for header in headers:
            if header.get('name', '').lower() == name.lower():
                return header.get('value')
        return None
    
    def _extract_body(self, payload: Dict) -> tuple[str, str]:
        """Extract text and HTML body from message payload"""
        body_text = ""
        body_html = ""
        
        def extract_parts(parts):
            nonlocal body_text, body_html
            
            for part in parts:
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        body_text = self._decode_base64(data)
                elif mime_type == 'text/html':
                    data = part.get('body', {}).get('data')
                    if data:
                        body_html = self._decode_base64(data)
                elif part.get('parts'):
                    extract_parts(part['parts'])
        
        if payload.get('parts'):
            extract_parts(payload['parts'])
        elif payload.get('body', {}).get('data'):
            # Single part message
            data = self._decode_base64(payload['body']['data'])
            mime_type = payload.get('mimeType', '')
            
            if mime_type == 'text/html':
                body_html = data
            else:
                body_text = data
        
        return body_text, body_html
    
    def _decode_base64(self, data: str) -> str:
        """Decode base64 URL-safe data"""
        try:
            # Add padding if needed
            missing_padding = len(data) % 4
            if missing_padding:
                data += '=' * (4 - missing_padding)
            
            # Replace URL-safe characters
            data = data.replace('-', '+').replace('_', '/')
            
            return base64.b64decode(data).decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to decode base64 data: {e}")
            return ""