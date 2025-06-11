import httpx
from typing import Optional, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

class AuthClient:
    def __init__(self):
        self.auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify token with auth service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.auth_service_url}/verify",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
                
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    async def get_gmail_credentials(self, token: str) -> Optional[Dict[str, Any]]:
        """Get Gmail credentials for user - calendar might need same Google access"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.auth_service_url}/gmail/credentials",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
                
        except Exception as e:
            logger.error(f"Failed to get Gmail credentials: {e}")
            return None

# Global instance
auth_client = AuthClient()