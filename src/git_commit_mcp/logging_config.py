"""Structured logging configuration for Git Commit MCP Server.

This module provides structured logging with JSON format, request ID tracking,
Git operation logging, and audit logging for security events.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path


# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.
    
    Formats log records as JSON with consistent fields including:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name
    - message: Log message
    - request_id: Request ID from context (if available)
    - Additional fields from extra parameter
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        # Skip standard LogRecord attributes
        skip_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "message", "pathname", "process", "processName", "relativeCreated",
            "thread", "threadName", "exc_info", "exc_text", "stack_info"
        }
        
        for key, value in record.__dict__.items():
            if key not in skip_attrs and not key.startswith("_"):
                log_entry[key] = value
        
        return json.dumps(log_entry)


class RequestIDFilter(logging.Filter):
    """Filter that adds request ID to log records.
    
    Retrieves request ID from context variable and adds it to the log record.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            Always True (doesn't filter out records)
        """
        request_id = request_id_var.get()
        if request_id:
            record.request_id = request_id
        return True


def setup_logging(
    log_level: str = "INFO",
    use_json: bool = True,
    log_file: Optional[str] = None
) -> None:
    """Configure logging for the application.
    
    Sets up structured logging with JSON format (optional), request ID tracking,
    and configurable output destinations.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: If True, use JSON formatter; otherwise use standard format
        log_file: Optional file path for logging output
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter
    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIDFilter())
        root_logger.addHandler(file_handler)


def generate_request_id() -> str:
    """Generate a unique request ID.
    
    Returns:
        UUID-based request ID string
    """
    return str(uuid.uuid4())


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request ID in context.
    
    Args:
        request_id: Request ID to set, or None to generate a new one
        
    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = generate_request_id()
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get current request ID from context.
    
    Returns:
        Current request ID, or None if not set
    """
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear request ID from context."""
    request_id_var.set(None)


# Specialized loggers for different components
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific component.
    
    Args:
        name: Logger name (typically module name)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Git operations logger
git_logger = get_logger("git_commit_mcp.git_operations")


def log_git_operation(
    operation: str,
    repository: str,
    success: bool,
    duration: float,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> None:
    """Log a Git operation with structured data.
    
    Args:
        operation: Type of operation (commit, push, clone, etc.)
        repository: Repository path or URL
        success: Whether operation succeeded
        duration: Operation duration in seconds
        details: Additional operation details
        error: Error message if operation failed
    """
    log_data = {
        "operation": operation,
        "repository": repository,
        "success": success,
        "duration_seconds": round(duration, 3),
    }
    
    if details:
        log_data.update(details)
    
    if error:
        log_data["error"] = error
    
    if success:
        git_logger.info(
            f"Git operation completed: {operation}",
            extra=log_data
        )
    else:
        git_logger.error(
            f"Git operation failed: {operation}",
            extra=log_data
        )



