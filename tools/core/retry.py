"""Retry and timeout utilities for tool calls."""

from functools import wraps
from typing import Callable, TypeVar, Tuple
import time
import signal
from contextlib import contextmanager
from logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when a function call times out."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[type[Exception], ...] = (Exception,)
):
    """Retry decorator with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        exceptions: Tuple of exception types to catch and retry (default: all exceptions)
    
    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        @tool
        def unreliable_tool():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            
            # Re-raise the last exception
            raise last_exception
        return wrapper
    return decorator


@contextmanager
def timeout(seconds: int):
    """Context manager for function timeouts.
    
    Note: This uses signal.SIGALRM which only works on Unix systems.
    On Windows, this will not work and will raise NotImplementedError.
    
    Args:
        seconds: Timeout duration in seconds
        
    Raises:
        TimeoutError: If the operation exceeds the timeout
        NotImplementedError: On Windows systems
        
    Example:
        with timeout(5):
            result = slow_operation()
    """
    if not hasattr(signal, 'SIGALRM'):
        raise NotImplementedError("Timeout not supported on this platform (Windows)")
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Function timed out after {seconds} seconds")
    
    # Set up the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore the old handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def with_timeout(seconds: int):
    """Decorator to add timeout to function calls.
    
    Note: This uses signal.SIGALRM which only works on Unix systems.
    On Windows, this decorator will raise NotImplementedError when applied.
    
    Args:
        seconds: Timeout duration in seconds
        
    Example:
        @with_timeout(5)
        @tool
        def slow_tool():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with timeout(seconds):
                return func(*args, **kwargs)
        return wrapper
    return decorator

