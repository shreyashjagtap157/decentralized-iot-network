"""
Rate limiting middleware for API endpoints
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
from typing import Optional

# Redis client for rate limiting storage
redis_client: Optional[redis.Redis] = None

try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    redis_client.ping()  # Test connection
except Exception as e:
    print(f"Redis connection failed: {e}. Using in-memory rate limiting.")
    redis_client = None

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379" if redis_client else "memory://",
)

def setup_rate_limiting(app):
    """Setup rate limiting for the FastAPI application"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

def get_limiter():
    """Get the limiter instance"""
    return limiter

# Custom rate limit decorators
def auth_rate_limit():
    """Rate limit for authentication endpoints"""
    return limiter.limit("5/minute")

def api_rate_limit():
    """Rate limit for general API endpoints"""
    return limiter.limit("100/minute")

def device_rate_limit():
    """Rate limit for device endpoints"""
    return limiter.limit("10/minute")

def analytics_rate_limit():
    """Rate limit for analytics endpoints"""
    return limiter.limit("20/minute")
