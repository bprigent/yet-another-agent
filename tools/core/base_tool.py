"""Base patterns and utilities for tool development."""

from typing import Optional, Dict, Any, TypeVar, Callable
from pydantic import BaseModel, Field
from functools import wraps
from logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ToolResult(BaseModel):
    """Structured tool result for consistent error handling.
    
    Use this instead of returning free-form strings to provide
    structured success/error information.
    """
    
    success: bool = Field(..., description="Whether the tool call succeeded")
    data: Optional[Any] = Field(
        default=None,
        description="Result data (if successful)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (if failed)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the tool call"
    )
    
    def to_string(self) -> str:
        """Convert to string format for agent consumption."""
        if self.success:
            if isinstance(self.data, str):
                return self.data
            elif self.data is not None:
                return str(self.data)
            else:
                return "Operation completed successfully."
        else:
            return f"Error: {self.error or 'Unknown error'}"


def log_tool_call(tool_name: str):
    """Decorator to log tool calls with parameters and results.
    
    Usage:
        @log_tool_call("my_tool")
        @tool
        def my_tool(param: str) -> str:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            logger.info(
                f"Tool call: {tool_name}",
                extra={
                    "tool": tool_name,
                    "args": str(args)[:200],  # Truncate for logging
                    "kwargs": {k: str(v)[:200] for k, v in kwargs.items()}
                }
            )
            try:
                result = func(*args, **kwargs)
                
                # Log result preview
                result_preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                logger.info(
                    f"Tool success: {tool_name}",
                    extra={
                        "tool": tool_name,
                        "result_preview": result_preview
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Tool error: {tool_name}",
                    extra={
                        "tool": tool_name,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


def handle_tool_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to wrap tool functions with error handling.
    
    Converts exceptions to ToolResult with error information.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            result = func(*args, **kwargs)
            # If result is already a ToolResult, return it
            if isinstance(result, ToolResult):
                return result
            # Otherwise wrap in success ToolResult
            return ToolResult(success=True, data=result)
        except ValueError as e:
            # Validation errors - return structured error
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            # Unexpected errors - log and return error
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"{func.__name__} failed: {str(e)}"
            )
    return wrapper

