import base64
import os
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from models import Email, Attachment, User, DatabaseSession
import asyncio

# OAuth scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Authenticate with Gmail API"""
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=8080)
    return build('gmail', 'v1', credentials=creds)

def get_or_create_user(service, session):
    """Get or create user based on Gmail profile"""
    try:
        # Get user's Gmail profile
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile['emailAddress']
        
        # Check if user exists
        user = session.query(User).filter(User.email == email_address).first()
        
        if not user:
            print(f"Creating new user for {email_address}")
            user = User(
                email=email_address,
                name=email_address.split('@')[0],  # Use email prefix as name
                created_at=datetime.utcnow(),
                is_active=True
            )
            session.add(user)
            session.commit()
            print(f"✅ Created user: {email_address}")
        else:
            # Update last login
            user.last_login = datetime.utcnow()
            session.commit()
            print(f"✅ Found existing user: {email_address}")
        
        return user
        
    except Exception as e:
        print(f"Error getting user profile: {e}")
        raise

def get_messages(service):
    """Get list of messages"""
    results = service.users().messages().list(userId='me', maxResults=100).execute()
    return results.get('messages', [])

def get_full_message(service, msg_id):
    """Get full message details"""
    return service.users().messages().get(userId='me', id=msg_id, format='full').execute()

def extract_payload(payload, content_type='text/html'):
    """Extract email body content - improved version"""
    def extract_from_part(part, target_type):
        if part.get('mimeType') == target_type:
            body_data = part.get('body', {}).get('data')
            if body_data:
                try:
                    return base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                except Exception as e:
                    print(f"Error decoding {target_type}: {e}")
                    return ""
        return None
    
    # First check if this part itself has the content
    content = extract_from_part(payload, content_type)
    if content:
        return content
    
    # If not, check all parts recursively
    if 'parts' in payload:
        for part in payload['parts']:
            # Check this part
            content = extract_from_part(part, content_type)
            if content:
                return content
            
            # If this part has nested parts, check them too
            if 'parts' in part:
                content = extract_payload(part, content_type)
                if content:
                    return content
    
    return ""

def convert_gmail_b64_to_standard_b64(gmail_b64_data):
    """Convert Gmail's base64url to standard base64"""
    if not gmail_b64_data:
        return ''
    
    # Replace base64url characters with standard base64
    standard_b64 = gmail_b64_data.replace('-', '+').replace('_', '/')
    
    # Add padding if needed
    missing_padding = len(standard_b64) % 4
    if missing_padding:
        standard_b64 += '=' * (4 - missing_padding)
    
    return standard_b64

def get_attachments(service, msg):
    """Get email attachments"""
    attachments = []
    for part in msg['payload'].get('parts', []):
        if part['filename'] and part.get('body', {}).get('attachmentId'):
            att_id = part['body']['attachmentId']
            try:
                att = service.users().messages().attachments().get(
                    userId='me', messageId=msg['id'], id=att_id).execute()
                
                # Convert Gmail's base64url to standard base64
                standard_b64_data = convert_gmail_b64_to_standard_b64(att['data'])
                
                attachments.append({
                    'id': att_id,
                    'filename': part['filename'],
                    'mimeType': part['mimeType'],
                    'data': standard_b64_data  # Now properly formatted
                })
            except Exception as e:
                print(f"Error getting attachment {att_id}: {e}")
                continue
    
    return attachments

def download_emails_for_user():
    """Main function to download emails for authenticated user"""
    print("🔐 Starting Gmail authentication...")
    service = authenticate_gmail()
    session = DatabaseSession()
    
    try:
        # Get or create user
        user = get_or_create_user(service, session)
        print(f"📧 Fetching emails for user: {user.email}")
        
        for msg_meta in get_messages(service):
            msg = get_full_message(service, msg_meta['id'])
            headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
            subject = headers.get('Subject', '(No Subject)')
            sender = headers.get('From', '')
            to = headers.get('To', '')
            snippet = msg.get('snippet', '')
            labels = ",".join(msg.get('labelIds', []))
            internal_date = datetime.fromtimestamp(int(msg.get('internalDate', '0')) / 1000)

            # Check if email already exists for this user
            existing_email = session.query(Email).filter(
                Email.id == msg['id'],
                Email.user_id == user.id
            ).first()
            
            if existing_email:
                # Email exists - check if labels have changed and update if needed
                current_labels = ",".join(msg.get('labelIds', []))
                if existing_email.label_ids != current_labels:
                    print(f"📧 Updating labels for existing email: {subject[:30]}...")
                    update_existing_email_from_labels(msg['id'], msg.get('labelIds', []), session)
                else:
                    print(f"📧 Email already exists and up-to-date: {subject[:30]}...")
                continue

            # Get HTML and plain body - fixed extraction
            html_body = extract_payload(msg['payload'], 'text/html')
            plain_body = extract_payload(msg['payload'], 'text/plain')
            
            # Parse Gmail labels to extract status information
            label_info = parse_gmail_labels(msg.get('labelIds', []))
            
            # Debug print to see what we're getting
            print(f"Email: {subject[:30]}... | HTML: {len(html_body)} chars | Plain: {len(plain_body)} chars")
            print(f"Labels: {labels} | Starred: {label_info['is_starred']} | Read: {label_info['is_read']} | Category: {label_info['category']} | Urgency: {label_info['urgency']}")

            # Save email with user association and parsed label information
            email = Email(
                id=msg['id'],
                user_id=user.id,  # Associate with user
                thread_id=msg['threadId'],
                subject=subject,
                sender=sender,
                recipients=to,
                snippet=snippet,
                html_body=html_body,
                plain_body=plain_body,
                category=label_info['category'],
                is_starred=label_info['is_starred'],
                is_read=label_info['is_read'],
                urgency=label_info['urgency'],
                label_ids=labels,
                internal_date=internal_date
            )
            session.add(email)

            # Save attachments with user association
            for att in get_attachments(service, msg):
                attachment = Attachment(
                    id=att['id'],
                    user_id=user.id,  # Associate with user
                    email_id=msg['id'],
                    filename=att['filename'],
                    mime_type=att['mimeType'],
                    data=att['data']  # Now properly converted
                )
                session.add(attachment)

            session.commit()
            print(f"✅ Saved: {subject[:50]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()
    
    print("✅ All emails and attachments saved to PostgreSQL.")

async def sync_emails_async(user_id):
    """
    Asynchronous version of sync_emails function
    Start email synchronization process for a user in an async context
    
    Args:
        user_id: The ID of the user whose emails to sync
        
    Returns:
        None - operates as a background task
    """
    # Execute the synchronous function in a thread pool to not block the event loop
    return await asyncio.to_thread(sync_emails_for_user, user_id)

def sync_emails_for_user(user_id):
    """Sync emails for a specific user"""
    
    print(f"🔐 Starting Gmail sync for user: {user_id}")
    
    # Note: In production, you would need to implement proper OAuth flow
    # For now, this assumes the user has already authenticated with Google
    # and you have stored their credentials securely
    
    try:
        session = DatabaseSession()
        
        # Get user
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ User not found: {user_id}")
            return
        
        # For now, we'll use the existing Gmail authentication
        # In production, you'd need to implement proper OAuth token management
        service = authenticate_gmail()
        
        # Download emails for the specific user
        download_emails_for_user_with_service(service, user, session)
        
    except Exception as e:
        print(f"❌ Error syncing emails for user {user_id}: {e}")
    finally:
        if 'session' in locals():
            session.close()

def download_emails_for_user_with_service(service, user, session):
    """Download emails for a specific user with Gmail service"""
    print(f"📧 Fetching emails for user: {user.email}")
    
    try:
        for msg_meta in get_messages(service):
            msg = get_full_message(service, msg_meta['id'])
            headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
            subject = headers.get('Subject', '(No Subject)')
            sender = headers.get('From', '')
            to = headers.get('To', '')
            snippet = msg.get('snippet', '')
            labels = ",".join(msg.get('labelIds', []))
            internal_date = datetime.fromtimestamp(int(msg.get('internalDate', '0')) / 1000)

            # Check if email already exists for this user
            existing_email = session.query(Email).filter(
                Email.id == msg['id'],
                Email.user_id == user.id
            ).first()
            
            if existing_email:
                # Email exists - check if labels have changed and update if needed
                current_labels = ",".join(msg.get('labelIds', []))
                if existing_email.label_ids != current_labels:
                    print(f"📧 Updating labels for existing email: {subject[:30]}...")
                    update_existing_email_from_labels(msg['id'], msg.get('labelIds', []), session)
                else:
                    print(f"📧 Email already exists and up-to-date: {subject[:30]}...")
                continue

            # Get HTML and plain body
            html_body = extract_payload(msg['payload'], 'text/html')
            plain_body = extract_payload(msg['payload'], 'text/plain')
            
            # Parse Gmail labels to extract status information
            label_info = parse_gmail_labels(msg.get('labelIds', []))
            
            print(f"Email: {subject[:30]}... | HTML: {len(html_body)} chars | Plain: {len(plain_body)} chars")
            print(f"Labels: {labels} | Starred: {label_info['is_starred']} | Read: {label_info['is_read']} | Category: {label_info['category']} | Urgency: {label_info['urgency']}")

            # Save email with user association and parsed label information
            email = Email(
                id=msg['id'],
                user_id=user.id,
                thread_id=msg['threadId'],
                subject=subject,
                sender=sender,
                recipients=to,
                snippet=snippet,
                html_body=html_body,
                plain_body=plain_body,
                category=label_info['category'],
                is_starred=label_info['is_starred'],
                is_read=label_info['is_read'],
                urgency=label_info['urgency'],
                label_ids=labels,
                internal_date=internal_date
            )
            session.add(email)

            # Save attachments with user association
            for att in get_attachments(service, msg):
                attachment = Attachment(
                    id=att['id'],
                    user_id=user.id,
                    email_id=msg['id'],
                    filename=att['filename'],
                    mime_type=att['mimeType'],
                    data=att['data']
                )
                session.add(attachment)

            session.commit()
            print(f"✅ Saved: {subject[:50]}...")

    except Exception as e:
        print(f"❌ Error downloading emails: {e}")
        session.rollback()
        raise

def parse_gmail_labels(label_ids):
    """Parse Gmail labels and extract status information"""
    labels = label_ids if isinstance(label_ids, list) else label_ids.split(',')
    
    # Check for starred status
    is_starred = 'STARRED' in labels
    
    # Check for read status (UNREAD label means it's unread, absence means it's read)
    is_read = 'UNREAD' not in labels
    
    # Determine category based on Gmail labels
    category = 'INBOX'  # default
    if 'SPAM' in labels:
        category = 'SPAM'
    elif 'CATEGORY_PROMOTIONS' in labels:
        category = 'PROMOTIONS'
    elif 'CATEGORY_SOCIAL' in labels:
        category = 'SOCIAL'
    elif 'CATEGORY_UPDATES' in labels:
        category = 'UPDATES'
    elif 'CATEGORY_FORUMS' in labels:
        category = 'FORUMS'
    elif 'CATEGORY_PERSONAL' in labels:
        category = 'PERSONAL'
    elif 'IMPORTANT' in labels:
        category = 'IMPORTANT'
    elif 'SENT' in labels:
        category = 'SENT'
    elif 'DRAFT' in labels:
        category = 'DRAFT'
    
    # Determine urgency based on labels (basic logic)
    urgency = 50  # default
    if 'IMPORTANT' in labels:
        urgency = 80
    elif 'CATEGORY_PROMOTIONS' in labels:
        urgency = 20
    elif 'SPAM' in labels:
        urgency = 10
    elif 'CATEGORY_PERSONAL' in labels:
        urgency = 70
    elif 'CATEGORY_UPDATES' in labels:
        urgency = 40
    
    return {
        'is_starred': is_starred,
        'is_read': is_read,
        'category': category,
        'urgency': urgency
    }

def update_existing_email_from_labels(email_id, label_ids, session):
    """Update an existing email's fields based on current Gmail labels"""
    try:
        email = session.query(Email).filter(Email.id == email_id).first()
        if not email:
            return False
        
        # Parse the current labels
        label_info = parse_gmail_labels(label_ids)
        
        # Update the email fields
        email.is_starred = label_info['is_starred']
        email.is_read = label_info['is_read']
        email.category = label_info['category']
        email.urgency = label_info['urgency']
        email.label_ids = ",".join(label_ids) if isinstance(label_ids, list) else label_ids
        
        session.commit()
        return True
        
    except Exception as e:
        print(f"Error updating email {email_id}: {e}")
        session.rollback()
        return False

# Only run when called directly
if __name__ == '__main__':
    download_emails_for_user()