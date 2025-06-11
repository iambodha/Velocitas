# File: /gmail-api-microservices/gmail-api-microservices/gateway/src/routes/api.py
#Tested

from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse  # Add HTMLResponse
import httpx
import os
from ..middleware.auth import verify_token, require_auth

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
            raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")
    
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
    # Forward the callback to auth service
    query_params = str(request.url.query)
    response = await forward_request(
        AUTH_SERVICE_URL, 
        f"/callback?{query_params}", 
        "GET"
    )
    
    if response.status_code == 200:
        # Get the response data
        auth_data = response.json()
        
        # Return HTML that communicates with parent window
        return HTMLResponse(content=f"""
            <html>
                <body>
                    <script>
                        window.opener.postMessage({{
                            type: 'GMAIL_AUTH_SUCCESS',
                            token: '{auth_data.get("session_token", "")}',
                            user_email: '{auth_data.get("email", "")}',
                            user_id: '{auth_data.get("user_id", "")}',
                            user_name: '{auth_data.get("name", "")}'
                        }}, window.location.origin);
                        window.close();
                    </script>
                    <p>Authentication successful! This window will close automatically.</p>
                </body>
            </html>
        """)
    else:
        # Handle error case
        error_detail = "Authentication failed"
        try:
            error_response = response.json()
            error_detail = error_response.get("detail", error_detail)
        except:
            pass
            
        return HTMLResponse(content=f"""
            <html>
                <body>
                    <script>
                        window.opener.postMessage({{
                            type: 'GMAIL_AUTH_ERROR',
                            error: '{error_detail}'
                        }}, window.location.origin);
                        window.close();
                    </script>
                    <p>Authentication failed: {error_detail}</p>
                </body>
            </html>
        """)

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
@router.get("/gmail/profile")
async def get_gmail_profile(user_id: str = Depends(require_auth)):
    """Get Gmail user profile"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(GMAIL_SERVICE_URL, "/profile", "GET", headers=headers)
    return response.json()

@router.post("/gmail/threads/list")
async def list_gmail_threads(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """List Gmail threads with sophisticated filtering"""
    headers = {"X-User-ID": user_id}
    json_data = await request.json()
    response = await forward_request(GMAIL_SERVICE_URL, "/threads/list", "POST", headers=headers, json=json_data)
    return response.json()

@router.get("/gmail/threads/{thread_id}")
async def get_gmail_thread(
    thread_id: str,
    user_id: str = Depends(require_auth)
):
    """Get complete Gmail thread"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(GMAIL_SERVICE_URL, f"/threads/{thread_id}", "GET", headers=headers)
    return response.json()

@router.get("/gmail/messages/{message_id}/attachments/{attachment_id}")
async def get_gmail_attachment(
    message_id: str,
    attachment_id: str,
    user_id: str = Depends(require_auth)
):
    """Get Gmail attachment"""
    headers = {"X-User-ID": user_id}
    response = await forward_request(GMAIL_SERVICE_URL, f"/messages/{message_id}/attachments/{attachment_id}", "GET", headers=headers)
    return response.json()

@router.post("/gmail/threads/mark-read")
async def mark_gmail_threads_read(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Mark Gmail threads as read"""
    headers = {"X-User-ID": user_id}
    json_data = await request.json()
    response = await forward_request(GMAIL_SERVICE_URL, "/threads/mark-read", "POST", headers=headers, json=json_data)
    return response.json()

@router.post("/gmail/threads/mark-unread")
async def mark_gmail_threads_unread(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Mark Gmail threads as unread"""
    headers = {"X-User-ID": user_id}
    json_data = await request.json()
    response = await forward_request(GMAIL_SERVICE_URL, "/threads/mark-unread", "POST", headers=headers, json=json_data)
    return response.json()

@router.get("/gmail/search")
async def search_gmail(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Search Gmail with sophisticated filtering"""
    headers = {"X-User-ID": user_id}
    params = dict(request.query_params)
    response = await forward_request(GMAIL_SERVICE_URL, "/search", "GET", headers=headers, params=params)
    return response.json()

# Update your existing sync endpoint
@router.post("/emails/sync")
async def sync_emails(
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Trigger email sync with sophisticated parsing"""
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

# Email management routes
@router.put("/email/{email_id}/read")
async def mark_email_read(
    email_id: str,
    is_read: bool = Query(default=True),
    user_id: str = Depends(require_auth)
):
    """Mark email as read/unread"""
    headers = {"X-User-ID": user_id}
    params = {"is_read": is_read}
    response = await forward_request(EMAIL_SERVICE_URL, f"/email/{email_id}/read", "PUT", headers=headers, params=params)
    return response.json()

@router.put("/email/{email_id}/star")
async def mark_email_starred(
    email_id: str,
    is_starred: bool = Query(default=True),
    user_id: str = Depends(require_auth)
):
    """Mark email as starred/unstarred"""
    headers = {"X-User-ID": user_id}
    params = {"is_starred": is_starred}
    response = await forward_request(EMAIL_SERVICE_URL, f"/email/{email_id}/star", "PUT", headers=headers, params=params)
    return response.json()

@router.put("/email/{email_id}/category")
async def update_email_category(
    email_id: str,
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Update email category"""
    headers = {"X-User-ID": user_id}
    json_data = await request.json()
    response = await forward_request(EMAIL_SERVICE_URL, f"/email/{email_id}/category", "PUT", headers=headers, json=json_data)
    return response.json()

@router.put("/email/{email_id}/urgency")
async def update_email_urgency(
    email_id: str,
    request: Request,
    user_id: str = Depends(require_auth)
):
    """Update email urgency level (0-10 scale)"""
    headers = {"X-User-ID": user_id}
    json_data = await request.json()
    response = await forward_request(EMAIL_SERVICE_URL, f"/email/{email_id}/urgency", "PUT", headers=headers, json=json_data)
    return response.json()