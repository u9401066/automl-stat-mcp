"""
Shared Structured Logging Configuration

Provides consistent structured logging across all services and tests.
Uses structlog for structured, context-aware logging.

Usage:
    from shared.logging import get_logger, configure_logging
    
    logger = get_logger(__name__)
    logger.info("event_name", key1="value1", key2=123)
"""
import logging
import os
import sys
from typing import Any, Dict, Optional

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    service_name: Optional[str] = None,
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output JSON format (for production)
        service_name: Service name to include in logs
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if STRUCTLOG_AVAILABLE:
        _configure_structlog(log_level, json_format, service_name)
    else:
        _configure_stdlib_logging(log_level, service_name)


def _configure_structlog(
    level: int,
    json_format: bool,
    service_name: Optional[str],
) -> None:
    """Configure structlog."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if service_name:
        shared_processors.insert(0, _add_service_name(service_name))
    
    if json_format:
        # JSON format for production/log aggregation
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        # Console format for development
        shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _add_service_name(service_name: str):
    """Create processor that adds service name to all logs."""
    def processor(logger, method_name, event_dict):
        event_dict["service"] = service_name
        return event_dict
    return processor


def _configure_stdlib_logging(level: int, service_name: Optional[str]) -> None:
    """Configure stdlib logging as fallback."""
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if service_name:
        format_str = f"%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str = __name__) -> Any:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance (structlog or stdlib)
    """
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


def bind_context(**kwargs) -> None:
    """
    Bind context variables to all subsequent logs in this context.
    
    Args:
        **kwargs: Context variables to bind
    
    Example:
        bind_context(user_id="user123", request_id="req456")
        logger.info("processing")  # Will include user_id and request_id
    """
    if STRUCTLOG_AVAILABLE:
        structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    if STRUCTLOG_AVAILABLE:
        structlog.contextvars.clear_contextvars()


# =============================================================================
# Convenience Logger Classes
# =============================================================================

class LoggerAdapter:
    """
    Adapter that works with both structlog and stdlib logging.
    Provides consistent interface regardless of available logging library.
    """
    
    def __init__(self, name: str):
        self._name = name
        self._logger = get_logger(name)
    
    def debug(self, event: str, **kwargs):
        """Log debug message."""
        self._log("debug", event, **kwargs)
    
    def info(self, event: str, **kwargs):
        """Log info message."""
        self._log("info", event, **kwargs)
    
    def warning(self, event: str, **kwargs):
        """Log warning message."""
        self._log("warning", event, **kwargs)
    
    def error(self, event: str, **kwargs):
        """Log error message."""
        self._log("error", event, **kwargs)
    
    def exception(self, event: str, **kwargs):
        """Log exception with traceback."""
        if STRUCTLOG_AVAILABLE:
            self._logger.exception(event, **kwargs)
        else:
            self._logger.exception(f"{event} {kwargs}")
    
    def _log(self, level: str, event: str, **kwargs):
        """Internal log method."""
        if STRUCTLOG_AVAILABLE:
            getattr(self._logger, level)(event, **kwargs)
        else:
            # Format kwargs for stdlib logging
            msg = event
            if kwargs:
                msg = f"{event} {kwargs}"
            getattr(self._logger, level)(msg)
    
    def bind(self, **kwargs) -> "LoggerAdapter":
        """
        Create a new logger with bound context.
        
        Args:
            **kwargs: Context to bind
        
        Returns:
            New logger with bound context
        """
        if STRUCTLOG_AVAILABLE:
            new_logger = self._logger.bind(**kwargs)
            adapter = LoggerAdapter(self._name)
            adapter._logger = new_logger
            return adapter
        return self


# =============================================================================
# Pre-configured Loggers
# =============================================================================

def get_test_logger(test_name: str) -> LoggerAdapter:
    """Get logger configured for testing."""
    logger = LoggerAdapter("test")
    return logger.bind(test=test_name)


def get_service_logger(service_name: str) -> LoggerAdapter:
    """Get logger configured for a service."""
    logger = LoggerAdapter(service_name)
    return logger.bind(service=service_name)


# =============================================================================
# Auto-configure on import
# =============================================================================

# Configure logging based on environment
_log_level = os.environ.get("LOG_LEVEL", "INFO")
_json_format = os.environ.get("LOG_FORMAT", "").lower() == "json"
_service_name = os.environ.get("SERVICE_NAME")

configure_logging(
    level=_log_level,
    json_format=_json_format,
    service_name=_service_name,
)
