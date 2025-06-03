# File: /gmail-api-microservices/gmail-api-microservices/services/gmail-service/src/handlers/gmail_api.py

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from typing import List, Dict

class GmailAPIHandler:
    """Handle Gmail API interactions"""
    
    def create_credentials_from_dict(self, creds_data: dict) -> Credentials:
        """Create credentials object from dictionary"""
        return Credentials(
            token=creds_data['token'],
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
    
    def fetch_emails(self, credentials: Credentials, limit: int = 50) -> List[Dict]:
        """Fetch emails from Gmail API"""
        service = build('gmail', 'v1', credentials=credentials)
        
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
                    id=message['id'],
                    format='full'
                ).execute()
                
                email_data = self._extract_email_data(msg)
                email_list.append(email_data)
                
            except Exception as e:
                print(f"Error processing message {message['id']}: {e}")
                continue
        
        return email_list
    
    def _extract_email_data(self, msg: dict) -> dict:
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