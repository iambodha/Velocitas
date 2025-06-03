# File: /gmail-api-microservices/gmail-api-microservices/services/gmail-service/src/app.py

from fastapi import FastAPI, HTTPException, Header, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from .handlers.gmail_api import GmailAPIHandler
from .handlers.sync import EmailSyncHandler

app = FastAPI(
    title="Gmail Service",
    description="Gmail API integration service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Initialize handlers
gmail_handler = GmailAPIHandler()
sync_handler = EmailSyncHandler()

# Service URLs
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:5000')
EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:5002')

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gmail"}

@app.post("/sync")
async def sync_emails(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=50, le=200),
    x_user_id: str = Header(None)
):
    """Manually trigger email sync from Gmail"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    # Get credentials from auth service
    async with httpx.AsyncClient() as client:
        auth_response = await client.get(
            f"{AUTH_SERVICE_URL}/credentials",
            headers={"X-User-ID": x_user_id}
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Could not get credentials")
        
        credentials_data = auth_response.json()
    
    # Start sync in background
    background_tasks.add_task(sync_handler.sync_user_emails, x_user_id, credentials_data, limit)
    
    return {
        "success": True,
        "message": f"Sync started for up to {limit} emails",
        "user_id": x_user_id
    }

@app.post("/sync/new-user")
async def sync_new_user(
    background_tasks: BackgroundTasks,
    x_user_id: str = Header(None)
):
    """Handle new user initial email sync"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    # Get credentials from auth service
    async with httpx.AsyncClient() as client:
        auth_response = await client.get(
            f"{AUTH_SERVICE_URL}/credentials",
            headers={"X-User-ID": x_user_id}
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Could not get credentials")
        
        credentials_data = auth_response.json()
    
    # Start initial sync in background
    background_tasks.add_task(sync_handler.initial_user_sync, x_user_id, credentials_data)
    
    return {
        "success": True,
        "message": "Initial sync started for new user",
        "user_id": x_user_id
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)