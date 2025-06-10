import uuid
import time
from typing import Any, Optional
from .redis import redis_client
import os

SESSION_TTL = int(os.getenv("SESSION_TTL", 86400))  # 24 hours
SESSION_PREFIX = os.getenv("SESSION_PREFIX", "session")

class SessionManager:
    @staticmethod
    def create_session(user_id: str, data: dict = None) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "data": data or {},
            "created_at": int(time.time())
        }
        
        key = f"{SESSION_PREFIX}:{session_id}"
        redis_client.set(key, session_data, SESSION_TTL)
        
        return session_id
    
    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """Get session data"""
        key = f"{SESSION_PREFIX}:{session_id}"
        return redis_client.get(key)
    
    @staticmethod
    def update_session(session_id: str, data: dict) -> bool:
        """Update session data"""
        key = f"{SESSION_PREFIX}:{session_id}"
        session = redis_client.get(key)
        
        if session:
            session["data"].update(data)
            return redis_client.set(key, session, SESSION_TTL)
        
        return False
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete session"""
        key = f"{SESSION_PREFIX}:{session_id}"
        return redis_client.delete(key)
    
    @staticmethod
    def extend_session(session_id: str, ttl: int = None) -> bool:
        """Extend session TTL"""
        key = f"{SESSION_PREFIX}:{session_id}"
        return redis_client.expire(key, ttl or SESSION_TTL)