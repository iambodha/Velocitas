# File: /gmail-api-microservices/gmail-api-microservices/gateway/src/routes/api.py

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from ..middleware.auth import verify_token, require_auth
import httpx
import os

router = APIRouter()

# Service URLs
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:5000')
GMAIL_SERVICE_URL = os.getenv('GMAIL_SERVICE_URL', 'http://localhost:5001')
EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:5002')
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:5003')

async def forward_request(service_url: str, path: str, method: str, **kwargs):
    """Forward request to a microservice"""
    url = f"{service_url}{path}"
    
    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            response = await client.get(url, **kwargs)
        elif method.upper() == "POST":
            response = await client.post(url, **kwargs)
        elif method.upper() == "PUT":
            response = await client.put(url, **kwargs)
        elif method.upper() == "DELETE":
            response = await client.delete(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    return response

# Authentication routes
@router.get("/auth")
async def get_auth_url():
    """Get OAuth authorization URL"""
    response = await forward_request(AUTH_SERVICE_URL, "/auth", "GET")
    return response.json()

@router.get("/callback")
async def oauth_callback(request: Request):
    """Handle OAuth callback"""
    params = dict(request.query_params)
    response = await forward_request(AUTH_SERVICE_URL, "/callback", "GET", params=params)
    return response.json()

@router.get("/status")
async def auth_status(user_id: str = Depends(require_auth)):
    """Check authentication status"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(AUTH_SERVICE_URL, "/status", "GET", headers=headers)
    return response.json()

@router.post("/logout")
async def logout(user_id: str = Depends(require_auth)):
    """Logout user"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(AUTH_SERVICE_URL, "/logout", "POST", headers=headers)
    return response.json()

# Email routes
@router.get("/emails")
async def get_emails(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Get user emails"""
    headers = {"X-User-ID": user_id}
    params = dict(request.query_params)
    response = await forward_request(EMAIL_SERVICE_URL, "/emails", "GET", headers=headers, params=params)
    return response.json()

@router.get("/email/{email_id}")
async def get_email(email_id: str, user_id: str = Depends(require_auth)):
    """Get specific email"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(EMAIL_SERVICE_URL, f"/email/{email_id}", "GET", headers=headers)
    return response.json()

@router.get("/emails/search")
async def search_emails(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Search emails"""
    headers = {"X-User-ID": user_id}
    params = dict(request.query_params)
    response = await forward_request(EMAIL_SERVICE_URL, "/emails/search", "GET", headers=headers, params=params)
    return response.json()

@router.get("/emails/stats")
async def get_email_stats(user_id: str = Depends(require_auth)):
    """Get email statistics"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(EMAIL_SERVICE_URL, "/emails/stats", "GET", headers=headers)
    return response.json()

# Gmail service routes
@router.post("/emails/sync")
async def sync_emails(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Trigger email sync"""
    headers = {"X-User-ID": user_id}
    params = dict(request.query_params)
    response = await forward_request(GMAIL_SERVICE_URL, "/sync", "POST", headers=headers, params=params)
    return response.json()

# User profile routes
@router.get("/user/profile")
async def get_user_profile(user_id: str = Depends(require_auth)):
    """Get user profile"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(USER_SERVICE_URL, "/profile", "GET", headers=headers)
    return response.json()

@router.put("/user/profile")
async def update_user_profile(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Update user profile"""
    headers = {"X-User-ID": user_id}
    json_data = await request.json()
    response = await forward_request(USER_SERVICE_URL, "/profile", "PUT", headers=headers, json=json_data)
    return response.json()