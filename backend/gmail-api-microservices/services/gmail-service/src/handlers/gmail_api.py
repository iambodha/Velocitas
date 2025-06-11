# File: /gmail-api-microservices/gmail-api-microservices/services/gmail-service/src/handlers/gmail_api.py

import base64
import html
import re
from typing import List, Dict, Optional, Tuple, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from dataclasses import dataclass
from email.utils import parseaddr, getaddresses
import mimetypes

logger = logging.getLogger(__name__)

@dataclass
class EmailAddress:
    email: str
    name: Optional[str] = None
    
    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email

@dataclass
class Attachment:
    filename: str
    mime_type: str
    size: int
    attachment_id: str
    data: Optional[str] = None
    headers: Optional[List[Dict]] = None

@dataclass
class ParsedMessage:
    id: str
    thread_id: str
    subject: str
    sender: EmailAddress
    to: List[EmailAddress]
    cc: Optional[List[EmailAddress]]
    bcc: Optional[List[EmailAddress]]
    date: str
    snippet: str
    body_text: str
    body_html: str
    processed_html: str
    is_read: bool
    is_starred: bool
    is_important: bool
    is_draft: bool
    labels: List[Dict[str, str]]
    attachments: List[Attachment]
    message_id: Optional[str]
    reply_to: Optional[str]
    references: Optional[str]
    in_reply_to: Optional[str]
    list_unsubscribe: Optional[str]
    has_tls: bool
    raw_message: Dict

class GmailAPIHandler:
    """Sophisticated Gmail API handler matching TypeScript functionality"""
    
    def __init__(self):
        self.service = None
    
    def create_credentials_from_dict(self, creds_data: dict) -> Credentials:
        """Create credentials object from dictionary with proper validation"""
        # Required fields for OAuth2 credentials
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        
        # Check for missing fields
        missing_fields = [field for field in required_fields if not creds_data.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required credential fields: {missing_fields}")
        
        return Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data.get('scopes', ['https://www.googleapis.com/auth/gmail.readonly'])
        )
    
    def initialize_service(self, credentials: Credentials):
        """Initialize Gmail service"""
        self.service = build('gmail', 'v1', credentials=credentials)
    
    def get_user_profile(self) -> Dict[str, str]:
        """Get user profile information"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                'email': profile.get('emailAddress', ''),
                'messages_total': profile.get('messagesTotal', 0),
                'threads_total': profile.get('threadsTotal', 0)
            }
        except HttpError as error:
            logger.error(f"Error fetching user profile: {error}")
            raise
    
    def list_threads(self, 
                    folder: str = 'inbox',
                    query: Optional[str] = None,
                    max_results: int = 100,
                    page_token: Optional[str] = None,
                    label_ids: Optional[List[str]] = None) -> Dict:
        """List email threads with sophisticated filtering"""
        try:
            normalized_query = self._normalize_search(folder, query or '')
            
            params = {
                'userId': 'me',
                'maxResults': max_results,
                'q': normalized_query['q'] if normalized_query['q'] else None,
                'pageToken': page_token
            }
            
            if folder == 'inbox' and label_ids:
                params['labelIds'] = label_ids
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            result = self.service.users().threads().list(**params).execute()
            
            threads = result.get('threads', [])
            
            return {
                'threads': [
                    {
                        'id': thread['id'],
                        'history_id': thread.get('historyId'),
                        'raw': thread
                    }
                    for thread in threads
                ],
                'next_page_token': result.get('nextPageToken')
            }
            
        except HttpError as error:
            logger.error(f"Error listing threads: {error}")
            raise
    
    def get_thread(self, thread_id: str) -> Dict:
        """Get complete thread with all messages parsed"""
        try:
            result = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            
            if not result.get('messages'):
                return {
                    'messages': [],
                    'latest': None,
                    'has_unread': False,
                    'total_replies': 0,
                    'labels': []
                }
            
            messages = []
            has_unread = False
            labels = set()
            
            for message in result['messages']:
                parsed_message = self._parse_message(message)
                messages.append(parsed_message)
                
                if not parsed_message.is_read:
                    has_unread = True
                
                for label in parsed_message.labels:
                    labels.add(label['id'])
            
            return {
                'messages': [msg.__dict__ for msg in messages],
                'latest': messages[-1].__dict__ if messages else None,
                'has_unread': has_unread,
                'total_replies': len(messages),
                'labels': [{'id': label_id, 'name': label_id} for label_id in labels]
            }
            
        except HttpError as error:
            logger.error(f"Error getting thread {thread_id}: {error}")
            raise
    
    def get_attachment(self, message_id: str, attachment_id: str) -> str:
        """Get attachment data"""
        try:
            result = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            data = result.get('data', '')
            # Convert from URL-safe base64 to regular base64
            return self._from_base64_url(data)
            
        except HttpError as error:
            logger.error(f"Error getting attachment: {error}")
            raise
    
    def mark_as_read(self, thread_ids: List[str]):
        """Mark threads as read"""
        self._modify_thread_labels(thread_ids, remove_label_ids=['UNREAD'])
    
    def mark_as_unread(self, thread_ids: List[str]):
        """Mark threads as unread"""
        self._modify_thread_labels(thread_ids, add_label_ids=['UNREAD'])
    
    def _parse_message(self, message: Dict) -> ParsedMessage:
        """Parse a Gmail message into structured format"""
        headers = message.get('payload', {}).get('headers', [])
        header_dict = {h['name'].lower(): h['value'] for h in headers}
        
        # Extract basic info
        message_id = message.get('id', '')
        thread_id = message.get('threadId', '')
        snippet = html.unescape(message.get('snippet', ''))
        label_ids = message.get('labelIds', [])
        
        # Parse headers
        subject = header_dict.get('subject', '(no subject)')
        sender = self._parse_email_address(header_dict.get('from', ''))
        to_addresses = self._parse_address_list(header_dict.get('to', ''))
        cc_addresses = self._parse_address_list(header_dict.get('cc', '')) if header_dict.get('cc') else None
        date = header_dict.get('date', '')
        
        # Extract body content
        body_text, body_html = self._extract_body_content(message['payload'])
        processed_html = self._process_html_content(body_html, message)
        
        # Parse attachments
        attachments = self._extract_attachments(message['payload'])
        
        # Message metadata
        is_read = 'UNREAD' not in label_ids
        is_starred = 'STARRED' in label_ids
        is_important = 'IMPORTANT' in label_ids
        is_draft = 'DRAFT' in label_ids
        
        # Check for TLS
        has_tls = self._check_tls_headers(headers)
        
        return ParsedMessage(
            id=message_id,
            thread_id=thread_id,
            subject=subject,
            sender=sender,
            to=to_addresses,
            cc=cc_addresses,
            bcc=None,  # BCC not available in received messages
            date=date,
            snippet=snippet,
            body_text=body_text,
            body_html=body_html,
            processed_html=processed_html,
            is_read=is_read,
            is_starred=is_starred,
            is_important=is_important,
            is_draft=is_draft,
            labels=[{'id': label, 'name': label, 'type': 'user'} for label in label_ids],
            attachments=attachments,
            message_id=header_dict.get('message-id'),
            reply_to=header_dict.get('reply-to'),
            references=header_dict.get('references'),
            in_reply_to=header_dict.get('in-reply-to'),
            list_unsubscribe=header_dict.get('list-unsubscribe'),
            has_tls=has_tls,
            raw_message=message
        )
    
    def _extract_body_content(self, payload: Dict) -> Tuple[str, str]:
        """Extract text and HTML body content"""
        body_text = ""
        body_html = ""
        
        def extract_from_parts(parts):
            nonlocal body_text, body_html
            for part in parts:
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                    body_text = self._decode_base64_data(part['body']['data'])
                elif mime_type == 'text/html' and part.get('body', {}).get('data'):
                    body_html = self._decode_base64_data(part['body']['data'])
                elif part.get('parts'):
                    extract_from_parts(part['parts'])
        
        if payload.get('parts'):
            extract_from_parts(payload['parts'])
        elif payload.get('body', {}).get('data'):
            data = self._decode_base64_data(payload['body']['data'])
            if payload.get('mimeType') == 'text/html':
                body_html = data
            else:
                body_text = data
        
        return body_text, body_html
    
    def _process_html_content(self, html_content: str, message: Dict) -> str:
        """Process HTML content including inline images"""
        if not html_content:
            return html_content
        
        processed_html = html_content
        
        # Handle inline images
        payload = message.get('payload', {})
        if payload.get('parts'):
            inline_images = self._find_inline_images(payload['parts'])
            
            for part in inline_images:
                content_id = self._get_content_id(part)
                if content_id and part.get('body', {}).get('attachmentId'):
                    try:
                        image_data = self.get_attachment(message['id'], part['body']['attachmentId'])
                        if image_data:
                            clean_content_id = content_id.strip('<>')
                            data_url = f"data:{part.get('mimeType', 'image/jpeg')};base64,{image_data}"
                            processed_html = re.sub(
                                f'cid:{re.escape(clean_content_id)}',
                                data_url,
                                processed_html
                            )
                    except Exception as e:
                        logger.warning(f"Failed to process inline image: {e}")
        
        return processed_html
    
    def _extract_attachments(self, payload: Dict) -> List[Attachment]:
        """Extract attachments from message payload"""
        attachments = []
        
        def find_attachments(parts):
            for part in parts:
                filename = part.get('filename', '')
                if filename and len(filename) > 0:
                    # Check if it's not an inline image
                    content_disposition = self._get_header_value(part.get('headers', []), 'content-disposition')
                    is_inline = content_disposition and 'inline' in content_disposition.lower()
                    has_content_id = self._get_content_id(part) is not None
                    
                    if not (is_inline and has_content_id):
                        attachment = Attachment(
                            filename=filename,
                            mime_type=part.get('mimeType', 'application/octet-stream'),
                            size=int(part.get('body', {}).get('size', 0)),
                            attachment_id=part.get('body', {}).get('attachmentId', ''),
                            headers=part.get('headers', [])
                        )
                        attachments.append(attachment)
                
                if part.get('parts'):
                    find_attachments(part['parts'])
        
        if payload.get('parts'):
            find_attachments(payload['parts'])
        
        return attachments
    
    def _find_inline_images(self, parts: List[Dict]) -> List[Dict]:
        """Find inline images in message parts"""
        inline_images = []
        
        for part in parts:
            content_disposition = self._get_header_value(part.get('headers', []), 'content-disposition')
            is_inline = content_disposition and 'inline' in content_disposition.lower()
            has_content_id = self._get_content_id(part) is not None
            
            if is_inline and has_content_id:
                inline_images.append(part)
            
            if part.get('parts'):
                inline_images.extend(self._find_inline_images(part['parts']))
        
        return inline_images
    
    def _get_content_id(self, part: Dict) -> Optional[str]:
        """Get content-id header from part"""
        return self._get_header_value(part.get('headers', []), 'content-id')
    
    def _get_header_value(self, headers: List[Dict], header_name: str) -> Optional[str]:
        """Get header value by name"""
        for header in headers:
            if header.get('name', '').lower() == header_name.lower():
                return header.get('value')
        return None
    
    def _parse_email_address(self, address_string: str) -> EmailAddress:
        """Parse email address string into EmailAddress object"""
        if not address_string:
            return EmailAddress(email='', name=None)
        
        name, email = parseaddr(address_string)
        return EmailAddress(email=email or '', name=name or None)
    
    def _parse_address_list(self, address_string: str) -> List[EmailAddress]:
        """Parse comma-separated email addresses"""
        if not address_string:
            return []
        
        addresses = getaddresses([address_string])
        return [EmailAddress(email=email, name=name or None) for name, email in addresses]
    
    def _check_tls_headers(self, headers: List[Dict]) -> bool:
        """Check if email was sent with TLS"""
        received_headers = [h['value'] for h in headers if h['name'].lower() == 'received']
        
        for received in received_headers:
            if any(tls_indicator in received.lower() for tls_indicator in ['tls', 'ssl', 'encrypted']):
                return True
        
        # Check for TLS-Report header
        return any(h['name'].lower() == 'tls-report' for h in headers)
    
    def _decode_base64_data(self, data: str) -> str:
        """Decode base64 URL-safe data"""
        try:
            # Convert URL-safe base64 to regular base64
            data = data.replace('-', '+').replace('_', '/')
            # Add padding if needed
            padding = 4 - len(data) % 4
            if padding != 4:
                data += '=' * padding
            
            decoded_bytes = base64.b64decode(data)
            return decoded_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Failed to decode base64 data: {e}")
            return ""
    
    def _from_base64_url(self, data: str) -> str:
        """Convert URL-safe base64 to regular base64"""
        data = data.replace('-', '+').replace('_', '/')
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return data
    
    def _normalize_search(self, folder: str, query: str) -> Dict[str, str]:
        """Normalize search parameters"""
        if folder != 'inbox':
            query = query.strip()
            
            if folder == 'bin':
                return {'folder': None, 'q': f'in:trash {query}'}
            elif folder == 'archive':
                return {'folder': None, 'q': f'in:archive AND ({query})'}
            elif folder == 'draft':
                return {'folder': None, 'q': f'is:draft AND ({query})'}
            
            return {'folder': folder, 'q': f'in:{folder} {query}' if folder.strip() else query}
        
        return {'folder': folder, 'q': query}
    
    def _modify_thread_labels(self, thread_ids: List[str], 
                             add_label_ids: Optional[List[str]] = None,
                             remove_label_ids: Optional[List[str]] = None):
        """Modify labels on threads"""
        if not thread_ids:
            return
        
        request_body = {}
        if add_label_ids:
            request_body['addLabelIds'] = add_label_ids
        if remove_label_ids:
            request_body['removeLabelIds'] = remove_label_ids
        
        # Process in chunks to avoid rate limits
        chunk_size = 15
        for i in range(0, len(thread_ids), chunk_size):
            chunk = thread_ids[i:i + chunk_size]
            
            for thread_id in chunk:
                try:
                    self.service.users().threads().modify(
                        userId='me',
                        id=thread_id,
                        body=request_body
                    ).execute()
                except HttpError as error:
                    logger.error(f"Error modifying thread {thread_id}: {error}")