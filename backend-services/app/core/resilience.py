"""
Backend service initialization with retry logic and circuit breaker pattern
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker pattern implementation for fault tolerance."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
    
    def record_success(self):
        """Record a successful operation."""
        self.failures = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed operation."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failures} failures")
    
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout has elapsed
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        
        # half-open state allows one attempt
        return True
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == "open"


class RetryPolicy:
    """Retry policy with exponential backoff."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_attempts}")
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    # Calculate exponential backoff
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed: {str(e)}")
        
        raise last_exception


class ServiceConnector:
    """Connector for external services with circuit breaker and retry logic."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.circuit_breaker = CircuitBreaker()
        self.retry_policy = RetryPolicy()
    
    async def execute(self, func, *args, **kwargs):
        """Execute operation with circuit breaker and retry logic."""
        if not self.circuit_breaker.can_execute():
            logger.error(f"{self.service_name} circuit breaker is open")
            raise Exception(f"{self.service_name} is temporarily unavailable")
        
        try:
            result = await self.retry_policy.execute_with_retry(func, *args, **kwargs)
            self.circuit_breaker.record_success()
            return result
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise


# Global service connectors
database_connector = ServiceConnector("database")
cache_connector = ServiceConnector("cache")
mqtt_connector = ServiceConnector("mqtt")


async def get_database_connection():
    """Get database connection with retry logic."""
    from app.core.db import get_db
    return await database_connector.execute(get_db)


async def get_cache_connection():
    """Get cache connection with retry logic."""
    from app.core.cache import get_redis
    return await cache_connector.execute(get_redis)
