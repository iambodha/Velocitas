from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .database.db import get_db
from .models.user import User
from .handlers.profile import UserProfileHandler

app = FastAPI(
    title="User Service",
    description="User management service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

profile_handler = UserProfileHandler()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "user"}

@app.get("/profile")
async def get_user_profile(x_user_id: str = Header(None)):
    """Get current user profile"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    profile = await profile_handler.get_profile(x_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    return profile

@app.put("/profile")
async def update_user_profile(
    profile_data: dict,
    x_user_id: str = Header(None)
):
    """Update user profile"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    success = await profile_handler.update_profile(x_user_id, profile_data)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True, "message": "Profile updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)