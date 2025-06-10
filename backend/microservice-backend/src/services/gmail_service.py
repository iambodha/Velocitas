from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import uuid
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..database.models.connection import Connection
from ..database.models.email import Email, EmailThread, SyncStatus
from ..database.models.attachment import Attachment
from ..database.connection import get_db
from ..core.config import settings
from .email_service import EmailService

class GmailService:
    
    @staticmethod
    def get_gmail_service(connection: Connection):
        """Get authenticated Gmail service"""
        creds = Credentials(
            token=connection.access_token,
            refresh_token=connection.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET
        )
        
        # Refresh token if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
            # Update connection with new tokens
            with get_db() as db:
                connection.access_token = creds.token
                if creds.refresh_token:
                    connection.refresh_token = creds.refresh_token
                connection.token_expires_at = creds.expiry
                db.commit()
        
        return build('gmail', 'v1', credentials=creds)
    
    @staticmethod
    def initial_sync(connection_id: str):
        """Perform initial sync for a Gmail connection"""
        with get_db() as db:
            connection = db.query(Connection).filter(Connection.id == connection_id).first()
            if not connection:
                return
            
            # Mark as syncing
            connection.is_syncing = True
            db.commit()
            
            try:
                # Create sync status record
                sync_status = SyncStatus(
                    id=str(uuid.uuid4()),
                    connection_id=connection_id,
                    sync_type="full",
                    status="running"
                )
                db.add(sync_status)
                db.commit()
                
                service = GmailService.get_gmail_service(connection)
                
                # Get all messages (limited for initial sync)
                messages = GmailService.get_messages(service, max_results=1000)
                
                sync_status.total_emails = len(messages)
                db.commit()
                
                processed = 0
                new_emails = 0
                
                for message in messages:
                    try:
                        email_data = GmailService.parse_gmail_message(service, message['id'])
                        if email_data:
                            # Create or update email
                            email = EmailService.create_or_update_email(db, connection_id, email_data)
                            if email:
                                new_emails += 1
                        processed += 1
                        
                        # Update progress
                        sync_status.processed_emails = processed
                        db.commit()
                        
                    except Exception as e:
                        print(f"Error processing message {message['id']}: {e}")
                        sync_status.failed_emails += 1
                        continue
                
                # Complete sync
                sync_status.status = "completed"
                sync_status.new_emails = new_emails
                sync_status.completed_at = datetime.utcnow()
                
                connection.is_syncing = False
                connection.last_sync_at = datetime.utcnow()
                
                db.commit()
                
            except Exception as e:
                # Handle sync error
                sync_status.status = "failed"
                sync_status.error_message = str(e)
                sync_status.completed_at = datetime.utcnow()
                
                connection.is_syncing = False
                
                db.commit()
                print(f"Gmail sync failed: {e}")
    
    @staticmethod
    def sync_emails(connection_id: str):
        """Incremental sync for Gmail connection"""
        with get_db() as db:
            connection = db.query(Connection).filter(Connection.id == connection_id).first()
            if not connection or connection.is_syncing:
                return
            
            connection.is_syncing = True
            db.commit()
            
            try:
                service = GmailService.get_gmail_service(connection)
                
                # Get messages since last sync
                query = ""
                if connection.last_sync_at:
                    # Convert to Gmail date format
                    after_date = connection.last_sync_at.strftime("%Y/%m/%d")
                    query = f"after:{after_date}"
                
                messages = GmailService.get_messages(service, query=query)
                
                for message in messages:
                    try:
                        email_data = GmailService.parse_gmail_message(service, message['id'])
                        if email_data:
                            EmailService.create_or_update_email(db, connection_id, email_data)
                    except Exception as e:
                        print(f"Error syncing message {message['id']}: {e}")
                        continue
                
                connection.is_syncing = False
                connection.last_sync_at = datetime.utcnow()
                db.commit()
                
            except Exception as e:
                connection.is_syncing = False
                db.commit()
                print(f"Gmail incremental sync failed: {e}")
    
    @staticmethod
    def get_messages(service, query: str = "", max_results: int = 100) -> List[Dict]:
        """Get Gmail messages"""
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get additional pages if needed
            while 'nextPageToken' in results and len(messages) < max_results:
                page_token = results['nextPageToken']
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_results - len(messages),
                    pageToken=page_token
                ).execute()
                messages.extend(results.get('messages', []))
            
            return messages
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    @staticmethod
    def parse_gmail_message(service, message_id: str) -> Optional[Dict[str, Any]]:
        """Parse Gmail message into email data"""
        try:
            message = service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract email data
            email_data = {
                'message_id': message_id,
                'provider_message_id': message_id,
                'subject': headers.get('Subject', ''),
                'from_email': GmailService.extract_email(headers.get('From', '')),
                'from_name': GmailService.extract_name(headers.get('From', '')),
                'reply_to': headers.get('Reply-To'),
                'to_emails': GmailService.parse_email_list(headers.get('To', '')),
                'cc_emails': GmailService.parse_email_list(headers.get('Cc', '')),
                'bcc_emails': GmailService.parse_email_list(headers.get('Bcc', '')),
                'date_sent': GmailService.parse_date(headers.get('Date')),
                'date_received': datetime.now(timezone.utc),
                'provider_labels': message.get('labelIds', []),
                'size_bytes': message.get('sizeEstimate', 0),
                'snippet': message.get('snippet', '')
            }
            
            # Parse message body
            body_data = GmailService.parse_message_body(message['payload'])
            email_data.update(body_data)
            
            # Set status flags based on labels
            labels = message.get('labelIds', [])
            email_data['is_read'] = 'UNREAD' not in labels
            email_data['is_starred'] = 'STARRED' in labels
            email_data['is_important'] = 'IMPORTANT' in labels
            email_data['is_draft'] = 'DRAFT' in labels
            email_data['is_sent'] = 'SENT' in labels
            email_data['is_spam'] = 'SPAM' in labels
            email_data['is_archived'] = 'INBOX' not in labels
            
            # Handle attachments
            if 'parts' in message['payload']:
                attachments = GmailService.extract_attachments(message['payload']['parts'])
                email_data['has_attachments'] = len(attachments) > 0
                email_data['attachment_count'] = len(attachments)
            
            return email_data
            
        except HttpError as error:
            print(f"Error parsing message {message_id}: {error}")
            return None
    
    @staticmethod
    def parse_message_body(payload: Dict) -> Dict[str, str]:
        """Extract text and HTML body from message payload"""
        body_data = {'body_text': '', 'body_html': ''}
        
        def extract_body_recursive(parts):
            if 'parts' in parts:
                for part in parts['parts']:
                    extract_body_recursive(part)
            else:
                mime_type = parts.get('mimeType', '')
                body = parts.get('body', {})
                data = body.get('data', '')
                
                if data:
                    decoded_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    
                    if mime_type == 'text/plain':
                        body_data['body_text'] = decoded_data
                    elif mime_type == 'text/html':
                        body_data['body_html'] = decoded_data
        
        extract_body_recursive(payload)
        return body_data
    
    @staticmethod
    def extract_attachments(parts: List[Dict]) -> List[Dict]:
        """Extract attachment information from message parts"""
        attachments = []
        
        for part in parts:
            if part.get('filename'):
                attachment = {
                    'filename': part['filename'],
                    'content_type': part.get('mimeType', ''),
                    'size_bytes': part.get('body', {}).get('size', 0),
                    'provider_attachment_id': part.get('body', {}).get('attachmentId'),
                    'is_inline': 'inline' in part.get('headers', {}).get('Content-Disposition', '')
                }
                attachments.append(attachment)
        
        return attachments
    
    @staticmethod
    def send_email(
        connection: Connection,
        to_emails: List[str],
        subject: str,
        body_text: str = "",
        body_html: str = "",
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None
    ) -> Optional[str]:
        """Send email via Gmail"""
        try:
            service = GmailService.get_gmail_service(connection)
            
            # Create message
            if body_html:
                message = MIMEMultipart('alternative')
                if body_text:
                    message.attach(MIMEText(body_text, 'plain'))
                message.attach(MIMEText(body_html, 'html'))
            else:
                message = MIMEText(body_text or "")
            
            message['to'] = ', '.join(to_emails)
            message['from'] = connection.email
            message['subject'] = subject
            
            if cc_emails:
                message['cc'] = ', '.join(cc_emails)
            if bcc_emails:
                message['bcc'] = ', '.join(bcc_emails)
            
            # Send message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return result.get('id')
            
        except HttpError as error:
            print(f"Error sending email: {error}")
            return None
    
    @staticmethod
    def extract_email(email_string: str) -> str:
        """Extract email address from 'Name <email>' format"""
        if '<' in email_string and '>' in email_string:
            return email_string.split('<')[1].split('>')[0].strip()
        return email_string.strip()
    
    @staticmethod
    def extract_name(email_string: str) -> str:
        """Extract name from 'Name <email>' format"""
        if '<' in email_string:
            return email_string.split('<')[0].strip().strip('"')
        return ""
    
    @staticmethod
    def parse_email_list(email_string: str) -> List[str]:
        """Parse comma-separated email list"""
        if not email_string:
            return []
        
        emails = []
        for email_part in email_string.split(','):
            email_addr = GmailService.extract_email(email_part.strip())
            if email_addr:
                emails.append(email_addr)
        
        return emails
    
    @staticmethod
    def parse_date(date_string: str) -> Optional[datetime]:
        """Parse email date string to datetime"""
        if not date_string:
            return None
        
        try:
            # Gmail date format: "Wed, 23 Nov 2022 10:30:00 +0000"
            import email.utils
            timestamp = email.utils.parsedate_to_datetime(date_string)
            return timestamp.astimezone(timezone.utc)
        except:
            return None