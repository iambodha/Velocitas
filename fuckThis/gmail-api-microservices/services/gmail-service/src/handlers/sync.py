# File: /gmail-api-microservices/gmail-api-microservices/services/gmail-service/src/handlers/sync.py

import httpx
import os
from .gmail_api import GmailAPIHandler

class EmailSyncHandler:
    """Handle email synchronization"""
    
    def __init__(self):
        self.gmail_handler = GmailAPIHandler()
        self.email_service_url = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:5002')
    
    async def sync_user_emails(self, user_id: str, credentials_data: dict, limit: int = 50):
        """Sync emails for a user"""
        try:
            # Create credentials
            credentials = self.gmail_handler.create_credentials_from_dict(credentials_data)
            
            # Fetch emails from Gmail
            email_list = self.gmail_handler.fetch_emails(credentials, limit)
            
            # Save emails via email service
            if email_list:
                await self._save_emails_to_service(user_id, email_list)
                print(f"Synced {len(email_list)} emails for user {user_id}")
            
        except Exception as e:
            print(f"Error syncing emails for user {user_id}: {e}")
    
    async def initial_user_sync(self, user_id: str, credentials_data: dict):
        """Initial sync for new users"""
        await self.sync_user_emails(user_id, credentials_data, limit=100)
    
    async def _save_emails_to_service(self, user_id: str, email_list: list):
        """Save emails via email service"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.email_service_url}/emails/bulk",
                headers={"X-User-ID": user_id},
                json={"emails": email_list}
            )
            
            if response.status_code != 200:
                print(f"Failed to save emails: {response.text}")