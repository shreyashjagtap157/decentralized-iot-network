"""
Caching utilities for high-performance data retrieval.
Uses Redis for distributed caching with automatic expiration.
"""
import json
import os
from typing import Any, Optional, Callable
from functools import wraps
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    """
    Redis-based caching service with fallback to in-memory cache.
    """
    
    def __init__(self):
        self._memory_cache: dict = {}
        self._redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
            except Exception:
                self._redis_client = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key from function arguments."""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        if self._redis_client:
            try:
                value = self._redis_client.get(key)
                return json.loads(value) if value else None
            except Exception:
                pass
        return self._memory_cache.get(key)
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Store a value in cache with TTL."""
        serialized = json.dumps(value, default=str)
        
        if self._redis_client:
            try:
                self._redis_client.setex(key, ttl_seconds, serialized)
                return
            except Exception:
                pass
        
        self._memory_cache[key] = value
    
    def delete(self, key: str) -> None:
        """Remove a value from cache."""
        if self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass
        self._memory_cache.pop(key, None)
    
    def clear_prefix(self, prefix: str) -> None:
        """Clear all keys matching a prefix (Redis only)."""
        if self._redis_client:
            try:
                keys = self._redis_client.keys(f"{prefix}:*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception:
                pass


# Global cache instance
cache_service = CacheService()


def cached(prefix: str, ttl_seconds: int = 300):
    """
    Decorator for caching function results.
    
    Usage:
        @cached("user_earnings", ttl_seconds=60)
        async def get_user_earnings(user_id: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = cache_service._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator
