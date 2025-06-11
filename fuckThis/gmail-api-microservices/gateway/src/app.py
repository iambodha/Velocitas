# File: /gmail-api-microservices/gmail-api-microservices/gateway/src/app.py
#Tested
from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
import httpx
import os
from typing import Optional
import jwt
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Gmail API Gateway",
    description="API Gateway for Gmail microservices",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Service URLs - Fix: Use correct auth service port
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8001')
GMAIL_SERVICE_URL = os.getenv('GMAIL_SERVICE_URL', 'http://localhost:5001')
EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:5002')
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:5003')

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
security = HTTPBearer(auto_error=False)

async def verify_token(authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verify JWT token"""
    if not authorization:
        return None
    
    try:
        # Try local JWT verification first
        payload = jwt.decode(authorization.credentials, JWT_SECRET, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.InvalidTokenError:
        # If local verification fails, try auth service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{AUTH_SERVICE_URL}/verify",
                    headers={"Authorization": f"Bearer {authorization.credentials}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('user_id')
        except:
            pass
        return None

async def forward_request(service_url: str, path: str, method: str, headers: dict = None, json_data: dict = None, params: dict = None):
    """Forward request to microservice"""
    async with httpx.AsyncClient() as client:
        url = f"{service_url}{path}"
        
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=30.0
            )
            return response
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

# Health check
@app.get("/health")
async def health():
    """Gateway health check"""
    services_status = {}
    
    # Check each service
    services = {
        "auth": AUTH_SERVICE_URL,
        "gmail": GMAIL_SERVICE_URL,
        "email": EMAIL_SERVICE_URL,
        "user": USER_SERVICE_URL
    }
    
    for service_name, service_url in services.items():
        try:
            response = await forward_request(service_url, "/health", "GET")
            services_status[service_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            services_status[service_name] = "unreachable"
    
    overall_status = "healthy" if all(status == "healthy" for status in services_status.values()) else "degraded"
    
    return {
        "status": overall_status,
        "service": "gateway",
        "services": services_status
    }

# Auth service routes
@app.get("/auth")
async def auth():
    """Get OAuth authorization URL"""
    try:
        response = await forward_request(AUTH_SERVICE_URL, "/auth", "GET")
        
        # Check if response is successful and has content
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Auth service error")
        
        # Check if response has content before parsing JSON
        if not response.content:
            raise HTTPException(status_code=502, detail="Empty response from auth service")
        
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with auth service: {str(e)}")

@app.get("/callback")
async def callback(request: Request):
    """Handle OAuth callback - returns HTML response"""
    try:
        query_params = dict(request.query_params)
        response = await forward_request(AUTH_SERVICE_URL, "/callback", "GET", params=query_params)
        
        # For callback, we expect HTML response, so return it directly
        if response.status_code == 200:
            return HTMLResponse(content=response.text)
        else:
            raise HTTPException(status_code=response.status_code, detail="Callback failed")
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error handling callback: {str(e)}")

@app.get("/status")
async def status(user_id: str = Depends(verify_token)):
    """Check authentication status"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        headers = {"X-User-ID": user_id}
        response = await forward_request(AUTH_SERVICE_URL, "/status", "GET", headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Status check failed")
        
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error checking status: {str(e)}")

@app.post("/logout")
async def logout(user_id: str = Depends(verify_token)):
    """Logout user"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        headers = {"X-User-ID": user_id}
        response = await forward_request(AUTH_SERVICE_URL, "/logout", "POST", headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Logout failed")
        
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error during logout: {str(e)}")

# User service routes
@app.get("/user/profile")
async def get_user_profile(user_id: str = Depends(verify_token)):
    """Get user profile"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        headers = {"X-User-ID": user_id}
        response = await forward_request(USER_SERVICE_URL, "/profile", "GET", headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to get profile")
        
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"User service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error getting profile: {str(e)}")

@app.put("/user/profile")
async def update_user_profile(request: Request, user_id: str = Depends(verify_token)):
    """Update user profile"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        headers = {"X-User-ID": user_id}
        json_data = await request.json()
        response = await forward_request(USER_SERVICE_URL, "/profile", "PUT", headers=headers, json_data=json_data)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to update profile")
        
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"User service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error updating profile: {str(e)}")

@app.get("/emails")
async def get_emails(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(verify_token)
):
    """Get user emails"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    headers = {"X-User-ID": user_id}
    params = {"limit": limit, "offset": offset}
    
    response = await forward_request(
        EMAIL_SERVICE_URL, 
        "/emails", 
        "GET", 
        headers=headers, 
        params=params
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch emails")

@app.get("/email/{email_id}")
async def get_email(
    email_id: str,
    user_id: str = Depends(verify_token)
):
    """Get specific email"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    headers = {"X-User-ID": user_id}
    
    response = await forward_request(
        EMAIL_SERVICE_URL, 
        f"/email/{email_id}", 
        "GET", 
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch email")

@app.get("/emails/search")
async def search_emails(
    request: Request,
    user_id: str = Depends(verify_token)
):
    """Search emails"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    headers = {"X-User-ID": user_id}
    params = dict(request.query_params)
    
    response = await forward_request(
        EMAIL_SERVICE_URL, 
        "/emails/search", 
        "GET", 
        headers=headers, 
        params=params
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to search emails")

@app.post("/emails/sync")
async def sync_emails(
    user_id: str = Depends(verify_token)
):
    """Sync emails from Gmail"""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    headers = {"X-User-ID": user_id}
    
    response = await forward_request(
        EMAIL_SERVICE_URL, 
        "/emails/sync", 
        "POST", 
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to sync emails")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)