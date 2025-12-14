"""
Redis caching and optimization utilities
"""

import logging
import json
import pickle
from typing import Any, Optional, Callable
from functools import wraps
import aioredis
import os

logger = logging.getLogger(__name__)


class RedisCache:
    """Advanced Redis caching with serialization options."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.create_redis_pool(self.redis_url)
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache."""
        try:
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            logger.debug(f"Cached key {key} with TTL {ttl}s")
        except Exception as e:
            logger.error(f"Error setting key {key}: {str(e)}")
    
    async def delete(self, key: str):
        """Delete value from cache."""
        try:
            await self.redis.delete(key)
            logger.debug(f"Deleted cache key {key}")
        except Exception as e:
            logger.error(f"Error deleting key {key}: {str(e)}")
    
    async def clear(self, pattern: str = "*"):
        """Clear cache keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys")
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
    
    async def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            info = await self.redis.info()
            return {
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}


class CacheDecorator:
    """Decorator for caching function results."""
    
    def __init__(self, cache: RedisCache, ttl: int = 300, key_prefix: str = "cache"):
        self.cache = cache
        self.ttl = ttl
        self.key_prefix = key_prefix
    
    def cached(self, func: Callable) -> Callable:
        """Decorator to cache function results."""
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            cache_key = f"{self.key_prefix}:{func.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await self.cache.set(cache_key, result, self.ttl)
            
            return result
        
        return wrapper


class RateLimiter:
    """Token bucket rate limiter using Redis."""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
    
    async def is_allowed(self, key: str, rate: int, period: int) -> bool:
        """Check if request is allowed under rate limit."""
        try:
            current_count = await self.cache.redis.incr(f"rate_limit:{key}")
            
            if current_count == 1:
                # Set expiration on first request
                await self.cache.redis.expire(f"rate_limit:{key}", period)
            
            return current_count <= rate
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True  # Allow on error


class SessionCache:
    """Session storage using Redis."""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
    
    async def set_session(self, session_id: str, data: dict, ttl: int = 3600):
        """Store session in Redis."""
        await self.cache.set(f"session:{session_id}", data, ttl)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session from Redis."""
        return await self.cache.get(f"session:{session_id}")
    
    async def delete_session(self, session_id: str):
        """Delete session from Redis."""
        await self.cache.delete(f"session:{session_id}")


class DistributedLock:
    """Distributed lock using Redis."""
    
    def __init__(self, redis_cache: RedisCache, timeout: int = 30):
        self.cache = redis_cache
        self.timeout = timeout
    
    async def acquire(self, lock_key: str) -> bool:
        """Acquire a lock."""
        try:
            result = await self.cache.redis.set(
                f"lock:{lock_key}",
                "1",
                expire=self.timeout,
                exist=False  # Only set if not exists
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_key}: {str(e)}")
            return False
    
    async def release(self, lock_key: str):
        """Release a lock."""
        try:
            await self.cache.delete(f"lock:{lock_key}")
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {str(e)}")


class CacheWarmup:
    """Preload frequently accessed data into cache."""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
    
    async def warmup_device_cache(self, devices: list):
        """Preload device data into cache."""
        logger.info(f"Warming up cache with {len(devices)} devices")
        for device in devices:
            await self.cache.set(
                f"device:{device['device_id']}",
                device,
                ttl=3600
            )
    
    async def warmup_user_cache(self, users: list):
        """Preload user data into cache."""
        logger.info(f"Warming up cache with {len(users)} users")
        for user in users:
            await self.cache.set(
                f"user:{user['user_id']}",
                user,
                ttl=3600
            )


# Global cache instance
redis_cache = RedisCache()
