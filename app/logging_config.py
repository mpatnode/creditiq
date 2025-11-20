"""Logging configuration for the Credit Rating System.

This module sets up structured logging with appropriate log levels,
handlers, and formatters for the application.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class SanitizingFormatter(logging.Formatter):
    """Custom formatter that sanitizes sensitive information from log messages."""
    
    # Patterns to sanitize
    SENSITIVE_PATTERNS = [
        ('password', '***'),
        ('api_key', '***'),
        ('token', '***'),
        ('secret', '***'),
        ('authorization', '***'),
        ('bearer', '***'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sanitization.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted and sanitized log message
        """
        # Format the record normally first
        formatted = super().format(record)
        
        # Sanitize sensitive information
        formatted_lower = formatted.lower()
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            if pattern in formatted_lower:
                # Find and replace the value after the pattern
                import re
                # Match pattern like "password=value" or "password: value"
                regex = re.compile(
                    rf'{pattern}[\s:=]+["\']?([^"\'\s,}}]+)["\']?',
                    re.IGNORECASE
                )
                formatted = regex.sub(f'{pattern}={replacement}', formatted)
        
        return formatted


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
) -> None:
    """Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: logs/app.log)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
    """
    # Get log level from environment or parameter
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    
    # Get log file path
    if log_file is None:
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'app.log'
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_value)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = SanitizingFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = SanitizingFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level_value)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level_value)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific log levels for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    
    # Log startup message
    root_logger.info(f"Logging initialized at {log_level} level")
    root_logger.info(f"Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding contextual information to logs."""
    
    def __init__(self, logger: logging.Logger, **context):
        """Initialize log context.
        
        Args:
            logger: Logger instance
            **context: Context key-value pairs to add to logs
        """
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and add context to log records."""
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original log record factory."""
        logging.setLogRecordFactory(self.old_factory)


def log_function_call(logger: logging.Logger):
    """Decorator to log function calls with parameters and results.
    
    Args:
        logger: Logger instance to use
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Log function entry
            logger.debug(
                f"Calling {func.__name__} with args={args}, kwargs={kwargs}"
            )
            
            try:
                # Call function
                result = func(*args, **kwargs)
                
                # Log successful completion
                logger.debug(f"{func.__name__} completed successfully")
                
                return result
            
            except Exception as e:
                # Log exception
                logger.error(
                    f"{func.__name__} raised {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator
