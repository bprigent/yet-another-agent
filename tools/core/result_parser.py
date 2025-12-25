"""Utilities for parsing ToolResult from tool outputs.

This module provides optional utilities for parsing structured ToolResult
data from tool outputs. This is useful if you want to enhance your agent
to handle structured results programmatically.
"""

import json
from typing import Optional, Dict, Any
from tools.core.base_tool import ToolResult
from logging_config import get_logger

logger = get_logger(__name__)


def parse_tool_result(tool_output: str) -> Dict[str, Any]:
    """Try to parse ToolResult from tool output string.
    
    Since tools return ToolResult.to_string(), this attempts to extract
    the structured data if available. Falls back to treating the output
    as a plain string.
    
    Args:
        tool_output: The string output from a tool
        
    Returns:
        Dictionary with:
        - success: bool (if parsed successfully)
        - data: Any (structured data if available)
        - error: str (error message if failed)
        - raw: str (original output)
        - is_structured: bool (whether parsing succeeded)
    """
    result = {
        "raw": tool_output,
        "is_structured": False,
        "success": None,
        "data": None,
        "error": None
    }
    
    # Try to parse as JSON (if ToolResult was serialized)
    try:
        parsed = json.loads(tool_output)
        if isinstance(parsed, dict) and "success" in parsed:
            result.update({
                "is_structured": True,
                "success": parsed.get("success"),
                "data": parsed.get("data"),
                "error": parsed.get("error"),
                "metadata": parsed.get("metadata", {})
            })
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Try to detect ToolResult format from string patterns
    if tool_output.startswith("Error:"):
        result.update({
            "success": False,
            "error": tool_output.replace("Error: ", "").strip()
        })
    elif "Operation completed successfully" in tool_output:
        result.update({
            "success": True,
            "data": tool_output
        })
    else:
        # Assume success for non-error outputs
        result.update({
            "success": True,
            "data": tool_output
        })
    
    return result


def extract_tool_data(tool_output: str) -> Optional[Any]:
    """Extract structured data from tool output if available.
    
    Args:
        tool_output: The string output from a tool
        
    Returns:
        Structured data if available, None otherwise
    """
    parsed = parse_tool_result(tool_output)
    if parsed.get("is_structured") and parsed.get("success"):
        return parsed.get("data")
    return None


def check_tool_success(tool_output: str) -> bool:
    """Check if a tool call was successful.
    
    Args:
        tool_output: The string output from a tool
        
    Returns:
        True if successful, False if error detected
    """
    parsed = parse_tool_result(tool_output)
    if parsed.get("is_structured"):
        return parsed.get("success", True)
    
    # Heuristic: check for error patterns
    return not tool_output.startswith("Error:")


def get_tool_error(tool_output: str) -> Optional[str]:
    """Extract error message from tool output if available.
    
    Args:
        tool_output: The string output from a tool
        
    Returns:
        Error message if available, None otherwise
    """
    parsed = parse_tool_result(tool_output)
    if parsed.get("is_structured") and not parsed.get("success"):
        return parsed.get("error")
    
    if tool_output.startswith("Error:"):
        return tool_output.replace("Error: ", "").strip()
    
    return None

