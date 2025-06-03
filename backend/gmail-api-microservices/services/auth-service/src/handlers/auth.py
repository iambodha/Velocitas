# File: /gmail-api-microservices/gmail-api-microservices/services/auth-service/src/handlers/auth.py
#Tested

import base64
import json
import uuid
from datetime import datetime
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from sqlalchemy.orm import Session
from ..models.user import User
from ..database.db import get_db
from contextlib import contextmanager

@contextmanager
def get_db_context():
    """Database session context manager"""
    db = next(get_db())
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

class SecureCredentialManager:
    """Secure credential manager with PostgreSQL storage"""
    
    def __init__(self, encryption_key: str = None):
        import os
        self.encryption_key = encryption_key or os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
    
    def _encrypt_credentials(self, creds_dict: dict) -> str:
        """Encrypt credentials before storage"""
        import cryptography.fernet
        key = base64.urlsafe_b64encode(self.encryption_key.ljust(32)[:32].encode())
        f = cryptography.fernet.Fernet(key)
        return f.encrypt(json.dumps(creds_dict).encode()).decode()
    
    def _decrypt_credentials(self, encrypted_creds: str) -> dict:
        """Decrypt stored credentials"""
        import cryptography.fernet
        key = base64.urlsafe_b64encode(self.encryption_key.ljust(32)[:32].encode())
        f = cryptography.fernet.Fernet(key)
        return json.loads(f.decrypt(encrypted_creds.encode()).decode())
    
    def save_user_and_credentials(self, google_user_id: str, email: str, name: str, creds: Credentials):
        """Save or update user and their credentials securely"""
        with get_db_context() as db:
            # Check if user exists
            user = db.query(User).filter(User.google_user_id == google_user_id).first()
            
            # Prepare credentials dict
            creds_dict = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            encrypted_creds = self._encrypt_credentials(creds_dict)
            
            if user:
                # Update existing user
                user.email = email
                user.name = name
                user.encrypted_credentials = encrypted_creds
                user.credentials_updated_at = datetime.utcnow()
                user.last_login = datetime.utcnow()
                user.is_active = True
            else:
                # Create new user
                user = User(
                    google_user_id=google_user_id,
                    email=email,
                    name=name,
                    encrypted_credentials=encrypted_creds,
                    credentials_updated_at=datetime.utcnow(),
                    last_login=datetime.utcnow()
                )
                db.add(user)
            
            db.flush()
            return str(user.id)
    
    def load_credentials(self, user_id: str) -> Optional[Credentials]:
        """Load and decrypt user credentials"""
        with get_db_context() as db:
            user = db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user or not user.encrypted_credentials:
                return None
            
            try:
                creds_data = self._decrypt_credentials(user.encrypted_credentials)
                
                creds = Credentials(
                    token=creds_data['token'],
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri=creds_data['token_uri'],
                    client_id=creds_data['client_id'],
                    client_secret=creds_data['client_secret'],
                    scopes=creds_data['scopes']
                )
                
                # Refresh if expired
                if creds.expired and creds.refresh_token:
                    creds.refresh(GoogleRequest())
                    self._update_credentials(user_id, creds)
                
                return creds
            except Exception as e:
                print(f"Error loading credentials for user {user_id}: {e}")
                return None
    
    def _update_credentials(self, user_id: str, creds: Credentials):
        """Update existing user credentials"""
        with get_db_context() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                creds_dict = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes,
                    'updated_at': datetime.utcnow().isoformat()
                }
                user.encrypted_credentials = self._encrypt_credentials(creds_dict)
                user.credentials_updated_at = datetime.utcnow()
    
    def get_user_by_google_id(self, google_user_id: str) -> Optional[User]:
        """Get user by Google ID"""
        with get_db_context() as db:
            return db.query(User).filter(
                User.google_user_id == google_user_id,
                User.is_active == True
            ).first()
    
    def deactivate_user(self, user_id: str):
        """Deactivate user instead of deleting"""
        with get_db_context() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                user.encrypted_credentials = None