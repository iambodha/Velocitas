# File: /gmail-api-microservices/gmail-api-microservices/gateway/src/middleware/auth.py
#Tested

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Fix: Use correct port for auth service
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8001')

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify token and return user_id"""
    try:
        logger.info(f"Verifying token: {credentials.credentials[:20]}...")
        
        # Call auth service to verify token
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/verify",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            
            logger.info(f"Auth service response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                user_id = data.get("user_id") or data.get("email")
                logger.info(f"Token verified for user: {user_id}")
                return user_id
            else:
                logger.error(f"Token verification failed: {response.text}")
                raise HTTPException(status_code=401, detail="Invalid token")
                
    except httpx.RequestError as e:
        logger.error(f"Auth service connection error: {e}")
        raise HTTPException(status_code=401, detail="Authentication service unavailable")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Require authentication and return user_id"""
    return await verify_token(credentials)