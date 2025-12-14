"""
Structured logging configuration for the IoT backend services.
Provides both sync and async-compatible logging interfaces.
"""
import structlog
import logging
import sys
from typing import Any


# Configure standard logging
logging.basicConfig(
    format="%(message)s", 
    stream=sys.stdout, 
    level=logging.INFO
)

# Configure structlog processors
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


class AsyncCompatibleLogger:
    """
    A wrapper around structlog that provides both sync and async-compatible 
    logging methods. This allows the code to use 'await logger.info(...)' syntax
    without actually being async, for code consistency in async contexts.
    """
    
    def __init__(self):
        self._logger = structlog.get_logger()
    
    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Internal sync logging method."""
        log_method = getattr(self._logger, level)
        log_method(message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log at DEBUG level."""
        self._log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log at INFO level."""
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log at WARNING level."""
        self._log("warning", message, **kwargs)
    
    def warn(self, message: str, **kwargs: Any) -> None:
        """Log at WARNING level (alias)."""
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log at ERROR level."""
        self._log("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log at CRITICAL level."""
        self._log("critical", message, **kwargs)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log("exception", message, **kwargs)
    
    def bind(self, **kwargs: Any) -> "AsyncCompatibleLogger":
        """Bind context variables to the logger."""
        self._logger = self._logger.bind(**kwargs)
        return self


# Global logger instance
logger = AsyncCompatibleLogger()

