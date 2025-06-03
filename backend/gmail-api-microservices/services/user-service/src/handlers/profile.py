# File: /gmail-api-microservices/gmail-api-microservices/services/user-service/src/handlers/profile.py

import httpx
import os
from typing import Optional, Dict
from ..database.db import get_db
from ..models.user import User

class UserProfileHandler:
    """Handle user profile operations"""
    
    def __init__(self):
        self.email_service_url = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:5002')
    
    async def get_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile with email stats"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return None
            
            # Get email stats from email service
            email_stats = await self._get_email_stats(user_id)
            
            return {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "email_stats": email_stats
            }
    
    async def update_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Update user profile"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return False
            
            # Update allowed fields
            if 'name' in profile_data:
                user.name = profile_data['name']
            
            return True
    
    async def _get_email_stats(self, user_id: str) -> Dict:
        """Get email statistics from email service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.email_service_url}/emails/stats",
                    headers={"X-User-ID": user_id}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"total_emails": 0, "unread_emails": 0, "top_senders": []}
        except Exception as e:
            print(f"Error getting email stats: {e}")
            return {"total_emails": 0, "unread_emails": 0, "top_senders": []}