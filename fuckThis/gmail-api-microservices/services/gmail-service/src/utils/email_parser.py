# gmail-api-microservices/services/gmail-service/src/utils/email_parser.py
import base64
import re
import html
from typing import Dict, List, Optional, Tuple, Any
from email.utils import parseaddr, getaddresses
from email.header import decode_header
import logging

logger = logging.getLogger(__name__)

class EmailParser:
    """Sophisticated email parsing utilities"""
    
    @staticmethod
    def extract_email_headers(headers: List[Dict]) -> Dict[str, str]:
        """Extract and normalize common email headers"""
        header_dict = {}
        
        important_headers = [
            'subject', 'from', 'to', 'date', 'cc', 'bcc', 'reply-to',
            'message-id', 'in-reply-to', 'references', 'list-unsubscribe',
            'list-unsubscribe-post', 'content-type', 'content-disposition'
        ]
        
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            
            if name in important_headers:
                # Decode header if it contains encoded words
                decoded_value = EmailParser._decode_header_value(value)
                header_dict[name] = decoded_value
        
        return header_dict
    
    @staticmethod
    def _decode_header_value(value: str) -> str:
        """Decode RFC 2047 encoded header values"""
        try:
            decoded_parts = decode_header(value)
            decoded_string = ''
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding, errors='replace')
                    else:
                        decoded_string += part.decode('utf-8', errors='replace')
                else:
                    decoded_string += part
            
            return decoded_string
        except Exception as e:
            logger.warning(f"Failed to decode header value: {e}")
            return value
    
    @staticmethod
    def extract_body_content(payload: Dict) -> Tuple[str, str, Dict[str, Any]]:
        """Extract body content with metadata"""
        body_text = ""
        body_html = ""
        metadata = {
            'has_html': False,
            'has_text': False,
            'encoding': 'utf-8',
            'content_type': 'text/plain'
        }
        
        def process_part(part: Dict, level: int = 0) -> None:
            nonlocal body_text, body_html, metadata
            
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                if part.get('body', {}).get('data'):
                    body_text = EmailParser._decode_base64_content(part['body']['data'])
                    metadata['has_text'] = True
                    
            elif mime_type == 'text/html':
                if part.get('body', {}).get('data'):
                    body_html = EmailParser._decode_base64_content(part['body']['data'])
                    metadata['has_html'] = True
                    metadata['content_type'] = 'text/html'
            
            # Process nested parts
            if part.get('parts'):
                for sub_part in part['parts']:
                    process_part(sub_part, level + 1)
        
        if payload.get('parts'):
            for part in payload['parts']:
                process_part(part)
        else:
            # Single part message
            if payload.get('body', {}).get('data'):
                content = EmailParser._decode_base64_content(payload['body']['data'])
                mime_type = payload.get('mimeType', 'text/plain')
                
                if mime_type == 'text/html':
                    body_html = content
                    metadata['has_html'] = True
                    metadata['content_type'] = 'text/html'
                else:
                    body_text = content
                    metadata['has_text'] = True
        
        # If we only have HTML, create a text version
        if body_html and not body_text:
            body_text = EmailParser._html_to_text(body_html)
            metadata['has_text'] = True
        
        return body_text, body_html, metadata
    
    @staticmethod
    def _decode_base64_content(data: str) -> str:
        """Decode base64 URL-safe content"""
        try:
            # Convert URL-safe base64 to regular base64
            data = data.replace('-', '+').replace('_', '/')
            
            # Add padding if needed
            padding = 4 - len(data) % 4
            if padding != 4:
                data += '=' * padding
            
            decoded_bytes = base64.b64decode(data)
            
            # Try to decode as UTF-8, fall back to latin-1
            try:
                return decoded_bytes.decode('utf-8')
            except UnicodeDecodeError:
                return decoded_bytes.decode('latin-1', errors='replace')
                
        except Exception as e:
            logger.warning(f"Failed to decode base64 content: {e}")
            return ""
    
    @staticmethod
    def _html_to_text(html_content: str) -> str:
        """Convert HTML to plain text"""
        if not html_content:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    @staticmethod
    def extract_message_metadata(msg: Dict) -> Dict[str, Any]:
        """Extract comprehensive message metadata"""
        label_ids = msg.get('labelIds', [])
        
        metadata = {
            'is_read': 'UNREAD' not in label_ids,
            'is_starred': 'STARRED' in label_ids,
            'is_important': 'IMPORTANT' in label_ids,
            'is_draft': 'DRAFT' in label_ids,
            'is_sent': 'SENT' in label_ids,
            'is_inbox': 'INBOX' in label_ids,
            'is_spam': 'SPAM' in label_ids,
            'is_trash': 'TRASH' in label_ids,
            'label_count': len(label_ids),
            'labels': label_ids,
            'size_estimate': msg.get('sizeEstimate', 0),
            'internal_date': msg.get('internalDate'),
            'thread_id': msg.get('threadId'),
            'message_id': msg.get('id')
        }
        
        return metadata
    
    @staticmethod
    def parse_email_addresses(address_string: str) -> List[Dict[str, str]]:
        """Parse email address string into structured format"""
        if not address_string:
            return []
        
        try:
            addresses = getaddresses([address_string])
            parsed_addresses = []
            
            for name, email in addresses:
                if email:  # Only include if email is present
                    parsed_addresses.append({
                        'email': email.strip(),
                        'name': name.strip() if name else None,
                        'display': f"{name} <{email}>" if name else email
                    })
            
            return parsed_addresses
            
        except Exception as e:
            logger.warning(f"Failed to parse email addresses: {e}")
            return [{'email': address_string, 'name': None, 'display': address_string}]
    
    @staticmethod
    def extract_attachments_info(payload: Dict) -> List[Dict[str, Any]]:
        """Extract attachment information"""
        attachments = []
        
        def find_attachments(parts: List[Dict], level: int = 0) -> None:
            for part in parts:
                filename = part.get('filename', '')
                
                if filename:
                    # Get content disposition to check if it's an attachment
                    headers = part.get('headers', [])
                    content_disposition = None
                    content_id = None
                    
                    for header in headers:
                        if header.get('name', '').lower() == 'content-disposition':
                            content_disposition = header.get('value', '')
                        elif header.get('name', '').lower() == 'content-id':
                            content_id = header.get('value', '')
                    
                    is_inline = content_disposition and 'inline' in content_disposition.lower()
                    is_attachment = content_disposition and 'attachment' in content_disposition.lower()
                    
                    # Include if it's explicitly an attachment or has filename but no inline disposition
                    if is_attachment or (filename and not is_inline):
                        attachment_info = {
                            'filename': filename,
                            'mime_type': part.get('mimeType', 'application/octet-stream'),
                            'size': int(part.get('body', {}).get('size', 0)),
                            'attachment_id': part.get('body', {}).get('attachmentId'),
                            'content_id': content_id,
                            'is_inline': is_inline,
                            'headers': headers,
                            'part_id': part.get('partId')
                        }
                        attachments.append(attachment_info)
                
                # Process nested parts
                if part.get('parts'):
                    find_attachments(part['parts'], level + 1)
        
        if payload.get('parts'):
            find_attachments(payload['parts'])
        
        return attachments
    
    @staticmethod
    def extract_security_info(headers: List[Dict]) -> Dict[str, Any]:
        """Extract security-related information from headers"""
        security_info = {
            'has_tls': False,
            'spf_result': None,
            'dkim_result': None,
            'dmarc_result': None,
            'authentication_results': [],
            'received_spf': None
        }
        
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            
            if name == 'received':
                # Check for TLS indicators in Received headers
                if any(tls_indicator in value.lower() for tls_indicator in ['tls', 'ssl', 'esmtps']):
                    security_info['has_tls'] = True
            
            elif name == 'authentication-results':
                security_info['authentication_results'].append(value)
                
                # Extract specific results
                if 'spf=' in value.lower():
                    spf_match = re.search(r'spf=(\w+)', value.lower())
                    if spf_match:
                        security_info['spf_result'] = spf_match.group(1)
                
                if 'dkim=' in value.lower():
                    dkim_match = re.search(r'dkim=(\w+)', value.lower())
                    if dkim_match:
                        security_info['dkim_result'] = dkim_match.group(1)
                
                if 'dmarc=' in value.lower():
                    dmarc_match = re.search(r'dmarc=(\w+)', value.lower())
                    if dmarc_match:
                        security_info['dmarc_result'] = dmarc_match.group(1)
            
            elif name == 'received-spf':
                security_info['received_spf'] = value
        
        return security_info
    
    @staticmethod
    def clean_subject(subject: str) -> str:
        """Clean and normalize email subject"""
        if not subject:
            return "(no subject)"
        
        # Remove extra quotes and whitespace
        cleaned = subject.replace('"', '').strip()
        
        # Decode HTML entities
        cleaned = html.unescape(cleaned)
        
        return cleaned if cleaned else "(no subject)"