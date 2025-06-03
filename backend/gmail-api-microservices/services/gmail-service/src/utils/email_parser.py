# gmail-api-microservices/services/gmail-service/src/utils/email_parser.py
import base64
from typing import Dict, Tuple

def extract_email_headers(headers: list) -> Dict[str, str]:
    """Extract common email headers"""
    header_dict = {}
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        
        if name in ['subject', 'from', 'to', 'date', 'cc', 'bcc']:
            header_dict[name] = value
    
    return header_dict

def extract_body_content(payload: dict) -> Tuple[str, str]:
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

def extract_message_metadata(msg: dict) -> Dict[str, bool]:
    """Extract message metadata like read status, starred, etc."""
    label_ids = msg.get('labelIds', [])
    
    return {
        'is_read': 'UNREAD' not in label_ids,
        'is_starred': 'STARRED' in label_ids,
        'is_important': 'IMPORTANT' in label_ids,
        'is_draft': 'DRAFT' in label_ids
    }