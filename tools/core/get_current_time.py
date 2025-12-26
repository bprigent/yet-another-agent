"""Tool to get the current date and time."""

from datetime import datetime
import pytz
from tools.core.base_tool import ToolResult, log_tool_call, ensure_string_result
from langchain_core.tools import tool


@tool
@ensure_string_result
@log_tool_call("get_current_time")
def get_current_time(timezone: str = "UTC") -> ToolResult:
    """Get the current date and time in a specified timezone.
    
    Use this tool when you need to know the current time, date for a specific task. 
    If no timezone is specified by Benjamin, use the location tool to know where Benjamin is. 
    
    Args:
        timezone: Optional timezone name (e.g., "UTC", "America/New_York", "Europe/London", "Asia/Tokyo").
                 Defaults to "UTC" if not specified or invalid.
                 
    Returns:
        A formatted string with the current date and time in the specified timezone.
    """
    try:
        # Get the timezone object
        if timezone:
            try:
                tz = pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                # Fallback to UTC if timezone is invalid
                tz = pytz.UTC
                timezone = "UTC"
        else:
            tz = pytz.UTC
            timezone = "UTC"
        
        # Get current time in the specified timezone
        now = datetime.now(tz)
        
        # Format the output
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        day_name = now.strftime("%A")
        
        return ToolResult(
            success=True,
            data=f"Current time in {timezone}: {formatted_time} ({day_name})"
        )
    
    except Exception as e:
        # Fallback to UTC if anything goes wrong
        now = datetime.now(pytz.UTC)
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        day_name = now.strftime("%A")
        return ToolResult(
            success=False,
            error=f"Current time in UTC: {formatted_time} ({day_name})\n(Note: Error occurred with requested timezone: {str(e)})"
        )

