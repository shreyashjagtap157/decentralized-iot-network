"""
Database query optimization with caching and indexing strategies
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import Index, event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QueryCache:
    """Simple query result cache with invalidation."""
    
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            import time
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set cached result."""
        import time
        self.cache[key] = (value, time.time())
        logger.debug(f"Cache set for key: {key}")
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
    
    def invalidate(self, key: str):
        """Invalidate a specific cache key."""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache invalidated for key: {key}")

    def invalidate_all(self):
        """Invalidate all cache entries."""
        self.cache.clear()
        logger.debug("All cache entries invalidated.")


# Global query cache
query_cache = QueryCache(ttl=300)


class IndexingStrategy:
    """Define optimal indexes for database tables."""
    
    @staticmethod
    def create_device_indexes(db_model):
        """Create indexes for device table."""
        indexes = [
            Index('idx_device_user_id', 'user_id'),
            Index('idx_device_device_id', 'device_id', unique=True),
            Index('idx_device_created_at', 'created_at'),
            Index('idx_device_status', 'status'),
            Index('idx_device_user_status', 'user_id', 'status'),  # Composite index
        ]
        return indexes
    
    @staticmethod
    def create_device_data_indexes(db_model):
        """Create indexes for device data table."""
        indexes = [
            Index('idx_data_device_id', 'device_id'),
            Index('idx_data_timestamp', 'timestamp'),
            Index('idx_data_device_timestamp', 'device_id', 'timestamp'),  # Composite
            Index('idx_data_energy', 'energy_generated'),
        ]
        return indexes
    
    @staticmethod
    def create_user_indexes(db_model):
        """Create indexes for user table."""
        indexes = [
            Index('idx_user_email', 'email', unique=True),
            Index('idx_user_username', 'username', unique=True),
            Index('idx_user_created_at', 'created_at'),
            Index('idx_user_status', 'status'),
        ]
        return indexes
    
    @staticmethod
    def create_transaction_indexes(db_model):
        """Create indexes for transaction table."""
        indexes = [
            Index('idx_transaction_user_id', 'user_id'),
            Index('idx_transaction_device_id', 'device_id'),
            Index('idx_transaction_timestamp', 'timestamp'),
            Index('idx_transaction_user_timestamp', 'user_id', 'timestamp'),
            Index('idx_transaction_status', 'status'),
        ]
        return indexes

    @staticmethod
    def create_optimized_indexes(db_model):
        """Create additional composite indexes for common query patterns."""
        indexes = [
            Index('idx_device_user_timestamp', 'user_id', 'timestamp'),
            Index('idx_device_status_timestamp', 'status', 'timestamp'),
        ]
        return indexes


class QueryOptimization:
    """Query optimization utilities."""
    
    @staticmethod
    def optimize_device_query(session: Session, device_id: str):
        """Get device with optimized query (eager loading)."""
        cache_key = f"device_{device_id}"
        cached = query_cache.get(cache_key)
        if cached:
            return cached
        
        # In production, use joinedload or selectinload for relationships
        # from sqlalchemy.orm import joinedload
        # query = session.query(Device).options(joinedload(Device.user))
        # result = query.filter(Device.device_id == device_id).first()
        
        logger.info(f"Executing optimized query for device {device_id}")
        result = session.query(Device).filter(Device.device_id == device_id).first()
        
        if result:
            query_cache.set(cache_key, result)
        
        return result
    
    @staticmethod
    def optimize_bulk_device_query(session: Session, device_ids: List[str]):
        """Get multiple devices efficiently."""
        logger.info(f"Executing bulk query for {len(device_ids)} devices")
        
        # Use IN clause for efficient bulk queries
        from sqlalchemy import and_
        results = session.query(Device).filter(Device.device_id.in_(device_ids)).all()
        
        return results
    
    @staticmethod
    def optimize_aggregation_query(session: Session, device_id: str):
        """Get aggregated device data efficiently."""
        cache_key = f"device_stats_{device_id}"
        cached = query_cache.get(cache_key)
        if cached:
            return cached
        
        # Use aggregation functions
        from sqlalchemy import func
        result = session.query(
            func.count(DeviceData.id).label('count'),
            func.sum(DeviceData.energy_generated).label('total_energy'),
            func.avg(DeviceData.energy_generated).label('avg_energy'),
            func.max(DeviceData.energy_generated).label('max_energy'),
            func.min(DeviceData.energy_generated).label('min_energy'),
        ).filter(DeviceData.device_id == device_id).first()
        
        query_cache.set(cache_key, result)
        return result


class DatabaseConnectionPooling:
    """Configure optimal connection pooling."""
    
    @staticmethod
    def get_pool_config():
        """Get recommended connection pool configuration."""
        return {
            "pool_size": 10,           # Number of connections in the pool
            "max_overflow": 20,        # Additional connections to create
            "pool_recycle": 3600,      # Recycle connections after 1 hour
            "pool_pre_ping": True,     # Test connections before using
            "echo": False,             # Don't log SQL queries (set True for debugging)
            "connect_args": {
                "connect_timeout": 10,
                "application_name": "iot_network_app"
            }
        }
    
    @staticmethod
    def tune_for_high_load():
        """Adjust connection pool settings for high-load scenarios."""
        return {
            "pool_size": 20,           # Increase pool size
            "max_overflow": 40,        # Allow more overflow connections
            "pool_recycle": 1800,      # Recycle connections more frequently
            "pool_pre_ping": True,     # Test connections before using
            "echo": False,             # Disable SQL logging in production
            "connect_args": {
                "connect_timeout": 5,
                "application_name": "iot_network_app_high_load"
            }
        }


class N_PlusOneQueryDetector:
    """Detect and log N+1 query problems."""
    
    def __init__(self):
        self.query_log = []
    
    def detect_n_plus_one(self, session: Session):
        """Enable N+1 query detection."""
        @event.listens_for(session.connection(), "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            self.query_log.append(statement)
            logger.debug(f"Query: {statement}")
        
        @event.listens_for(session.connection(), "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Analyze query patterns
            similar_queries = sum(1 for q in self.query_log if self._is_similar(q, statement))
            if similar_queries > 5:
                logger.warning(f"Possible N+1 query detected: {statement}")
    
    @staticmethod
    def _is_similar(query1: str, query2: str) -> bool:
        """Check if two queries are similar (same structure)."""
        # Simple similarity check - normalize queries
        return query1.split()[0:3] == query2.split()[0:3]
    
    def clear_log(self):
        """Clear query log."""
        self.query_log.clear()
    
    def log_n_plus_one_issues(self):
        """Log detected N+1 query issues."""
        for query in self.query_log:
            logger.warning(f"Potential N+1 query detected: {query}")


class ConnectionHealthCheck:
    """Monitor database connection health."""
    
    @staticmethod
    def check_connection_health(session: Session) -> bool:
        """Check if database connection is healthy."""
        try:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            logger.info("Database connection healthy")
            return True
        except Exception as e:
            logger.error(f"Database connection health check failed: {str(e)}")
            return False


# Placeholder model definitions (would be imported from actual models)
class Device:
    pass


class DeviceData:
    pass
