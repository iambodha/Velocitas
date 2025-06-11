import redis
from typing import Any, Optional
import json
import os
from urllib.parse import urlparse

class RedisClient:
    def __init__(self):
        """Initialize Redis client without immediate connection"""
        self.client = None
        self._connected = False
        print("⚠️  Redis client initialized (connection will be attempted on first use)")
    
    def _connect(self):
        """Lazy connection to Redis"""
        if self._connected:
            return True
        
        try:
            redis_url = os.getenv("REDIS_URL", "redis://:redis123@localhost:6379/0")
            
            # Parse Redis URL
            parsed = urlparse(redis_url)
            
            # Try connecting without password first
            self.client = redis.Redis(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 6379,
                db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self.client.ping()
            self._connected = True
            print("✅ Connected to Redis without password")
            return True
            
        except Exception as e:
            print(f"⚠️  Redis not available: {e}")
            print("⚠️  Running without Redis (caching disabled)")
            self.client = None
            self._connected = False
            return False
    
    def get(self, key: str) -> Any:
        """Get value from Redis"""
        if not self._connect():
            return None
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        if not self._connect():
            return False
        try:
            serialized_value = json.dumps(value, default=str)
            if ttl:
                return self.client.setex(key, ttl, serialized_value)
            else:
                return self.client.set(key, serialized_value)
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self._connect():
            return False
        try:
            return bool(self.client.delete(key))
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._connect():
            return False
        try:
            return bool(self.client.exists(key))
        except Exception:
            return False
    
    def flush_db(self) -> bool:
        """Clear all keys in current database"""
        if not self._connect():
            return False
        try:
            return self.client.flushdb()
        except Exception:
            return False
    
    def get_keys_by_pattern(self, pattern: str) -> list:
        """Get keys matching pattern"""
        if not self._connect():
            return []
        try:
            return self.client.keys(pattern)
        except Exception:
            return []

# Create global Redis client instance
redis_client = RedisClient()