# File: /gmail-api-microservices/gmail-api-microservices/services/email-service/src/app.py

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from .utils.auth_client import auth_client
from .services.gmail_service import GmailService
from typing import Optional, Dict, Any
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Email Service with Supabase Auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

security = HTTPBearer()

async def get_current_user_and_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> tuple[Dict[str, Any], str]:
    """Get current user from token and return both user data and token"""
    user_data = await auth_client.verify_token(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_data, credentials.credentials

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "email"}

@app.get("/emails")
async def get_emails(
    max_results: int = 10,
    user_and_token: tuple = Depends(get_current_user_and_token)
):
    """Get user's emails via gmail-service"""
    try:
        current_user, token = user_and_token
        
        gmail_service_url = os.getenv("GMAIL_SERVICE_URL", "http://localhost:8003")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gmail_service_url}/sync",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Gmail service error: {response.text}"
                )
            
            data = response.json()
            
            return {
                "emails": data.get("emails", []),
                "user_id": current_user["user"]["id"],
                "count": len(data.get("emails", []))
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get emails error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/emails/{email_id}")
async def get_email(
    email_id: str,
    user_and_token: tuple = Depends(get_current_user_and_token)
):
    """Get specific email by ID"""
    try:
        current_user, token = user_and_token
        
        # Get Gmail credentials
        creds = await auth_client.get_gmail_credentials(token)
        
        if not creds:
            raise HTTPException(
                status_code=403, 
                detail="Gmail access not granted. Please authenticate with Google first."
            )
        
        gmail_service = GmailService(creds)
        email = await gmail_service.get_email(email_id)
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        return {
            "email": email,
            "user_id": current_user["user"]["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get email error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/emails/search")
async def search_emails(
    query: str,
    max_results: int = 10,
    user_and_token: tuple = Depends(get_current_user_and_token)
):
    """Search emails"""
    try:
        current_user, token = user_and_token
        
        # Get Gmail credentials
        creds = await auth_client.get_gmail_credentials(token)
        
        if not creds:
            raise HTTPException(
                status_code=403, 
                detail="Gmail access not granted. Please authenticate with Google first."
            )
        
        gmail_service = GmailService(creds)
        emails = await gmail_service.search_emails(query=query, max_results=max_results)
        
        return {
            "emails": emails,
            "query": query,
            "user_id": current_user["user"]["id"],
            "count": len(emails)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search emails error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/labels")
async def get_labels(
    user_and_token: tuple = Depends(get_current_user_and_token)
):
    """Get Gmail labels"""
    try:
        current_user, token = user_and_token
        
        # Get Gmail credentials
        creds = await auth_client.get_gmail_credentials(token)
        
        if not creds:
            raise HTTPException(
                status_code=403, 
                detail="Gmail access not granted. Please authenticate with Google first."
            )
        
        gmail_service = GmailService(creds)
        labels = await gmail_service.get_labels()
        
        return {
            "labels": labels,
            "user_id": current_user["user"]["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get labels error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
