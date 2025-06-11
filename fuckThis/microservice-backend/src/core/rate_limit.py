import time
from typing import Optional
from fastapi import HTTPException, Request
from .redis import redis_client
import os

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 3600))

class RateLimiter:
    @staticmethod
    def check_rate_limit(identifier: str, requests: int = None, window: int = None) -> dict:
        """Check if identifier is within rate limits"""
        if not RATE_LIMIT_ENABLED:
            return {"allowed": True, "remaining": float('inf'), "reset_time": 0}
        
        requests = requests or RATE_LIMIT_REQUESTS
        window = window or RATE_LIMIT_WINDOW
        
        key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        
        # Get current count
        current_count = redis_client.get(key)
        
        if current_count is None:
            # First request
            redis_client.set(key, 1, window)
            return {
                "allowed": True,
                "remaining": requests - 1,
                "reset_time": current_time + window
            }
        
        current_count = int(current_count)
        
        if current_count >= requests:
            # Rate limit exceeded
            ttl = redis_client.client.ttl(key)
            reset_time = current_time + (ttl if ttl > 0 else window)
            
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": reset_time
            }
        
        # Increment counter
        redis_client.increment(key)
        
        return {
            "allowed": True,
            "remaining": requests - current_count - 1,
            "reset_time": current_time + redis_client.client.ttl(key)
        }

def rate_limit_dependency(request: Request, requests: int = None, window: int = None):
    """FastAPI dependency for rate limiting"""
    # Use IP address as identifier (you might want to use user ID instead)
    identifier = request.client.host
    
    result = RateLimiter.check_rate_limit(identifier, requests, window)
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Remaining": str(result["remaining"]),
                "X-RateLimit-Reset": str(result["reset_time"])
            }
        )
    
    return result