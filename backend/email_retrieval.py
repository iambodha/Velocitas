import base64
from models import Email, Attachment, DatabaseSession
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

# Assuming you have an async version of your database session
# You'll need to update your models.py with an async engine configuration
# For now, I'll use a function to simulate async behavior with the existing synchronous functions

async def get_email_by_id_async(email_id, user_id=None):
    """Asynchronous version of get_email_by_id"""
    # This is a placeholder implementation. In production, use a proper async database connection
    return await asyncio.to_thread(get_email_by_id, email_id, user_id)

async def get_attachment_data_async(attachment_id, user_id=None):
    """Asynchronous version of get_attachment_data"""
    # This is a placeholder implementation. In production, use a proper async database connection
    return await asyncio.to_thread(get_attachment_data, attachment_id)

async def search_emails_async(query=None, limit=50, user_id=None):
    """Asynchronous version of search_emails"""
    # This is a placeholder implementation. In production, use a proper async database connection
    def _search_with_user():
        session = DatabaseSession()
        try:
            emails_query = session.query(Email)
            
            if user_id:
                emails_query = emails_query.filter(Email.user_id == user_id)
                
            if query:
                emails_query = emails_query.filter(
                    Email.subject.ilike(f'%{query}%') |
                    Email.sender.ilike(f'%{query}%') |
                    Email.recipients.ilike(f'%{query}%') |
                    Email.snippet.ilike(f'%{query}%') |
                    Email.html_body.ilike(f'%{query}%') |
                    Email.plain_body.ilike(f'%{query}%')
                )
            
            emails = emails_query.order_by(Email.internal_date.desc()).limit(limit).all()
            
            return [
                {
                    'id': email.id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'snippet': email.snippet,
                    'internal_date': email.internal_date.isoformat(),
                    'category': email.category,
                    'is_starred': email.is_starred,
                    'is_read': email.is_read,
                    'urgency': email.urgency
                }
                for email in emails
            ]
        finally:
            session.close()
    
    return await asyncio.to_thread(_search_with_user)

async def get_user_emails_async(user_id, limit=50, offset=0):
    """Asynchronous version of get_user_emails"""
    # This is a placeholder implementation. In production, use a proper async database connection
    return await asyncio.to_thread(get_user_emails, user_id, limit, offset)

def safe_b64decode_size(data):
    """Safely calculate base64 decoded size with error handling"""
    if not data:
        return 0
    try:
        # Fix padding if needed
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return len(base64.b64decode(data))
    except Exception as e:
        print(f"Error decoding base64 data: {e}")
        return 0

def safe_b64decode(data):
    """Safely decode base64 data with error handling"""
    if not data:
        return b''
    try:
        # Fix padding if needed
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return base64.b64decode(data)
    except Exception as e:
        print(f"Error decoding base64 data: {e}")
        return b''

def get_email_by_id(email_id, user_id=None):
    """
    Retrieve a complete email with attachments and threading information
    """
    session = DatabaseSession()
    try:
        # Build query with optional user filtering
        query = session.query(Email).filter(Email.id == email_id)
        if user_id:
            query = query.filter(Email.user_id == user_id)
        
        email = query.first()
        if not email:
            return None
        
        # Get attachments
        attachments = session.query(Attachment).filter(
            Attachment.email_id == email_id,
            Attachment.user_id == email.user_id  # Ensure user consistency
        ).all()
        
        # Get thread emails (emails with same thread_id) - sorted by date
        thread_emails = session.query(Email).filter(
            Email.thread_id == email.thread_id,
            Email.user_id == email.user_id  # Filter by same user
        ).order_by(Email.internal_date.asc()).all()
        
        # Format the response
        email_data = {
            'id': email.id,
            'user_id': str(email.user_id),
            'thread_id': email.thread_id,
            'subject': email.subject,
            'sender': email.sender,
            'recipients': email.recipients,
            'snippet': email.snippet,
            'html_body': email.html_body,
            'plain_body': email.plain_body,
            'category': email.category,
            'is_starred': email.is_starred,
            'is_read': email.is_read,
            'urgency': email.urgency,
            'label_ids': email.label_ids.split(',') if email.label_ids else [],
            'internal_date': email.internal_date.isoformat(),
            'attachments': [
                {
                    'id': att.id,
                    'filename': att.filename,
                    'mime_type': att.mime_type,
                    'size': safe_b64decode_size(att.data)
                }
                for att in attachments
            ],
            'thread_emails': [
                {
                    'id': thread_email.id,
                    'subject': thread_email.subject,
                    'sender': thread_email.sender,
                    'recipients': thread_email.recipients,
                    'snippet': thread_email.snippet,
                    'html_body': thread_email.html_body,
                    'plain_body': thread_email.plain_body,
                    'internal_date': thread_email.internal_date.isoformat(),
                    'is_current': thread_email.id == email_id,
                    'category': thread_email.category,
                    'is_starred': thread_email.is_starred,
                    'is_read': thread_email.is_read,
                    'urgency': thread_email.urgency
                }
                for thread_email in thread_emails
            ]
        }
        
        return email_data
    
    finally:
        session.close()

def get_attachment_data(attachment_id):
    """
    Retrieve attachment data for download
    """
    session = DatabaseSession()
    try:
        attachment = session.query(Attachment).filter(Attachment.id == attachment_id).first()
        if not attachment:
            return None
        
        return {
            'filename': attachment.filename,
            'mime_type': attachment.mime_type,
            'data': safe_b64decode(attachment.data)
        }
    
    finally:
        session.close()

def search_emails(query=None, limit=50):
    """
    Search emails by subject, sender, recipients, or content
    """
    session = DatabaseSession()
    try:
        emails_query = session.query(Email)
        
        if query:
            emails_query = emails_query.filter(
                Email.subject.ilike(f'%{query}%') |
                Email.sender.ilike(f'%{query}%') |
                Email.recipients.ilike(f'%{query}%') |
                Email.snippet.ilike(f'%{query}%') |
                Email.html_body.ilike(f'%{query}%') |
                Email.plain_body.ilike(f'%{query}%')
            )
        
        emails = emails_query.order_by(Email.internal_date.desc()).limit(limit).all()
        
        return [
            {
                'id': email.id,
                'subject': email.subject,
                'sender': email.sender,
                'snippet': email.snippet,
                'internal_date': email.internal_date.isoformat(),
                'category': email.category,
                'is_starred': email.is_starred,
                'is_read': email.is_read,
                'urgency': email.urgency
            }
            for email in emails
        ]
    
    finally:
        session.close()

def get_user_emails(user_id, limit=50, offset=0):
    """Get emails for a specific user"""
    session = DatabaseSession()
    try:
        emails = session.query(Email).filter(
            Email.user_id == user_id
        ).order_by(
            Email.internal_date.desc()
        ).offset(offset).limit(limit).all()
        
        return [
            {
                'id': email.id,
                'thread_id': email.thread_id,
                'subject': email.subject,
                'sender': email.sender,
                'snippet': email.snippet,
                'internal_date': email.internal_date.isoformat(),
                'category': email.category,
                'is_starred': email.is_starred,
                'is_read': email.is_read,
                'urgency': email.urgency
            }
            for email in emails
        ]
    finally:
        session.close()