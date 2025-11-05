"""
Structured JSON logging with contextual data
"""
import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import json
from contextvars import ContextVar

from app.config import settings

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context variables if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
            
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id
        
        # Add extra fields from the log record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class ContextualLogger:
    """Logger wrapper that adds contextual information"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with context injection"""
        extra_fields = kwargs.copy()
        
        # Create a log record with extra fields
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        self._log(logging.CRITICAL, message, **kwargs)


def setup_logging():
    """Configure structured logging for the application"""
    
    # Get log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if settings.LOG_FORMAT.lower() == "json":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str) -> ContextualLogger:
    """Get a contextual logger instance"""
    logger = logging.getLogger(name)
    return ContextualLogger(logger)


def set_request_context(request_id: str, user_id: Optional[str] = None):
    """Set request context for logging"""
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context():
    """Clear request context"""
    request_id_var.set(None)
    user_id_var.set(None)