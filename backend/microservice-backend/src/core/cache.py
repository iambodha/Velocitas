import functools
import hashlib
import json
from typing import Any, Callable, Optional
from .redis import redis_client
import os

CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # 1 hour default
CACHE_PREFIX = os.getenv("CACHE_PREFIX", "email_service")

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"{CACHE_PREFIX}:{key_hash}"

def cached(ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{CACHE_PREFIX}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = redis_client.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.set(key, result, ttl or CACHE_TTL)
            
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Invalidate all cache keys matching pattern"""
    keys = redis_client.get_keys_by_pattern(f"{CACHE_PREFIX}:{pattern}")
    for key in keys:
        redis_client.delete(key)

# Email-specific cache utilities
class EmailCache:
    @staticmethod
    def cache_user_emails(user_id: str, emails: list, ttl: int = 300):
        """Cache user's email list"""
        key = f"{CACHE_PREFIX}:user_emails:{user_id}"
        redis_client.set(key, emails, ttl)
    
    @staticmethod
    def get_user_emails(user_id: str) -> Optional[list]:
        """Get cached user emails"""
        key = f"{CACHE_PREFIX}:user_emails:{user_id}"
        return redis_client.get(key)
    
    @staticmethod
    def invalidate_user_emails(user_id: str):
        """Invalidate user's cached emails"""
        pattern = f"user_emails:{user_id}*"
        invalidate_cache_pattern(pattern)
    
    @staticmethod
    def cache_email_content(email_id: str, content: dict, ttl: int = 3600):
        """Cache email content"""
        key = f"{CACHE_PREFIX}:email_content:{email_id}"
        redis_client.set(key, content, ttl)
    
    @staticmethod
    def get_email_content(email_id: str) -> Optional[dict]:
        """Get cached email content"""
        key = f"{CACHE_PREFIX}:email_content:{email_id}"
        return redis_client.get(key)