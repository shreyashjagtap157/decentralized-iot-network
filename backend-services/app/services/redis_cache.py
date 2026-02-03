"""
Redis-based distributed caching service for high-performance query caching.
Supports multiple workers and automatic cache invalidation.
"""

import redis.asyncio as redis
from functools import wraps
from typing import Any, Optional, Callable
import json
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class RedisCache:
    """Distributed Redis cache with async support"""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self.default_ttl = 300  # 5 minutes
    
    async def connect(self):
        """Connect to Redis"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url, 
                encoding="utf-8", 
                decode_responses=True
            )
            logger.info("Redis cache connected")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis cache disconnected")
    
    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Create a unique cache key from function arguments"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            logger.debug(f"Cache miss: {key}")
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set cached value with TTL"""
        try:
            await self.redis.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(value, default=str)
            )
            logger.debug(f"Cache set: {key}")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def delete(self, key: str):
        """Delete cached value"""
        try:
            await self.redis.delete(key)
            logger.debug(f"Cache deleted: {key}")
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        try:
            keys = await self.redis.keys(f"cache:*{pattern}*")
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys")
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
    
    def cached(self, prefix: str, ttl: int = None):
        """Decorator for caching async function results"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Skip caching if Redis not connected
                if self._redis is None:
                    return await func(*args, **kwargs)
                
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # Try cache first
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator


# Global cache instance
redis_cache = RedisCache()


async def get_redis_cache() -> RedisCache:
    """Dependency for getting Redis cache"""
    if redis_cache._redis is None:
        await redis_cache.connect()
    return redis_cache
