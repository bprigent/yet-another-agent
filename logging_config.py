"""Logging configuration for the Deep Agent application."""

import logging
import os
from datetime import datetime
from pathlib import Path
import contextvars
from typing import Optional

# Context variable for task tracking
task_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('task_id', default=None)


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    Set up structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler - logs everything
    log_file = log_path / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler - logs INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Error file handler - logs only errors and critical
    error_log_file = log_path / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # Log the logging setup
    logger.info(f"Logging initialized - Level: {log_level}, Log file: {log_file}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Add task context to log records if available
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        task_id = task_context.get()
        if task_id:
            record.task_id = task_id
        else:
            record.task_id = None
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    return logger


def set_task_context(task_id: Optional[str]) -> None:
    """Set the current task context for logging.
    
    Args:
        task_id: The task ID to set, or None to clear
    """
    task_context.set(task_id)


def get_task_context() -> Optional[str]:
    """Get the current task context.
    
    Returns:
        Current task ID or None
    """
    return task_context.get()
