"""
Performance profiling and optimization utilities
"""

import cProfile
import pstats
import io
import logging
import time
from functools import wraps
from typing import Callable, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """Profile function performance and identify bottlenecks."""
    
    def __init__(self, enable_profiling: bool = True):
        self.enable_profiling = enable_profiling
        self.profiles = {}
    
    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.enable_profiling:
                return func(*args, **kwargs)
            
            profiler = cProfile.Profile()
            profiler.enable()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()
                self._print_profile_stats(profiler, func.__name__)
        
        return wrapper
    
    @staticmethod
    def _print_profile_stats(profiler: cProfile.Profile, func_name: str):
        """Print profiling statistics."""
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions
        
        logger.info(f"Profile for {func_name}:\n{s.getvalue()}")


@contextmanager
def measure_time(operation_name: str):
    """Context manager to measure execution time."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"{operation_name} took {elapsed_time:.3f} seconds")


class PerformanceMonitor:
    """Monitor performance metrics across application."""
    
    def __init__(self):
        self.metrics = {}
    
    def record_metric(self, metric_name: str, value: float):
        """Record a performance metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append(value)
    
    def get_metric_stats(self, metric_name: str):
        """Get statistics for a metric."""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return None
        
        values = self.metrics[metric_name]
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values),
        }
    
    def clear_metrics(self):
        """Clear all recorded metrics."""
        self.metrics.clear()


# Global performance monitor
perf_monitor = PerformanceMonitor()


class DatabaseQueryOptimizer:
    """Utilities for optimizing database queries."""
    
    @staticmethod
    def log_slow_queries(threshold_ms: float = 100):
        """Decorator to log slow database queries."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    elapsed_time = (time.time() - start_time) * 1000
                    if elapsed_time > threshold_ms:
                        logger.warning(
                            f"Slow query detected: {func.__name__} took {elapsed_time:.2f}ms"
                        )
                    perf_monitor.record_metric(f"query_{func.__name__}", elapsed_time)
            
            return wrapper
        
        return decorator


class CachingStrategy:
    """Caching strategies for performance optimization."""
    
    @staticmethod
    def cache_result(ttl_seconds: int = 300):
        """Decorator to cache function results."""
        cache = {}
        cache_times = {}
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                cache_key = f"{func.__name__}_{args}_{kwargs}"
                current_time = time.time()
                
                # Check if cached result is still valid
                if cache_key in cache:
                    cached_time = cache_times.get(cache_key, 0)
                    if current_time - cached_time < ttl_seconds:
                        logger.debug(f"Cache hit for {func.__name__}")
                        return cache[cache_key]
                
                # Cache miss, call function
                result = await func(*args, **kwargs)
                cache[cache_key] = result
                cache_times[cache_key] = current_time
                logger.debug(f"Cache miss for {func.__name__}, result cached")
                
                return result
            
            return wrapper
        
        return decorator


class BulkOperationOptimizer:
    """Optimize bulk operations for better performance."""
    
    @staticmethod
    def batch_operations(batch_size: int = 100):
        """Decorator to batch operations."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(items: list, *args, **kwargs) -> Any:
                results = []
                
                for i in range(0, len(items), batch_size):
                    batch = items[i:i + batch_size]
                    logger.debug(f"Processing batch {i // batch_size + 1} with {len(batch)} items")
                    
                    batch_result = await func(batch, *args, **kwargs)
                    results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
                
                return results
            
            return wrapper
        
        return decorator


# Global profiler instance
profiler = PerformanceProfiler()
