# File: /gmail-api-microservices/gmail-api-microservices/gateway/src/middleware/auth.py
#Tested

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
from typing import Optional

AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:5000')

security = HTTPBearer(auto_error=False)

async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """Verify JWT token with auth service and return user_id"""
    if not credentials:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/verify",
                headers={"Authorization": f"Bearer {credentials.credentials}"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('user_id')
            else:
                return None
                
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

def require_auth(user_id: Optional[str] = Depends(verify_token)) -> str:
    """Require authentication and return user_id"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id